# Vietnamese and English

SoloOS includes Vietnamese (`vi`) and English (`en`) interface translations. Use the language selector on the admin sign-in screen or dashboard header. The selection persists on the current browser; switching languages keeps the active screen and unsaved form values.

The dashboard resolves a supported `?lang=vi|en` parameter first, then the saved language cookie, browser storage, and browser language. Server-rendered pages use the query parameter, cookie, and `Accept-Language` header, in that order. Unsupported languages fall back to Vietnamese. API requests from the dashboard include the selected language. The server returns `Content-Language` and language-aware `Vary` headers.

## Translation boundaries

Application labels, navigation, forms, date/number formatting, public account controls and theme descriptions are localized. Posts, page blocks, project names, chat messages, knowledge files and other user content are preserved exactly as entered. Changing the interface language does not translate existing content or spend AI credits. A newly generated starter page uses the current request language.

## Add or update translations

- Frontend: `dashboard/i18n/en.json`, called explicitly with `t` from `dashboard/i18n/runtime.js`. Vietnamese source labels are the fallback. Dynamic values use numbered placeholders such as `{0}`; preserve these in translations.
- Backend: `server/core/locales/en.json`, called with `t` from `server/core/i18n.py`. Request state uses a `ContextVar` to isolate concurrent visitors.
- Render user content as data, never as translation keys or executable HTML. `static_html` is only for literal application templates before user values are inserted.
- Add a locale to both supported-locale lists and language selectors when extending beyond Vietnamese/English.

Validate with `cd dashboard && npm test && npm run build` and `uv run pytest tests/test_i18n.py tests/test_cms.py tests/test_site.py` from the repository root.
