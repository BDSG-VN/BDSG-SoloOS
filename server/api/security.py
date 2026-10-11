"""Single-owner sessions; agent bearer credentials cannot approve or change policy."""

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import HTTPException, Request

COOKIE = "bdsg_session"


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def mint_session(settings, store):
    expires = time.time() + 43200
    payload = base64.urlsafe_b64encode(
        json.dumps(
            {
                "expires": expires,
                "csrf": secrets.token_urlsafe(32),
            }
        ).encode()
    ).decode()
    signature = hmac.new(settings.store_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = payload + "." + signature
    store.register_session(token_hash(token), expires)
    return token


def session_data(request: Request):
    token = request.cookies.get(COOKIE, "")
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(
            request.app.state.settings.store_key.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload))
        return (
            data
            if data["expires"] > time.time()
            and request.app.state.store.session_valid(token_hash(token))
            else None
        )
    except (ValueError, KeyError, TypeError):
        return None


def principal(request: Request) -> str:
    settings = request.app.state.settings
    authorization = request.headers.get("authorization")
    if authorization is not None:
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Bearer authentication required")
        token = authorization.removeprefix("Bearer ")
        if hmac.compare_digest(token.encode(), settings.owner_token.encode()):
            return "owner"
        if hmac.compare_digest(token.encode(), settings.agent_token.encode()):
            return "agent"
        raise HTTPException(401, "Invalid bearer credential")
    if session_data(request):
        return "owner"
    raise HTTPException(401, "Authentication required")


def owner(request: Request) -> str:
    if principal(request) != "owner":
        raise HTTPException(403, "Only the owner can approve actions or change policy")
    return "owner"
