from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from server.api.security import owner
from server.core.workspace import ProjectInput, SessionInput

router = APIRouter(prefix="/api/workspace", dependencies=[Depends(owner)])


@router.get("/projects")
def projects(request: Request):
    return request.app.state.workspace.list("projects")


@router.post("/projects")
def create_project(body: ProjectInput, request: Request):
    return request.app.state.workspace.save("projects", body)


@router.put("/projects/{identifier}")
def save_project(identifier: str, body: ProjectInput, request: Request):
    return request.app.state.workspace.save("projects", body, identifier)


@router.get("/sessions")
def sessions(
    request: Request, search: str = Query(default="", max_length=200), archived: bool = False
):
    return request.app.state.workspace.list("sessions", search, archived)


@router.post("/sessions")
def create_session(body: SessionInput, request: Request):
    return request.app.state.workspace.save("sessions", body)


@router.put("/sessions/{identifier}")
def save_session(identifier: str, body: SessionInput, request: Request):
    return request.app.state.workspace.save("sessions", body, identifier)


@router.get("/sessions/{identifier}/export")
def export_session(identifier: str, request: Request):
    session = request.app.state.workspace.get("sessions", identifier)
    return JSONResponse(
        {
            "session": session,
            "messages": request.app.state.brain.messages(identifier, limit=100000),
        },
        headers={"Content-Disposition": 'attachment; filename="soloos-conversation.json"'},
    )
