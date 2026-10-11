"""Official Sign in with ChatGPT public-client flow, with no vendor CLI impersonation."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import jwt

AUTHORIZE = "https://auth.openai.com/api/accounts/authorize"
TOKEN = "https://auth.openai.com/api/accounts/oauth/token"
DISCOVERY = "https://auth.openai.com/.well-known/openid-configuration"
RESOURCE = "https://api.openai.com/v1"
CALLBACK = "http://127.0.0.1:1455/auth/callback"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"


class SignInError(ValueError):
    pass


def start(store, account_id=None):
    verifier, nonce = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    account = store.account(account_id) if account_id else None
    client_id = account["client_id"] if account else "dynamic_agent_client"
    state = store.pending(
        {
            "verifier": verifier,
            "nonce": nonce,
            "client_id": client_id,
            "account_id": account_id,
            "identity": account["identity"] if account else None,
            "revision": account["revision"] if account else None,
        }
    )
    query = {
        "client_id": client_id,
        "ext_agent_host_id": store.setting("host_id"),
        "response_type": "code",
        "redirect_uri": CALLBACK,
        "scope": SCOPES,
        "resource": RESOURCE,
        "state": state,
        "nonce": nonce,
        "code_challenge_method": "S256",
        "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("="),
    }
    if not account:
        query["agent_name_hint"] = "BDSG SoloOS"
    # Do not expose a retained ID token in an authorization URL returned to the dashboard.
    return {"authorization_url": AUTHORIZE + "?" + urlencode(query), "expires_in": 600}


async def discovery(client):
    response = await client.get(DISCOVERY)
    response.raise_for_status()
    data = response.json()
    if data.get("issuer") != "https://auth.openai.com":
        raise SignInError("Unexpected identity issuer")
    return data


def trusted_auth_url(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "auth.openai.com"
        or parsed.username
        or parsed.port not in {None, 443}
    ):
        raise SignInError("Unexpected identity endpoint")
    return value


async def validate_identity(client, token, client_id, nonce=None, expected_subject=None):
    metadata = await discovery(client)
    keys = await client.get(trusted_auth_url(metadata["jwks_uri"]))
    keys.raise_for_status()
    jwks = jwt.PyJWKSet.from_dict(keys.json())
    kid = jwt.get_unverified_header(token).get("kid")
    key = next((k for k in jwks.keys if k.key_id == kid and k.algorithm_name == "RS256"), None)
    if not key:
        raise SignInError("Identity signing key unavailable")
    claims = jwt.decode(
        token,
        key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer="https://auth.openai.com",
        options={"require": ["exp", "iss", "aud", "sub"]},
    )
    if nonce is not None and not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
        raise SignInError("Identity nonce mismatch")
    if expected_subject is not None and claims["sub"] != expected_subject:
        raise SignInError("Signed-in identity changed")
    return claims


def credentials(tokens, previous=None):
    previous = previous or {}
    scope = tokens.get("scope")
    scopes = scope.split() if isinstance(scope, str) else previous.get("scopes", [])
    if "chatgpt.tokens.use.direct" not in scopes:
        raise SignInError(
            "ChatGPT plan permission was not granted. Enable it in ChatGPT settings and reconnect."
        )
    if not tokens.get("access_token") or tokens.get("token_type", "Bearer").lower() != "bearer":
        raise SignInError("Missing access credential")
    return previous | {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", previous.get("refresh_token", "")),
        "id_token": tokens.get("id_token", previous.get("id_token", "")),
        "scopes": scopes,
        "expires_at": time.time() + max(1, min(int(tokens.get("expires_in", 3600)), 86400)),
    }


async def finish(store, callback_url):
    parsed = urlsplit(callback_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port != 1455
        or parsed.path != "/auth/callback"
        or parsed.fragment
        or parsed.username
    ):
        raise SignInError("Invalid callback address")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if any(len(values) != 1 for values in query.values()):
        raise SignInError("Duplicate callback fields")
    pending = store.consume_pending(query.get("state", [""])[0])
    if "error" in query:
        raise SignInError("ChatGPT sign-in was cancelled or denied")
    issued = query.get("client_id", [pending["client_id"]])[0]
    if issued == "dynamic_agent_client" or (
        pending["client_id"] != "dynamic_agent_client" and issued != pending["client_id"]
    ):
        raise SignInError("Account registration did not match")
    code = query.get("code", [""])[0]
    if not code:
        raise SignInError("Missing authorization code")
    try:
        async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
            response = await client.post(
                TOKEN,
                data={
                    "grant_type": "authorization_code",
                    "client_id": issued,
                    "code": code,
                    "code_verifier": pending["verifier"],
                    "redirect_uri": CALLBACK,
                    "resource": RESOURCE,
                },
            )
            response.raise_for_status()
            tokens = response.json()
            claims = await validate_identity(
                client, tokens["id_token"], issued, pending["nonce"], pending["identity"]
            )
            record = credentials(tokens) | {"email": claims.get("email", "")}
        account_id = store.save_account(
            claims["sub"], issued, record, pending["account_id"], pending["revision"]
        )
        return {"connected": True, "account_id": account_id}
    except SignInError:
        raise
    except Exception as exc:
        raise SignInError(
            "Could not validate ChatGPT sign-in. Start a fresh sign-in attempt."
        ) from exc


async def access_token(store, account_id):
    for _ in range(120):
        account = store.account(account_id)
        if not account["connected"]:
            raise SignInError("Reconnect your ChatGPT account")
        saved = account["credentials"]
        if saved.get("expires_at", 0) > time.time() + 60:
            return saved["access_token"]
        if not saved.get("refresh_token"):
            raise SignInError("ChatGPT sign-in expired. Reconnect this account.")
        with store.db() as db:
            acquired = db.execute(
                "UPDATE accounts SET refresh_until=? WHERE id=? AND revision=? AND connected=1 AND refresh_until<?",
                (time.time() + 120, account_id, account["revision"], time.time()),
            ).rowcount
        if not acquired:
            await asyncio.sleep(0.25)
            continue
        try:
            async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
                response = await client.post(
                    TOKEN,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": account["client_id"],
                        "refresh_token": saved["refresh_token"],
                        "resource": RESOURCE,
                    },
                )
                response.raise_for_status()
                tokens = response.json()
                if tokens.get("id_token"):
                    await validate_identity(
                        client,
                        tokens["id_token"],
                        account["client_id"],
                        expected_subject=account["identity"],
                    )
                updated = credentials(tokens, saved)
            with store.db() as db:
                changed = db.execute(
                    "UPDATE accounts SET credentials=?,refresh_until=0,revision=revision+1 WHERE id=? AND revision=? AND connected=1",
                    (store.seal(updated), account_id, account["revision"]),
                ).rowcount
            if not changed:
                raise SignInError("Account changed during renewal. Select it again.")
            return updated["access_token"]
        except SignInError:
            raise
        except Exception as exc:
            raise SignInError(
                "ChatGPT session could not be renewed. Reconnect this account."
            ) from exc
        finally:
            with store.db() as db:
                db.execute(
                    "UPDATE accounts SET refresh_until=0 WHERE id=? AND revision=?",
                    (account_id, account["revision"]),
                )
    raise SignInError("Another request is renewing this account. Try again shortly.")


async def logout(store, account_id):
    account = store.account(account_id)
    revoked = False
    token = account["credentials"].get("refresh_token")
    if token:
        try:
            async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
                meta = await discovery(client)
                response = await client.post(
                    trusted_auth_url(meta["revocation_endpoint"]),
                    data={
                        "token": token,
                        "token_type_hint": "refresh_token",
                        "client_id": account["client_id"],
                    },
                )
                revoked = response.status_code == 200
        except Exception:
            pass
    store.disconnect(account_id)
    return {"disconnected": True, "remote_revocation_confirmed": revoked}


async def models(store, account_id):
    token = await access_token(store, account_id)
    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        response = await client.get(
            RESOURCE + "/models", headers={"Authorization": "Bearer " + token}
        )
        response.raise_for_status()
        return [
            {"id": m["slug"], "name": m.get("display_name", m["slug"])}
            for m in response.json().get("models", [])
            if m.get("visibility") == "list"
        ]
