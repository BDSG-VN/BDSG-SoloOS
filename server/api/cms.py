"""Owner-only editorial API and explicitly published public documents."""

import io
import re
import time
import uuid
import warnings
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from server.api.security import owner
from server.config import ROOT
from server.core.cms import ContentInput
from server.core.cms_render import document_page, news_page

router = APIRouter(prefix="/api/cms", dependencies=[Depends(owner)])
public = APIRouter()


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Save(Input):
    content: ContentInput
    expected_version: int = Field(ge=1)


class Transition(Input):
    action: Literal["publish", "unpublish", "trash", "restore"]
    expected_version: int = Field(ge=1)


class Revision(Input):
    revision: int = Field(ge=1)
    expected_version: int = Field(ge=1)


class Homepage(Input):
    content_id: str | None = None


class Gateway(Input):
    base_url: str = Field(min_length=1, max_length=2000)
    model: str = Field(min_length=1, max_length=200)
    api_key: str | None = Field(default=None, max_length=4096)


class Generate(Input):
    instruction: str = Field(min_length=1, max_length=12000)
    kind: Literal["post", "page"] = "post"
    content_id: str | None = None
    reference_text: str = Field(default="", max_length=50000)
    sources: list[str] = Field(default_factory=list, max_length=20)


@router.get("/content")
def listing(request: Request, kind: str | None = None, search: str = "", status: str | None = None):
    return request.app.state.cms.list(kind, search[:250], status)


@router.post("/content")
def create(body: ContentInput, request: Request):
    return request.app.state.cms.save(body.model_dump())


@router.get("/content/{content_id}")
def read(content_id: str, request: Request):
    return request.app.state.cms.get(content_id)


@router.put("/content/{content_id}")
def save(content_id: str, body: Save, request: Request):
    return request.app.state.cms.save(body.content.model_dump(), content_id, body.expected_version)


@router.post("/content/{content_id}/transition")
def transition(content_id: str, body: Transition, request: Request):
    return request.app.state.cms.transition(content_id, body.expected_version, body.action)


@router.get("/content/{content_id}/revisions")
def revisions(content_id: str, request: Request):
    return request.app.state.cms.revisions(content_id)


@router.post("/content/{content_id}/restore-revision")
def restore_revision(content_id: str, body: Revision, request: Request):
    return request.app.state.cms.restore_revision(content_id, body.revision, body.expected_version)


@router.get("/content/{content_id}/preview")
def preview(content_id: str, request: Request):
    return HTMLResponse(
        document_page(request.app.state.cms.get(content_id), preview=True),
        headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"},
    )


@router.get("/settings")
async def settings(request: Request):
    cms = request.app.state.cms
    gateway = cms.gateway()
    homepage = cms.homepage()
    active = request.app.state.ai.setting("active_account", "gateway")
    chatgpt_connected = (
        active not in {"gateway", "claude-native"}
        and request.app.state.ai.account(active)["connected"]
    )
    if active == "claude-native":
        from server.engines.claude_native import status

        connected = (await status())["connected"]
    else:
        connected = bool(gateway["base_url"]) if active == "gateway" else bool(chatgpt_connected)
    return {
        "homepage_id": homepage["id"] if homepage else None,
        "gateway": {
            "base_url": gateway["base_url"],
            "model": gateway["model"],
            "has_api_key": bool(gateway["api_key"]),
            "configured": connected,
            "active_provider": "chatgpt" if chatgpt_connected else active,
        },
    }


@router.put("/homepage")
def homepage(body: Homepage, request: Request):
    request.app.state.cms.set_homepage(body.content_id)
    return {"homepage_id": body.content_id}


@router.put("/gateway")
def gateway(body: Gateway, request: Request):
    request.app.state.cms.configure_gateway(**body.model_dump())
    return {"configured": True}


@router.post("/generate")
async def generate(body: Generate, request: Request):
    from server.engines.cms_writer import generate_content

    # Validate references before opening a streaming response.
    ContentInput(title="References", sources=body.sources)
    if body.content_id:
        current = request.app.state.cms.get(body.content_id)
        if current["status"] == "trash":
            raise ValueError("Restore content before editing")
    return StreamingResponse(
        generate_content(body, request.app.state),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )


@router.get("/media")
def media_list(request: Request):
    with request.app.state.cms.db() as db:
        return [dict(row) for row in db.execute("SELECT * FROM media ORDER BY created DESC")]


@router.post("/media")
async def upload(request: Request):
    if request.headers.get("content-type", "").split(";")[0] not in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        raise HTTPException(415, "Use JPEG, PNG or WebP")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 5 * 1024 * 1024:
            raise HTTPException(413, "Maximum upload is 5 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if (
                    source.format not in {"JPEG", "PNG", "WEBP"}
                    or source.width * source.height > 20_000_000
                ):
                    raise ValueError("Image too large or unsupported")
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGBA")
                image.thumbnail((2560, 2560))
                output = io.BytesIO()
                image.save(output, format="WEBP", quality=85)
                width, height = image.size
    except (
        ValueError,
        OSError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise HTTPException(422, "Invalid image or more than 20 million pixels") from exc
    filename = uuid.uuid4().hex + ".webp"
    folder = request.app.state.settings.data_dir / "media"
    folder.mkdir(exist_ok=True, mode=0o700)
    path = folder / filename
    path.write_bytes(output.getvalue())
    path.chmod(0o600)
    with request.app.state.cms.db() as db:
        db.execute(
            "INSERT INTO media VALUES(?,?,?,?,?,?)",
            (filename, filename, path.stat().st_size, width, height, time.time()),
        )
    return {"filename": filename, "src": "/media/" + filename, "width": width, "height": height}


def media_file(filename, request):
    if not re.fullmatch(r"[a-f0-9]{32}\.webp", filename):
        raise HTTPException(404)
    path = request.app.state.settings.data_dir / "media" / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "no-store"})


@router.get("/media/{filename}")
def private_media(filename: str, request: Request):
    return media_file(filename, request)


@public.get("/media/{filename}")
def published_media(filename: str, request: Request):
    referenced = any(
        block.get("src") == "/media/" + filename and block["type"] == "image"
        for doc in request.app.state.cms.public()
        for block in doc["blocks"]
    )
    if not referenced:
        raise HTTPException(404)
    return media_file(filename, request)


@public.get("/news", response_class=HTMLResponse)
def news(request: Request, category: str = ""):
    return news_page(request.app.state.cms.public("post"), category)


@public.get("/news/{slug}", response_class=HTMLResponse)
def post_page(slug: str, request: Request):
    docs = request.app.state.cms.public("post", slug)
    if not docs:
        raise HTTPException(404)
    return document_page(docs[0])


@public.get("/pages/{slug}", response_class=HTMLResponse)
def page(slug: str, request: Request):
    docs = request.app.state.cms.public("page", slug)
    if not docs:
        raise HTTPException(404)
    return document_page(docs[0])


def dashboard():
    path = ROOT / "dashboard/dist/index.html"
    if not path.exists():
        raise HTTPException(503, "Build the dashboard first")
    return FileResponse(
        path, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"}
    )


@public.get("/admin")
@public.get("/admin/")
def admin():
    return dashboard()


@public.get("/", response_class=HTMLResponse)
def home(request: Request):
    doc = request.app.state.cms.homepage()
    return document_page(doc) if doc else dashboard()
