"""Private owner profile and password changes with reauthentication."""

import hmac
import json
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from server.api.security import COOKIE, owner
from server.core.members import password_hash

router = APIRouter(prefix="/api/profile", dependencies=[Depends(owner)])


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=120)
    email: str = Field(default="", max_length=254, pattern=r"^$|^[^\s@]+@[^\s@]+\.[^\s@]+$")
    bio: str = Field(default="", max_length=1000)


class Password(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


def read_account(db):
    row = db.execute("SELECT value FROM settings WHERE key='admin_account'").fetchone()
    if not row:
        raise HTTPException(409, "Hãy khởi tạo tài khoản admin trước.")
    return json.loads(row["value"])


def public_account(value):
    return {
        "username": value["username"],
        "display_name": value.get("display_name", value["username"]),
        "email": value.get("email", ""),
        "bio": value.get("bio", ""),
    }


@router.get("")
def profile(request: Request):
    with request.app.state.cms.db() as db:
        return public_account(read_account(db))


@router.put("")
def update_profile(body: Profile, request: Request):
    if not body.display_name.strip():
        raise HTTPException(422, "Tên hiển thị không được để trống.")
    with request.app.state.cms.db() as db:
        db.execute("BEGIN IMMEDIATE")
        value = read_account(db) | body.model_dump()
        value["display_name"] = body.display_name.strip()
        db.execute("UPDATE settings SET value=? WHERE key='admin_account'", (json.dumps(value),))
    return public_account(value)


@router.post("/password")
def change_password(body: Password, request: Request, response: Response):
    store = request.app.state.store
    if not store.rate_limit("admin-password-change", 5):
        raise HTTPException(429, "Thử quá nhiều lần. Vui lòng chờ một phút.")
    with request.app.state.cms.db() as db:
        db.execute("BEGIN IMMEDIATE")
        value = read_account(db)
        if not hmac.compare_digest(
            password_hash(body.current_password, value["salt"]), value["password"]
        ):
            raise HTTPException(400, "Mật khẩu hiện tại không đúng.")
        if body.current_password == body.new_password:
            raise HTTPException(422, "Mật khẩu mới phải khác mật khẩu hiện tại.")
        salt = secrets.token_hex(16)
        value.update(salt=salt, password=password_hash(body.new_password, salt))
        db.execute("UPDATE settings SET value=? WHERE key='admin_account'", (json.dumps(value),))
    store.revoke_all_sessions()
    response.delete_cookie(COOKIE, path="/")
    return {"changed": True, "reauthenticate": True}
