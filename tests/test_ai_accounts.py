import json
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import jwt
import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa

from server.core.ai_accounts import AIAccounts
from server.engines import chatgpt
from server.engines import chatgpt_auth as auth


@pytest.fixture
def store(tmp_path):
    return AIAccounts(tmp_path / "ai.db", Fernet.generate_key().decode())


def test_encryption_one_use_and_account_isolation(store):
    attempt = store.pending({"verifier": "secret-verifier"})
    assert store.consume_pending(attempt)["verifier"] == "secret-verifier"
    with pytest.raises(ValueError):
        store.consume_pending(attempt)
    first = store.save_account("one", "client-one", {"access_token": "secret-token"})
    second = store.save_account("two", "client-two", {"access_token": "other-token"})
    assert b"secret-token" not in store.path.read_bytes()
    assert "access_token" not in json.dumps(store.accounts())
    with pytest.raises(ValueError):
        store.save_account("two", "client-two", {}, expected_id=first)
    store.disconnect(first)
    assert store.account(first)["credentials"] == {}
    assert store.account(second)["connected"]
    assert store.setting("active_account") == second


@pytest.mark.asyncio
async def test_signed_identity_and_pkce_exchange(store, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())) | {
        "kid": "key",
        "alg": "RS256",
    }
    start = auth.start(store)
    query = parse_qs(urlsplit(start["authorization_url"]).query)
    seen = []

    def transport(request):
        if request.url.path.endswith("openid-configuration"):
            return httpx.Response(
                200,
                json={
                    "issuer": "https://auth.openai.com",
                    "jwks_uri": "https://auth.openai.com/keys",
                },
            )
        if request.url.path == "/keys":
            return httpx.Response(200, json={"keys": [jwk]})
        form = parse_qs(request.content.decode())
        seen.append(form)
        assert form["client_id"] == ["oaiapp-test"]
        assert form["redirect_uri"] == [auth.CALLBACK]
        claims = {
            "sub": "subject",
            "iss": "https://auth.openai.com",
            "aud": "oaiapp-test",
            "exp": time.time() + 300,
            "nonce": query["nonce"][0],
        }
        token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "key"})
        return httpx.Response(
            200,
            json={
                "access_token": "secret-access",
                "refresh_token": "secret-refresh",
                "id_token": token,
                "scope": auth.SCOPES,
                "expires_in": 3600,
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(transport), **kw),
    )
    callback = (
        auth.CALLBACK
        + "?"
        + urlencode({"state": query["state"][0], "client_id": "oaiapp-test", "code": "code"})
    )
    result = await auth.finish(store, callback)
    assert result["connected"]
    assert len(seen) == 1
    with pytest.raises(ValueError):
        await auth.finish(store, callback)
    again = parse_qs(urlsplit(auth.start(store, result["account_id"])["authorization_url"]).query)
    assert again["client_id"] == ["oaiapp-test"]
    assert again["ext_agent_host_id"] == query["ext_agent_host_id"]
    assert "agent_name_hint" not in again


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change", [{"nonce": "wrong"}, {"aud": "wrong"}, {"iss": "https://evil.example"}, {"exp": 1}]
)
async def test_reject_identity_claims(store, monkeypatch, change):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())) | {
        "kid": "key",
        "alg": "RS256",
    }
    claims = {
        "sub": "one",
        "iss": "https://auth.openai.com",
        "aud": "client",
        "exp": time.time() + 300,
        "nonce": "nonce",
    } | change
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "key"})

    def handler(request):
        return httpx.Response(
            200,
            json={"issuer": "https://auth.openai.com", "jwks_uri": "https://auth.openai.com/keys"}
            if request.url.path.endswith("openid-configuration")
            else {"keys": [jwk]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises((auth.SignInError, jwt.InvalidTokenError)):
            await auth.validate_identity(client, token, "client", "nonce")


def test_plan_grant_required():
    with pytest.raises(auth.SignInError):
        auth.credentials({"access_token": "token", "scope": "openid"})


@pytest.mark.asyncio
async def test_stream_completion_and_incomplete_are_distinct(store, monkeypatch):
    account = store.save_account(
        "one", "client", {"access_token": "token", "expires_at": time.time() + 3600}
    )
    completed = False

    def handler(request):
        body = json.loads(request.content)
        assert body["store"] is False and body["stream"] is True
        assert not {"temperature", "max_output_tokens", "conversation"} & body.keys()
        events = [{"type": "response.output_text.delta", "delta": "hello"}]
        if completed:
            events.append(
                {
                    "type": "response.completed",
                    "response": {
                        "status": "completed",
                        "output": [],
                        "usage": {"input_tokens": 2, "output_tokens": 1},
                    },
                }
            )
        return httpx.Response(200, text="".join("data: " + json.dumps(e) + "\n\n" for e in events))

    original = httpx.AsyncClient
    monkeypatch.setattr(
        chatgpt.httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
    )
    state = SimpleNamespace(ai=store)
    with pytest.raises(ValueError, match="giữa chừng"):
        _ = [v async for v in chatgpt.response_round(state, account, "model", "instructions", [])]
    completed = True
    values = [v async for v in chatgpt.response_round(state, account, "model", "instructions", [])]
    assert values[-1]["type"] == "completed"
    assert {row["status"] for row in store.usage_summary()} == {"completed", "interrupted"}


def test_old_reauth_cannot_restore_disconnected_account(store):
    account = store.save_account("one", "client", {"access_token": "secret"})
    revision = store.account(account)["revision"]
    store.disconnect(account)
    with pytest.raises(ValueError, match="changed"):
        store.save_account("one", "client", {"access_token": "new"}, account, revision)
    assert not store.account(account)["connected"]


@pytest.mark.asyncio
async def test_refresh_rotation_and_disconnect_race(store, monkeypatch):
    import asyncio

    account = store.save_account(
        "one",
        "client",
        {
            "access_token": "expired",
            "refresh_token": "old-refresh",
            "expires_at": 0,
            "scopes": auth.SCOPES.split(),
        },
    )
    calls = []

    async def handler(request):
        calls.append(parse_qs(request.content.decode()))
        await asyncio.sleep(0.05)
        return httpx.Response(
            200, json={"access_token": "new", "refresh_token": "rotated", "expires_in": 3600}
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        auth.httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
    )
    assert await asyncio.gather(
        auth.access_token(store, account), auth.access_token(store, account)
    ) == ["new", "new"]
    assert len(calls) == 1
    assert store.account(account)["credentials"]["refresh_token"] == "rotated"
    store.save_account(
        "one",
        "client",
        {
            "access_token": "expired",
            "refresh_token": "rotated",
            "expires_at": 0,
            "scopes": auth.SCOPES.split(),
        },
    )
    pending = asyncio.create_task(auth.access_token(store, account))
    await asyncio.sleep(0.01)
    store.disconnect(account)
    with pytest.raises(auth.SignInError):
        await pending
    assert not store.account(account)["connected"]
    assert store.account(account)["credentials"] == {}


@pytest.mark.asyncio
async def test_model_namespace_cannot_escape_hub(store, monkeypatch):
    account = store.save_account("one", "client", {"access_token": "token"})
    calls = []

    async def tools(identifier):
        return [{"name": "write", "description": "write", "inputSchema": {"type": "object"}}]

    async def call(*args, **kwargs):
        calls.append(args)

    async def response(*args, **kwargs):
        yield {
            "type": "completed",
            "output": [
                {
                    "type": "function_call",
                    "namespace": "evil",
                    "name": "tool_0",
                    "arguments": "{}",
                    "call_id": "call",
                }
            ],
        }

    monkeypatch.setattr(chatgpt, "response_round", response)
    state = SimpleNamespace(
        ai=store,
        brain=SimpleNamespace(notes=lambda: [], messages=lambda _: [], add=lambda *args: None),
        store=SimpleNamespace(connectors=lambda: [{"id": "service", "enabled": True}]),
        hub=SimpleNamespace(list_tools=tools, call_tool=call),
    )
    body = SimpleNamespace(
        model="model", conversation="default", message="hello", ui_prompt="library"
    )
    output = "".join([part async for part in chatgpt.stream_chatgpt(body, state)])
    assert '"type": "error"' in output and not calls
    assert store.setting("active_account") == account
