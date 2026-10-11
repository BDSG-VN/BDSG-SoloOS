"""Owner-only account controls; provider credentials never enter browser storage."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from server.api.security import owner
from server.config import ROOT
from server.engines import chatgpt_auth

router = APIRouter(prefix="/api/ai", dependencies=[Depends(owner)])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    account_id: str | None = None


class Callback(Input):
    callback_url: str = Field(max_length=16000)


class Selection(Input):
    account_id: str = Field(max_length=100)
    model: str = Field(default="", max_length=200)


@router.get("/accounts")
def accounts(request: Request):
    store = request.app.state.ai
    return {
        "accounts": store.accounts(),
        "active_account": store.setting("active_account", "gateway"),
        "selected_model": store.setting("model:" + store.setting("active_account", "gateway"), ""),
        "gateway_configured": bool(request.app.state.cms.gateway()["base_url"]),
        "usage": store.usage_summary(),
    }


@router.get("/claude/status")
async def claude_status():
    from server.engines.claude_native import status

    return await status()


@router.post("/chatgpt/start")
def start(body: Login, request: Request):
    return chatgpt_auth.start(request.app.state.ai, body.account_id)


@router.post("/chatgpt/finish")
async def finish(body: Callback, request: Request):
    return await chatgpt_auth.finish(request.app.state.ai, body.callback_url)


@router.get("/chatgpt/helper")
def helper():
    return FileResponse(
        ROOT / "scripts/chatgpt_login.py",
        media_type="text/x-python",
        filename="soloos-chatgpt-login.py",
    )


@router.get("/accounts/{account_id}/models")
async def models(account_id: str, request: Request):
    try:
        return await chatgpt_auth.models(request.app.state.ai, account_id)
    except ValueError:
        raise
    except Exception as exc:
        raise HTTPException(
            502, "Không đọc được danh sách model. Kiểm tra kết nối tài khoản."
        ) from exc


@router.post("/select")
def select(body: Selection, request: Request):
    store = request.app.state.ai
    store.activate(body.account_id)
    store.set_setting("model:" + body.account_id, body.model)
    return {"selected": True}


@router.post("/accounts/{account_id}/disconnect")
async def disconnect(account_id: str, request: Request):
    return await chatgpt_auth.logout(request.app.state.ai, account_id)
