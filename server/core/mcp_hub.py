"""The only tool execution boundary for every model and background worker."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Callable

import httpx
from jsonschema import Draft202012Validator, ValidationError
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from server.core.mcp_store import Connector, MCPStore, Permission, PolicyError, canonical, digest


def validate_local_schema(schema):
    """Never let a tool-supplied JSON Schema trigger external reference fetching."""
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key in {"$ref", "$dynamicRef"} and (
                not isinstance(value, str) or not value.startswith("#")
            ):
                raise PolicyError("External schema references are not allowed")
            validate_local_schema(value)
    elif isinstance(schema, list):
        for value in schema:
            validate_local_schema(value)


@asynccontextmanager
async def mcp_session(config: Connector, credentials: dict):
    """Open and close transport in the same async task (SDK uses AnyIO scopes).

    Servers are trusted installations: launching a malicious executable cannot be
    contained by tool policies. Sandbox the MCP process separately if necessary.
    No sampling or elicitation callbacks: servers cannot request extra LLM authority.
    """
    if config.transport == "stdio":
        params = StdioServerParameters(
            command=config.command, args=config.args, env=credentials.get("env", {})
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(
                read, write, read_timeout_seconds=timedelta(seconds=30)
            ) as session:
                await session.initialize()
                yield session
    else:
        async with httpx.AsyncClient(
            headers=credentials.get("headers", {}),
            timeout=30,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            async with streamable_http_client(config.url, http_client=client) as (read, write, _):
                async with ClientSession(
                    read, write, read_timeout_seconds=timedelta(seconds=30)
                ) as session:
                    await session.initialize()
                    yield session


class MCPHub:
    def __init__(self, store: MCPStore, session_factory: Callable = mcp_session):
        self.store = store
        self._session_factory = session_factory
        self.execution_guard = lambda run_id: False

    def _policy(self, connector_id: str, tool: str) -> Connector:
        config = self.store.connector(connector_id)
        if not config.enabled or tool not in config.tools:
            raise PolicyError("Connector disabled or tool not owner-allowlisted")
        if config.permission == Permission.READ_ONLY and config.tools[tool] is not True:
            raise PolicyError("Read-only connector cannot execute this tool")
        return config

    async def _tools(self, session) -> dict:
        tools, cursor, seen = {}, None, set()
        for _ in range(100):
            page = await session.list_tools(cursor=cursor)
            for tool in page.tools:
                if tool.name in tools:
                    raise PolicyError("Ambiguous MCP tool catalog")
                tools[tool.name] = tool
            cursor = page.nextCursor
            if not cursor:
                return tools
            if cursor in seen:
                break
            seen.add(cursor)
        raise PolicyError("Invalid or excessive MCP tool pagination")

    async def list_tools(self, connector_id: str) -> list[dict]:
        config = self.store.connector(connector_id)
        if not config.enabled:
            raise PolicyError("Connector disabled")
        async with asyncio.timeout(45):
            async with self._session_factory(
                config, self.store.credentials(connector_id)
            ) as session:
                tools = await self._tools(session)
        return [
            tool.model_dump(mode="json")
            for name, tool in tools.items()
            if name in config.tools
            and (config.permission != Permission.READ_ONLY or config.tools[name] is True)
        ]

    async def call_tool(
        self,
        connector_id: str,
        tool: str,
        arguments: dict,
        *,
        actor: str,
        run_id: str | None = None,
    ) -> dict:
        # Freeze a JSON copy so concurrent caller mutation cannot alter what was approved.
        import json

        arguments = json.loads(canonical(arguments))
        try:
            config = self._policy(connector_id, tool)
            return await self._dispatch(config, tool, arguments, actor, run_id=run_id)
        except PolicyError:
            self.store.audit("denied", connector_id, tool, actor)
            raise

    async def execute_confirmation(self, confirmation_id: str, *, actor: str) -> dict:
        payload = self.store.claim(confirmation_id, actor)
        config = self._policy(payload["connector"], payload["tool"])
        if config.revision != payload["revision"]:
            raise PolicyError("Connector policy changed; request a new confirmation")
        return await self._dispatch(
            config,
            payload["tool"],
            payload["arguments"],
            actor,
            approved=payload,
            run_id=payload.get("run_id"),
        )

    async def _dispatch(self, config, tool_name, arguments, actor, approved=None, run_id=None):
        async with asyncio.timeout(45):
            async with self._session_factory(config, self.store.credentials(config.id)) as session:
                tools = await self._tools(session)
                tool = tools.get(tool_name)
                if tool is None:
                    raise PolicyError("Tool missing from current MCP catalog")
                schema_hash = digest(tool.model_dump(mode="json"))
                validate_local_schema(tool.inputSchema)
                Draft202012Validator.check_schema(tool.inputSchema)
                try:
                    Draft202012Validator(tool.inputSchema).validate(arguments)
                except ValidationError as exc:
                    raise PolicyError("Arguments do not match MCP tool schema") from exc
                current = self._policy(config.id, tool_name)
                if current.revision != config.revision:
                    raise PolicyError("Connector changed during invocation")
                if approved and approved["schema_hash"] != schema_hash:
                    raise PolicyError("Tool definition changed; request a new confirmation")
                if run_id and not self.execution_guard(run_id):
                    raise PolicyError("Workflow is no longer active")
                if current.permission == Permission.REQUIRES_CONFIRMATION and approved is None:
                    confirmation_id = self.store.request_confirmation(
                        {
                            "connector": config.id,
                            "tool": tool_name,
                            "arguments": arguments,
                            "revision": config.revision,
                            "schema_hash": schema_hash,
                            "actor": actor,
                            **({"run_id": run_id} if run_id else {}),
                        }
                    )
                    self.store.audit("confirmation_requested", config.id, tool_name, actor)
                    return {"status": "requires_confirmation", "confirmation_id": confirmation_id}
                self.store.audit("dispatching", config.id, tool_name, actor)
                try:
                    result = await session.call_tool(tool_name, arguments=arguments)
                except BaseException:
                    self.store.audit("failed_or_uncertain", config.id, tool_name, actor)
                    raise
                self.store.audit(
                    "tool_error" if result.isError else "completed", config.id, tool_name, actor
                )
                return {
                    "status": "tool_error" if result.isError else "completed",
                    "result": result.model_dump(mode="json"),
                }
