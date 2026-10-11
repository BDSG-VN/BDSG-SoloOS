from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from server.api.security import owner
from server.core.devices import Pairing

router = APIRouter(prefix="/api/devices")


class Redeem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=20, max_length=100)


@router.get("", dependencies=[Depends(owner)])
def listing(request: Request):
    return request.app.state.devices.list()


@router.post("/pair", dependencies=[Depends(owner)])
def pair(body: Pairing, request: Request):
    return request.app.state.devices.pair(body)


@router.post("/redeem")
def redeem(body: Redeem, request: Request):
    client = request.client.host if request.client else "unknown"
    if not request.app.state.store.rate_limit("device-pair:" + client, 10):
        raise HTTPException(429, "Thử lại sau một phút.", headers={"Retry-After": "60"})
    return request.app.state.devices.redeem(body.code)


@router.delete("/self", dependencies=[Depends(owner)])
def disconnect_self(request: Request):
    identifier = getattr(request.state, "device_id", None)
    if not identifier:
        raise HTTPException(400, "Cần dùng thông tin đăng nhập của thiết bị.")
    return request.app.state.devices.revoke(identifier)


@router.delete("/{identifier}", dependencies=[Depends(owner)])
def revoke(identifier: str, request: Request):
    return request.app.state.devices.revoke(identifier)
