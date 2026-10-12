"""Request-scoped interface translations. Never translate user/CMS content implicitly."""

import json
from contextvars import ContextVar
from http.cookies import SimpleCookie
from pathlib import Path

from starlette.datastructures import Headers, MutableHeaders, QueryParams

SUPPORTED = ("vi", "en")
_locale = ContextVar("soloos_locale", default="vi")
EN = json.loads((Path(__file__).with_name("locales") / "en.json").read_text())


def get_locale():
    return _locale.get()


def t(message):
    return EN.get(message, message) if get_locale() == "en" else message


def resolve_locale(query="", cookie="", accept=""):
    explicit = QueryParams(query).get("lang")
    if explicit in SUPPORTED:
        return explicit
    cookies = SimpleCookie()
    try:
        cookies.load(cookie)
        saved = cookies.get("soloos_locale")
        if saved and saved.value in SUPPORTED:
            return saved.value
    except Exception:
        pass
    candidates = []
    for index, part in enumerate(accept.split(",")):
        bits = part.strip().split(";")
        code = bits[0].lower().split("-")[0]
        try:
            quality = float(
                next((v.strip()[2:] for v in bits[1:] if v.strip().startswith("q=")), "1")
            )
        except ValueError:
            continue
        if code in SUPPORTED and 0 < quality <= 1:
            candidates.append((quality, -index, code))
    return max(candidates)[2] if candidates else "vi"


class LocaleMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        query = scope.get("query_string", b"").decode("latin1")
        language = resolve_locale(
            query, headers.get("cookie", ""), headers.get("accept-language", "")
        )
        token = _locale.set(language)

        async def localized_send(message):
            if message["type"] == "http.response.start":
                out = MutableHeaders(scope=message)
                if "content-language" not in out:
                    out["Content-Language"] = language
                vary = [v.strip() for v in out.get("Vary", "").split(",") if v.strip()]
                for value in ("Accept-Language", "Cookie"):
                    if value.lower() not in [v.lower() for v in vary]:
                        vary.append(value)
                out["Vary"] = ", ".join(vary)
                if QueryParams(query).get("lang") in SUPPORTED:
                    secure = "; Secure" if scope.get("scheme") == "https" else ""
                    out.append(
                        "Set-Cookie",
                        f"soloos_locale={language}; Path=/; Max-Age=31536000; SameSite=Lax{secure}",
                    )
            await send(message)

        try:
            await self.app(scope, receive, localized_send)
        finally:
            _locale.reset(token)


def static_html(fragment):
    """Translate text in a trusted, literal UI template BEFORE inserting user values."""
    import re
    from html import escape

    return re.sub(
        r">([^<>]+)<",
        lambda m: (
            ">" + escape(t(m.group(1)), quote=False) + "<" if m.group(1) in EN else m.group(0)
        ),
        fragment,
    )
