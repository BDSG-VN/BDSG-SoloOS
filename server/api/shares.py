from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from server.api.security import owner

router = APIRouter()


class Share(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation: str = Field(max_length=128)
    days: int = Field(default=7, ge=1, le=30)


@router.post("/api/shares", dependencies=[Depends(owner)])
def create(body: Share, request: Request):
    session = request.app.state.workspace.get("sessions", body.conversation)
    messages = request.app.state.brain.messages(body.conversation, limit=100000)
    return request.app.state.shares.create(
        session["title"],
        [{"role": m["role"], "content": m["content"]} for m in messages],
        body.days,
    )


@router.get("/api/shares", dependencies=[Depends(owner)])
def listing(request: Request):
    return request.app.state.shares.list()


@router.delete("/api/shares/{identifier}", dependencies=[Depends(owner)])
def revoke(identifier: str, request: Request):
    return request.app.state.shares.revoke(identifier)


@router.get("/api/shared/{token}")
def public(token: str, request: Request):
    if len(token) > 100:
        raise HTTPException(404, "Liên kết không tồn tại.")
    try:
        return request.app.state.shares.get(token)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
