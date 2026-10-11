from __future__ import annotations

import asyncio
import hmac
import sys
from contextlib import asynccontextmanager, suppress
from types import SimpleNamespace

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from server.api.security import COOKIE, mint_session, owner, principal, session_data, token_hash
from server.config import ROOT, Settings
from server.core.ai_accounts import AIAccounts
from server.core.automation import Automation
from server.core.business import BusinessStore
from server.core.cms import CMSStore, ConflictError
from server.core.library import Library
from server.core.mcp_hub import MCPHub
from server.core.mcp_store import Connector, MCPStore, Permission, PolicyError
from server.core.shares import Shares
from server.core.tasks import TaskQueue
from server.core.workspace import Workspace
from server.engines.provider_specs import PROVIDERS


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(StrictModel):
    token: str = Field(max_length=512)


class ToolCall(StrictModel):
    tool: str = Field(min_length=1, max_length=128)
    arguments: dict = Field(default_factory=dict)


class Decision(StrictModel):
    approved: bool


class ConnectorInput(StrictModel):
    id: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    permission: Permission = Permission.READ_ONLY
    tools: dict[str, bool] = Field(default_factory=dict)
    enabled: bool = True
    credentials: dict[str, dict[str, str]] | None = None


class ChatInput(StrictModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation: str = Field(default="default", max_length=128)
    model: str = Field(default="solo-default", max_length=128)
    ui_prompt: str = Field(default="", max_length=50000)


class NoteInput(StrictModel):
    path: str = Field(max_length=256)
    content: str = Field(max_length=100000)


class TaskInput(StrictModel):
    title: str = Field(min_length=1, max_length=500)


class TaskMove(StrictModel):
    state: str


def create_app(settings: Settings | None = None, hub_factory=MCPHub):
    @asynccontextmanager
    async def lifespan(app):
        config = settings or Settings.from_env()
        app.state.settings = config
        app.state.store = MCPStore(config.data_dir / "system/mcp.db", config.store_key)
        app.state.hub = hub_factory(app.state.store)
        app.state.library = Library(config.data_dir / "brains")
        app.state.brain = app.state.library.brain("default")
        app.state.workspace = Workspace(
            config.data_dir / "system/workspace.db", app.state.brain, app.state.library
        )
        app.state.shares = Shares(config.data_dir / "system/shares.db")
        app.state.tasks = TaskQueue(config.data_dir / "system/tasks.db")
        app.state.business = BusinessStore(config.data_dir / "system/business.db", config.store_key)
        app.state.cms = CMSStore(config.data_dir / "system/cms.db", config.store_key)
        app.state.ai = AIAccounts(config.data_dir / "system/ai.db", config.store_key)
        if not any(c["id"] == "second-brain" for c in app.state.store.connectors()):
            app.state.store.put_connector(
                Connector(
                    id="second-brain",
                    command=sys.executable,
                    args=["-m", "server.plugins.brain_mcp"],
                    permission=Permission.REQUIRES_CONFIRMATION,
                    tools={"list_notes": True, "read_note": True, "write_note": False},
                ),
                {"env": {"BDSG_BRAIN_DIR": str(app.state.brain.root), "PYTHONPATH": str(ROOT)}},
            )
        for connector_id, permission, tools in (
            (
                "business-read",
                Permission.READ_ONLY,
                {"list_customers": True, "list_inbox": True, "business_analytics": True},
            ),
            (
                "business-write",
                Permission.REQUIRES_CONFIRMATION,
                {"create_customer": False, "create_campaign": False, "create_ticket": False},
            ),
        ):
            if not any(c["id"] == connector_id for c in app.state.store.connectors()):
                app.state.store.put_connector(
                    Connector(
                        id=connector_id,
                        command=sys.executable,
                        args=["-m", "server.plugins.business_mcp"],
                        permission=permission,
                        tools=tools,
                    ),
                    {
                        "env": {
                            "BDSG_BUSINESS_DB": str(config.data_dir / "system/business.db"),
                            "BDSG_STORE_KEY": config.store_key,
                            "PYTHONPATH": str(ROOT),
                        }
                    },
                )
        for connector_id, permission, tools in (
            ("cms-read", Permission.READ_ONLY, {"list_content": True}),
            ("cms-write", Permission.REQUIRES_CONFIRMATION, {"save_content_draft": False}),
        ):
            if not any(c["id"] == connector_id for c in app.state.store.connectors()):
                app.state.store.put_connector(
                    Connector(
                        id=connector_id,
                        command=sys.executable,
                        args=["-m", "server.plugins.cms_mcp"],
                        permission=permission,
                        tools=tools,
                    ),
                    {
                        "env": {
                            "BDSG_CMS_DB": str(config.data_dir / "system/cms.db"),
                            "PYTHONPATH": str(ROOT),
                        }
                    },
                )
        app.state.automation = Automation(config.data_dir / "system/automation.db")
        app.state.hub.execution_guard = app.state.automation.active
        from server.engines.automation import worker

        task = asyncio.create_task(worker(app.state))
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="BDSG Solo-OS",
        version="0.4.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # Middleware configuration is read at construction; production must provide env before import.
    config = settings or Settings.from_env()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(config.hosts))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )

    @app.middleware("http")
    async def security(request: Request, call_next):
        if request.url.path.startswith("/api/") and request.method != "OPTIONS":
            client = request.client.host if request.client else "unknown"
            login_attempt = request.url.path == "/api/session" and request.method == "POST"
            bucket = ("login:" if login_attempt else "api:") + client
            if not request.app.state.store.rate_limit(bucket, 10 if login_attempt else 240):
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
        unsafe = request.method not in {"GET", "HEAD", "OPTIONS"}
        origin = request.headers.get("origin")
        if unsafe:
            if origin and origin not in config.origins:
                return JSONResponse({"detail": "Untrusted origin"}, status_code=403)
            if request.url.path == "/api/session" and request.method == "POST" and not origin:
                return JSONResponse({"detail": "Login requires an allowed Origin"}, status_code=403)
            login_route = request.url.path == "/api/session" and request.method == "POST"
            if not request.headers.get("authorization") and not login_route:
                data = session_data(request)
                csrf = request.headers.get("x-csrf-token", "")
                if data and not hmac.compare_digest(csrf.encode(), data["csrf"].encode()):
                    return JSONResponse({"detail": "Invalid CSRF token"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
        if config.secure_cookies:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.exception_handler(PolicyError)
    async def policy_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=403)

    from server.engines.chatgpt_auth import SignInError

    @app.exception_handler(SignInError)
    async def sign_in_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(ConflictError)
    async def conflict_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        return JSONResponse({"detail": "Invalid input or configuration"}, status_code=422)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.4.0"}

    @app.post("/api/session")
    def login(body: Login, request: Request, response: Response):
        if not hmac.compare_digest(
            body.token.encode(), request.app.state.settings.owner_token.encode()
        ):
            raise HTTPException(401, "Invalid owner token")
        response.set_cookie(
            COOKIE,
            mint_session(config, request.app.state.store),
            httponly=True,
            secure=config.secure_cookies,
            samesite="strict",
            max_age=43200,
            path="/",
        )
        return {"authenticated": True}

    @app.get("/api/session", dependencies=[Depends(owner)])
    def session(request: Request):
        data = session_data(request)
        return {"authenticated": True, "csrf": data["csrf"] if data else None}

    @app.delete("/api/session", dependencies=[Depends(owner)])
    def logout(request: Request, response: Response):
        if request.cookies.get(COOKIE):
            request.app.state.store.revoke_session(token_hash(request.cookies[COOKIE]))
        response.delete_cookie(COOKIE, path="/")
        return {"authenticated": False}

    @app.get("/api/mcp/connectors", dependencies=[Depends(owner)])
    def connectors(request: Request):
        return request.app.state.store.connectors()

    @app.put("/api/mcp/connectors", dependencies=[Depends(owner)])
    def configure(body: ConnectorInput, request: Request):
        data = body.model_dump(exclude={"credentials"})
        request.app.state.store.put_connector(Connector(**data), body.credentials)
        return {"id": body.id, "configured": True}

    @app.get("/api/mcp/{connector_id}/tools", dependencies=[Depends(principal)])
    async def list_tools(connector_id: str, request: Request):
        return await request.app.state.hub.list_tools(connector_id)

    @app.post("/api/mcp/{connector_id}/call")
    async def call(connector_id: str, body: ToolCall, request: Request, actor=Depends(principal)):
        return await request.app.state.hub.call_tool(
            connector_id, body.tool, body.arguments, actor=actor
        )

    @app.get("/api/confirmations", dependencies=[Depends(owner)])
    def confirmations(request: Request):
        return request.app.state.store.confirmations()

    @app.post("/api/confirmations/{confirmation_id}/decision", dependencies=[Depends(owner)])
    async def decide(confirmation_id: str, body: Decision, request: Request):
        store = request.app.state.store
        # The owner executes the saved payload on behalf of its original requester.
        pending = next((r for r in store.confirmations() if r["id"] == confirmation_id), None)
        if not pending:
            raise PolicyError("Confirmation no longer pending")
        store.decide(confirmation_id, body.approved, "owner")
        if not body.approved:
            request.app.state.automation.settle(confirmation_id, {"status": "rejected"})
            request.app.state.business.settle_confirmation(confirmation_id, {"status": "rejected"})
            return {"status": "rejected"}
        try:
            result = await request.app.state.hub.execute_confirmation(
                confirmation_id, actor=pending["payload"]["actor"]
            )
        except BaseException:
            request.app.state.automation.settle(confirmation_id, {"status": "uncertain"})
            request.app.state.business.settle_confirmation(confirmation_id, {"status": "uncertain"})
            raise
        request.app.state.automation.settle(confirmation_id, result)
        request.app.state.business.settle_confirmation(confirmation_id, result)
        return result

    @app.get("/api/brain", dependencies=[Depends(owner)])
    def notes(request: Request):
        return request.app.state.brain.notes()

    @app.post("/api/brain", dependencies=[Depends(owner)])
    async def save_note(body: NoteInput, request: Request):
        # Owner-initiated saves still pass through the same Hub policy as model calls.
        return await request.app.state.hub.call_tool(
            "second-brain", "write_note", body.model_dump(), actor="owner"
        )

    @app.get("/api/tasks", dependencies=[Depends(owner)])
    def tasks(request: Request):
        return request.app.state.tasks.list()

    @app.post("/api/tasks", dependencies=[Depends(owner)])
    def create_task(body: TaskInput, request: Request):
        return request.app.state.tasks.create(body.title)

    @app.patch("/api/tasks/{task_id}", dependencies=[Depends(owner)])
    def move_task(task_id: str, body: TaskMove, request: Request):
        return request.app.state.tasks.move(task_id, body.state)

    @app.get("/api/engines", dependencies=[Depends(owner)])
    async def engines(request: Request):
        gateway = request.app.state.cms.gateway()
        active = request.app.state.ai.setting("active_account", "gateway")
        if active == "claude-native":
            from server.engines.claude_native import status

            connected = (await status())["connected"]
        else:
            connected = active != "gateway" and request.app.state.ai.account(active)["connected"]

        return {
            "providers": PROVIDERS,
            "model": gateway["model"]
            if active == "gateway"
            else request.app.state.ai.setting("model:" + active, "") or "solo-default",
            "configured": bool(gateway["base_url"]) if active == "gateway" else bool(connected),
            "active_account": active,
        }

    @app.get("/api/conversations/{conversation}", dependencies=[Depends(owner)])
    def history(conversation: str, request: Request):
        return request.app.state.brain.messages(conversation)

    @app.post("/api/chat", dependencies=[Depends(owner)])
    async def chat(body: ChatInput, request: Request):
        from server.engines.router import stream_chat

        request.app.state.workspace.context(body.conversation)
        session = request.app.state.workspace.get("sessions", body.conversation)
        brain_id = session.get("brain_id", "default")
        scoped = SimpleNamespace(**request.app.state._state)
        scoped.notes_brain = request.app.state.library.brain(brain_id)
        scoped.brain_connector = "second-brain" if brain_id == "default" else "brain-" + brain_id
        return StreamingResponse(
            stream_chat(body, scoped),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    @app.get("/api/demo/stream", dependencies=[Depends(owner)])
    async def demo():
        from server.engines.router import demo_stream

        return StreamingResponse(
            demo_stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
        )

    from server.api.business import router as business_router
    from server.api.business import webhooks

    app.include_router(business_router)
    app.include_router(webhooks)
    from server.api.ai import router as ai_router
    from server.api.automation import router as automation_router
    from server.api.cms import public as cms_public
    from server.api.cms import router as cms_router
    from server.api.library import router as library_router
    from server.api.shares import router as shares_router
    from server.api.workspace import router as workspace_router

    app.include_router(shares_router)
    app.include_router(library_router)
    app.include_router(automation_router)
    app.include_router(workspace_router)
    app.include_router(ai_router)
    app.include_router(cms_router)
    app.include_router(cms_public)

    @app.get("/share/{token}")
    def shared_page(token: str, request: Request):
        from fastapi.responses import FileResponse

        try:
            request.app.state.shares.get(token)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return FileResponse(
            ROOT / "dashboard/dist/index.html",
            headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"},
        )

    dist = ROOT / "dashboard/dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="dashboard")
    return app


# uvicorn server.main:create_app --factory; no secrets are generated implicitly on import.
