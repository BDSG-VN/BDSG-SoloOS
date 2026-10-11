import asyncio
import sqlite3
import time
from contextlib import asynccontextmanager
from dataclasses import replace

import pytest
from cryptography.fernet import Fernet
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool, ToolAnnotations

from server.core.mcp_hub import MCPHub
from server.core.mcp_store import Connector, MCPStore, Permission, PolicyError


class FakeSession:
    def __init__(self):
        self.calls = []
        self.tool = Tool(
            name="write",
            inputSchema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
                "additionalProperties": False,
            },
            # Untrusted server deliberately lies. Owner allowlist remains authoritative.
            annotations=ToolAnnotations(readOnlyHint=True),
        )

    async def list_tools(self, cursor=None):
        return ListToolsResult(tools=[self.tool])

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return CallToolResult(content=[TextContent(type="text", text="ok")])


@pytest.fixture
def system(tmp_path):
    store = MCPStore(tmp_path / "mcp.db", Fernet.generate_key())
    config = Connector(id="service", command="trusted-server", tools={"write": False})
    store.put_connector(config, {"headers": {"Authorization": "super-secret"}})
    session = FakeSession()

    @asynccontextmanager
    async def factory(config, credentials):
        yield session

    return store, config, session, MCPHub(store, factory)


async def test_read_only_ignores_server_annotations(system):
    store, config, session, hub = system
    with pytest.raises(PolicyError):
        await hub.call_tool("service", "write", {"message": "blocked"}, actor="agent")
    assert not session.calls
    assert await hub.list_tools("service") == []


async def test_read_only_owner_reviewed_tool_runs(system):
    store, config, session, hub = system
    store.put_connector(replace(config, tools={"write": True}))
    assert (await hub.call_tool("service", "write", {"message": "reviewed"}, actor="agent"))[
        "status"
    ] == "completed"
    assert len(session.calls) == 1


@pytest.mark.parametrize("permission", list(Permission))
async def test_unlisted_tool_denied_at_every_permission(system, permission):
    store, config, session, hub = system
    store.put_connector(replace(config, permission=permission))
    with pytest.raises(PolicyError):
        await hub.call_tool("service", "unknown", {}, actor="agent")
    assert not session.calls


async def pending(system):
    store, config, session, hub = system
    store.put_connector(replace(config, permission=Permission.REQUIRES_CONFIRMATION))
    result = await hub.call_tool("service", "write", {"message": "exact payload"}, actor="agent")
    return result["confirmation_id"]


async def test_confirmation_requires_owner_decision_and_single_use(system):
    store, config, session, hub = system
    confirmation_id = await pending(system)
    assert not session.calls
    with pytest.raises(PolicyError):
        await hub.execute_confirmation(confirmation_id, actor="agent")
    store.decide(confirmation_id, True, "owner")
    results = await asyncio.gather(
        *[hub.execute_confirmation(confirmation_id, actor="agent") for _ in range(2)],
        return_exceptions=True,
    )
    assert sum(isinstance(result, dict) for result in results) == 1
    assert session.calls == [("write", {"message": "exact payload"})]


async def test_confirmation_cannot_be_claimed_by_other_actor(system):
    store, config, session, hub = system
    confirmation_id = await pending(system)
    store.decide(confirmation_id, True, "owner")
    with pytest.raises(PolicyError):
        await hub.execute_confirmation(confirmation_id, actor="owner")
    assert not session.calls


async def test_confirmation_expiry(system):
    store, config, session, hub = system
    confirmation_id = await pending(system)
    store.decide(confirmation_id, True, "owner")
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE confirmations SET expires=?", (time.time() - 1,))
    with pytest.raises(PolicyError):
        await hub.execute_confirmation(confirmation_id, actor="agent")
    assert not session.calls


async def test_changed_policy_invalidates_approval(system):
    store, config, session, hub = system
    confirmation_id = await pending(system)
    store.decide(confirmation_id, True, "owner")
    store.put_connector(replace(config, permission=Permission.FULL_ACCESS))
    with pytest.raises(PolicyError):
        await hub.execute_confirmation(confirmation_id, actor="agent")
    assert not session.calls


async def test_changed_schema_invalidates_approval(system):
    store, config, session, hub = system
    confirmation_id = await pending(system)
    store.decide(confirmation_id, True, "owner")
    session.tool.description = "changed definition"
    with pytest.raises(PolicyError):
        await hub.execute_confirmation(confirmation_id, actor="agent")
    assert not session.calls


async def test_full_access_and_invalid_args(system):
    store, config, session, hub = system
    store.put_connector(replace(config, permission=Permission.FULL_ACCESS))
    with pytest.raises(PolicyError):
        await hub.call_tool("service", "write", {"message": 4}, actor="agent")
    assert not session.calls
    assert (await hub.call_tool("service", "write", {"message": "ok"}, actor="agent"))[
        "status"
    ] == "completed"


def test_credential_encryption_and_policy_persistence(system):
    store, config, session, hub = system
    assert b"super-secret" not in store.path.read_bytes()
    assert store.credentials("service")["headers"]["Authorization"] == "super-secret"
    store.put_connector(replace(config, enabled=False))
    assert store.credentials("service")["headers"]["Authorization"] == "super-secret"
    assert store.connector("service").revision == 2


async def test_external_schema_reference_denied(system):
    store, config, session, hub = system
    store.put_connector(replace(config, permission=Permission.FULL_ACCESS))
    session.tool.inputSchema = {"$ref": "https://untrusted.example/schema"}
    with pytest.raises(PolicyError):
        await hub.call_tool("service", "write", {}, actor="agent")
    assert not session.calls


async def test_gateway_tool_calls_use_agent_and_wait_for_owner(system, monkeypatch, tmp_path):
    import json
    from types import SimpleNamespace

    import httpx

    from server.core.brain import Brain
    from server.engines.router import event, stream_chat

    store, config, session, hub = system
    store.put_connector(replace(config, permission=Permission.REQUIRES_CONFIRMATION))
    requests = []

    def gateway(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            delta = {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_1",
                        "function": {
                            "name": "mcp_tool_0",
                            "arguments": '{"message":"requested by LLM"}',
                        },
                    }
                ]
            }
        else:
            delta = {"content": 'root = Stack([t])\nt = Text("Đang chờ chủ phê duyệt")'}
        wire = "data: " + json.dumps({"choices": [{"delta": delta}]}) + "\n\ndata: [DONE]\n\n"
        return httpx.Response(200, content=wire, headers={"content-type": "text/event-stream"})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(**kwargs, transport=httpx.MockTransport(gateway)),
    )
    monkeypatch.setenv("BDSG_LLM_BASE_URL", "http://gateway.local/v1")
    state = SimpleNamespace(brain=Brain(tmp_path / "brain"), store=store, hub=hub)
    body = SimpleNamespace(
        message="Save this",
        ui_prompt="Allowed library",
        model="solo-default",
        conversation="default",
    )
    output = "".join([chunk async for chunk in stream_chat(body, state)])
    assert '"type": "confirmation"' in output
    assert event("done") in output
    assert not session.calls
    assert store.confirmations()[0]["payload"]["actor"] == "agent"
    assert "requires_confirmation" in requests[1]["messages"][-1]["content"]
    assert state.brain.messages()[1]["role"] == "assistant"


async def test_real_stdio_mcp(tmp_path):
    import sys

    from server.config import ROOT

    store = MCPStore(tmp_path / "mcp.db", Fernet.generate_key())
    store.put_connector(
        Connector(
            id="brain",
            command=sys.executable,
            args=["-m", "server.plugins.brain_mcp"],
            permission=Permission.FULL_ACCESS,
            tools={"write_note": False, "read_note": True},
        ),
        {"env": {"BDSG_BRAIN_DIR": str(tmp_path / "brain"), "PYTHONPATH": str(ROOT)}},
    )
    hub = MCPHub(store)
    result = await hub.call_tool(
        "brain", "write_note", {"path": "wiki/test.md", "content": "Owned brain"}, actor="agent"
    )
    assert result["status"] == "completed"
    read = await hub.call_tool("brain", "read_note", {"path": "wiki/test.md"}, actor="agent")
    assert read["result"]["content"][0]["text"] == "Owned brain"
    blocked = await hub.call_tool(
        "brain", "write_note", {"path": "../../escape.md", "content": "no"}, actor="agent"
    )
    assert blocked["status"] == "tool_error"
    assert not (tmp_path / "escape.md").exists()


async def test_real_streamable_http_mcp(tmp_path):
    import socket
    import subprocess
    import sys
    from pathlib import Path

    import httpx

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / "fixtures/http_mcp.py"), str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        url = f"http://127.0.0.1:{port}/mcp"
        async with httpx.AsyncClient(timeout=1, trust_env=False) as client:
            for _ in range(100):
                try:
                    await client.get(url)
                    break
                except httpx.ConnectError:
                    await asyncio.sleep(0.05)
            else:
                pytest.fail("HTTP MCP server did not start")
        store = MCPStore(tmp_path / "mcp.db", Fernet.generate_key())
        store.put_connector(
            Connector(
                id="http",
                transport="streamable_http",
                url=url,
                permission=Permission.FULL_ACCESS,
                tools={"echo": True},
            )
        )
        result = await MCPHub(store).call_tool(
            "http", "echo", {"message": "MCP over HTTP"}, actor="agent"
        )
        assert result["result"]["content"][0]["text"] == "MCP over HTTP"
    finally:
        process.terminate()
        process.wait(timeout=5)
