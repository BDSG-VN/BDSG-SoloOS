from fastapi import APIRouter, Depends, Request

from server.api.security import owner
from server.core.automation import Agent, Schedule, Skill, Workflow
from server.core.mcp_store import PolicyError

router = APIRouter(prefix="/api/automation", dependencies=[Depends(owner)])


@router.get("")
def overview(request: Request):
    store = request.app.state.automation
    return {kind: store.definitions(kind) for kind in ("skills", "agents", "workflows")} | {
        "runs": store.runs(),
        "schedules": store.schedules(),
    }


@router.post("/skills")
def skill(body: Skill, request: Request):
    return request.app.state.automation.save("skills", body)


@router.put("/skills/{identifier}")
def update_skill(identifier: str, body: Skill, request: Request):
    return request.app.state.automation.save("skills", body, identifier)


@router.post("/agents")
def agent(body: Agent, request: Request):
    return request.app.state.automation.save("agents", body)


@router.put("/agents/{identifier}")
def update_agent(identifier: str, body: Agent, request: Request):
    return request.app.state.automation.save("agents", body, identifier)


@router.post("/workflows")
def workflow(body: Workflow, request: Request):
    return request.app.state.automation.save("workflows", body)


@router.put("/workflows/{identifier}")
def update_workflow(identifier: str, body: Workflow, request: Request):
    return request.app.state.automation.save("workflows", body, identifier)


@router.post("/workflows/{identifier}/run")
def run(identifier: str, request: Request):
    return request.app.state.automation.enqueue(identifier)


@router.post("/runs/{identifier}/cancel")
def cancel(identifier: str, request: Request):
    queue = request.app.state.automation
    run = next((r for r in queue.runs() if r["id"] == identifier), None)
    if run and run["confirmation"]:
        try:
            request.app.state.store.decide(run["confirmation"], False, "owner")
        except PolicyError:
            pass
    return queue.cancel(identifier)


@router.post("/schedules")
def schedule(body: Schedule, request: Request):
    return request.app.state.automation.schedule(body)


@router.put("/schedules/{identifier}")
def update_schedule(identifier: str, body: Schedule, request: Request):
    return request.app.state.automation.schedule(body, identifier)


@router.delete("/schedules/{identifier}")
def delete_schedule(identifier: str, request: Request):
    return request.app.state.automation.delete_schedule(identifier)


@router.post("/schedules/preview")
def preview(body: Schedule):
    import time

    cursor = time.time()
    values = []
    for _ in range(1 if body.kind == "once" else 5):
        cursor = body.next_after(cursor)
        values.append(cursor)
    return {"times": values, "timezone": body.timezone}


@router.get("/pack")
def export_pack(request: Request):
    from fastapi.responses import JSONResponse

    from server.core.bundles import export

    return JSONResponse(
        export(request.app.state.automation),
        headers={
            "Content-Disposition": 'attachment; filename="soloos-pack.json"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/pack/preview")
def preview_pack(body: dict):
    from server.core.bundles import Bundle

    bundle = Bundle.model_validate(body)
    return {
        "title": bundle.title,
        "items": {
            kind: [v.title for v in getattr(bundle, kind).values()]
            for kind in ("skills", "agents", "workflows")
        },
        "notice": "Gói sẽ được nhập ở trạng thái tắt. Trợ lý không được cấp kết nối.",
    }


@router.post("/pack/import")
def import_pack(body: dict, request: Request):
    from server.core.bundles import Bundle, install

    return install(request.app.state.automation, Bundle.model_validate(body))
