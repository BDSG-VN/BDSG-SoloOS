# BDSG SoloOS v0.2.0 — CMS & AI website builder

Adds owner-operated posts and pages, typed content blocks, categories/tags, SEO metadata, image uploads, revision history and public publishing. Published snapshots stay stable while drafts are edited. An owner can select a published page as the homepage and keep the dashboard at `/admin`.

The AI writer streams a validated draft proposal through an OpenAI-compatible gateway. It never saves or publishes automatically. The gateway credential is encrypted at rest and shared with AI Studio; a configured provider with available quota is required for real generation. MCP exposes read and approved draft writes, with no publish/homepage tools.

Security checks cover owner/agent separation, CSRF, escaped public rendering, rejected unsafe links, unpublished media, conflicting edits, immutable public snapshots, revision restoration, incomplete/invalid AI outputs and real MCP confirmation.

Validation: 41 Python tests; 7 frontend tests; 2 Chromium end-to-end flows. AI upstream is mocked in automated tests. Independent review identified and verified fixes for unsaved navigation, AI overwrite of new drafts, and gateway credential downgrade. Production AI availability is a separate operational check.

See [CMS guide](CMS.md) for setup, limitations and WordPress design references. No WordPress source, PHP runtime, themes or plugins are bundled; SoloOS remains MIT.
