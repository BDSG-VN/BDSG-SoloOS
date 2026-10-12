import asyncio

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route

from server.core.cms_render import document_page
from server.core.i18n import LocaleMiddleware, get_locale, resolve_locale, t


def test_precedence_and_invalid_languages():
    assert resolve_locale("lang=en", "soloos_locale=vi", "vi") == "en"
    assert resolve_locale("lang=bad", "soloos_locale=en", "vi") == "en"
    assert resolve_locale("", "", "fr;q=1,en;q=0.8,vi;q=0.9") == "vi"
    assert resolve_locale("", "", "en;q=0,vi;q=0.2") == "vi"
    assert resolve_locale("lang=../../", "", "xx") == "vi"


@pytest.mark.asyncio
async def test_concurrent_requests_are_isolated_and_user_content_unchanged():
    async def endpoint(request):
        await asyncio.sleep(0.01)
        return HTMLResponse(
            document_page(
                {
                    "title": "Lưu",
                    "blocks": [
                        {"type": "paragraph", "text": "Đăng nhập <script>alert(1)</script>"}
                    ],
                }
            )
        )

    app = LocaleMiddleware(Starlette(routes=[Route("/", endpoint)]))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="https://test"
    ) as client:
        en, vi = await asyncio.gather(client.get("/?lang=en"), client.get("/?lang=vi"))
    assert '<html lang="en">' in en.text and '<html lang="vi">' in vi.text
    assert ">Sign in</a>" in en.text and ">Đăng nhập</a>" in vi.text
    assert "<h1>Lưu</h1>" in en.text
    assert "Đăng nhập &lt;script&gt;" in en.text
    assert en.headers["content-language"] == "en"
    assert "Cookie" in en.headers["vary"] and "Accept-Language" in en.headers["vary"]
    assert "Secure" in en.headers["set-cookie"]
    assert get_locale() == "vi" and t("Lưu") == "Lưu"
