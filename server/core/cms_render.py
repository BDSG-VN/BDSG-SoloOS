"""Escaped, script-free public publishing; no model HTML/code is executed."""

from html import escape

from server.core.i18n import get_locale, static_html, t


def e(value):
    return escape(str(value), quote=True)


STYLE = """
:root{color-scheme:light;--ink:#16251e;--muted:#637068;--accent:#185c41;--paper:#fafbf8}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.75 system-ui,sans-serif}a{color:var(--accent)}header,footer{padding:24px max(24px,calc((100vw - 1120px)/2));border-bottom:1px solid #dde4db;display:flex;gap:24px;justify-content:space-between;flex-wrap:wrap}header a{text-decoration:none}main{max-width:1000px;margin:auto;padding:64px 24px 96px}h1,h2,h3{line-height:1.17;letter-spacing:-.035em}h1{font-size:clamp(36px,6vw,68px);margin:16px 0 30px}h2{font-size:34px;margin-top:52px}p{white-space:pre-wrap;overflow-wrap:anywhere}.hero{background:#e6f0e5;border-radius:24px;padding:clamp(24px,6vw,64px);margin:24px 0 48px}.hero h2{font-size:clamp(32px,5vw,56px);margin-top:0}.button{display:inline-block;background:var(--accent);color:white;padding:14px 24px;border-radius:10px;text-decoration:none}blockquote{border-left:4px solid var(--accent);padding:16px 24px;margin:32px 0;background:#f0f4ec}figure{margin:32px 0}img{max-width:100%;height:auto;border-radius:16px}small,.meta{color:var(--muted)}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:24px}.card{padding:28px;border:1px solid #dce3da;border-radius:16px}.card h2{font-size:28px;margin-top:0}.preview{padding:10px 24px;background:#fff0c7;text-align:center}.sources{font-size:15px;margin-top:64px;overflow-wrap:anywhere}footer{font-size:14px;border-top:1px solid #dde4db}ul{padding-left:24px}
"""


def render_blocks(blocks, preview=False):
    result = []
    for block in blocks:
        kind, text = block["type"], e(block.get("text", ""))
        if kind == "hero":
            result.append(
                f'<section class="hero"><h2>{text}</h2><p>{e(block.get("detail", ""))}</p></section>'
            )
        elif kind == "heading":
            result.append(f"<h2>{text}</h2>")
        elif kind == "paragraph":
            result.append(f"<p>{text}</p>")
        elif kind == "quote":
            result.append(f"<blockquote>{text}</blockquote>")
        elif kind == "list":
            result.append(
                "<ul>" + "".join("<li>" + e(v) + "</li>" for v in block.get("items", [])) + "</ul>"
            )
        elif kind == "button":
            result.append(f'<p><a class="button" href="{e(block["href"])}">{text}</a></p>')
        elif kind == "image":
            src = block["src"].replace("/media/", "/api/cms/media/") if preview else block["src"]
            result.append(
                f'<figure><img loading="lazy" src="{e(src)}" alt="{e(block.get("alt", ""))}"><figcaption>{text}</figcaption></figure>'
            )
        elif kind == "divider":
            result.append("<hr>")
    return "".join(result)


def layout(title, content, description="", preview=False, site=None):
    from server.core.site import THEMES, SiteSettings

    site = site or SiteSettings()
    theme = THEMES.get(site.theme, THEMES["personal"])
    theme_style = f":root{{--accent:{theme[2]};--paper:{theme[3]}}}"
    banner = static_html('<div class="preview">Bản xem trước riêng tư · chưa xuất bản</div>') if preview else ""
    return f'''<!doctype html><html lang="{get_locale()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><meta name="description" content="{e(description)}"><style>{STYLE}{theme_style}</style></head><body>{banner}<header><a href="/">{e(site.title)}</a><nav><a href="/news">{t("Tin tức")}</a> · <a href="/search">{t("Tìm kiếm")}</a> · <a href="/account">{t("Đăng nhập")}</a> · <a href="?lang=vi" lang="vi">Tiếng Việt</a> / <a href="?lang=en" lang="en">English</a></nav></header><main>{content}</main><footer><span>{e(site.title)}</span><span>{t("Vận hành bằng BDSG SoloOS · BDSG Foundation")}</span></footer></body></html>'''


def document_page(doc, preview=False, site=None):
    meta = " · ".join(e(v) for v in doc.get("categories", []))
    if doc.get("ai_generated"):
        meta += " · " + t("Nội dung có hỗ trợ AI")
    sources = ""
    if doc.get("sources"):
        sources = (
            static_html('<aside class="sources"><h3>Nguồn tham khảo</h3><ul>')
            + "".join(
                f'<li><a href="{e(u)}" rel="noopener noreferrer">{e(u)}</a></li>'
                for u in doc["sources"]
            )
            + "</ul></aside>"
        )
    body = (
        f'<article><div class="meta">{meta}</div><h1>{e(doc["title"])}</h1>'
        + render_blocks(doc["blocks"], preview)
        + sources
        + "</article>"
    )
    return layout(
        doc.get("seo_title") or doc["title"],
        body,
        doc.get("seo_description") or doc.get("excerpt", ""),
        preview,
        site,
    )


def news_page(posts, category="", site=None):
    categories = sorted({c for p in posts for c in p.get("categories", [])})
    from urllib.parse import quote

    filters = (
        static_html('<p><a href="/news">Tất cả</a> · ')
        + " · ".join(f'<a href="/news?category={quote(c)}">{e(c)}</a>' for c in categories)
        + "</p>"
    )
    visible = [p for p in posts if not category or category in p.get("categories", [])]
    cards = "".join(
        f'<article class="card"><h2><a href="/news/{e(p["slug"])}">{e(p["title"])}</a></h2><p>{e(p.get("excerpt", ""))}</p></article>'
        for p in visible
    )
    return layout(
        t("Tin tức"),
        static_html("<h1>Tin tức</h1>")
        + filters
        + '<div class="cards">'
        + (cards or static_html("<p>Chưa có bài viết được xuất bản.</p>"))
        + "</div>",
        site=site,
    )
