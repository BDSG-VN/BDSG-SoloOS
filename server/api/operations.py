"""Owner-only operational view. Counts come from stored state, never fabricated probes."""

import json
import sqlite3
import time

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from server.api.security import owner

router = APIRouter(prefix="/api/operations", dependencies=[Depends(owner)])


class ReadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[str] = Field(max_length=200)


def database(state):
    db = sqlite3.connect(state.settings.data_dir / "system/operations.db")
    db.execute("CREATE TABLE IF NOT EXISTS acknowledged(id TEXT PRIMARY KEY,created REAL NOT NULL)")
    return db


@router.get("")
def overview(request: Request):
    state = request.app.state
    runs = state.automation.runs()
    counts = {
        status: sum(r["status"] == status for r in runs)
        for status in (
            "queued",
            "running",
            "waiting",
            "completed",
            "failed",
            "uncertain",
            "cancelled",
        )
    }
    db = database(state)
    try:
        seen = {r[0] for r in db.execute("SELECT id FROM acknowledged")}
    finally:
        db.close()
    notices = [
        {
            "id": r["id"] + ":" + r["status"],
            "title": r["definition"]["title"],
            "status": r["status"],
            "updated": r["updated"],
            "error": r["error"],
            "read": r["id"] + ":" + r["status"] in seen,
        }
        for r in runs
        if r["status"] in {"waiting", "completed", "failed", "uncertain"}
    ]
    connectors = state.store.connectors()
    active = state.ai.setting("active_account", "gateway")
    configured = (
        bool(state.cms.gateway()["base_url"])
        if active == "gateway"
        else (None if active == "claude-native" else state.ai.account(active)["connected"])
    )
    return {
        "time": time.time(),
        "runs": counts,
        "window": "200 lượt chạy gần nhất",
        "notifications": notices,
        "checks": [
            {
                "name": "Nguồn AI",
                "status": "ready"
                if configured
                else "unknown"
                if configured is None
                else "needs_setup",
                "detail": "Claude cần kiểm tra CLI riêng"
                if configured is None
                else "Đã có cấu hình, chưa kiểm tra hạn mức"
                if configured
                else "Chưa kết nối nguồn AI",
                "page": "accounts",
            },
            {
                "name": "Công cụ",
                "status": "ready",
                "detail": f"{sum(c['enabled'] for c in connectors)} kết nối đang bật; chưa kiểm tra mạng",
                "page": "mcp",
            },
            {
                "name": "Lịch tự động",
                "status": "ready",
                "detail": f"{sum(s['enabled'] for s in state.automation.schedules())} lịch đang bật",
                "page": "automation",
            },
            {
                "name": "Bộ nhớ",
                "status": "ready",
                "detail": f"{len(state.library.list())} bộ nhớ",
                "page": "library",
            },
        ],
    }


@router.post("/read")
def mark_read(body: ReadInput, request: Request):
    if any(len(identifier) > 100 for identifier in body.ids):
        raise ValueError("Mã thông báo không hợp lệ.")
    db = database(request.app.state)
    try:
        with db:
            db.executemany(
                "INSERT OR REPLACE INTO acknowledged VALUES(?,?)",
                [(i, time.time()) for i in body.ids],
            )
            db.execute("DELETE FROM acknowledged WHERE created<?", (time.time() - 90 * 86400,))
    finally:
        db.close()
    return {"read": len(body.ids)}


@router.get("/export")
def export(request: Request):
    from fastapi.responses import Response

    data = overview(request)
    # Export operational metadata only, excluding prompts, results, tokens and personal memories.
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="soloos-operations.json"',
            "Cache-Control": "no-store",
        },
    )
