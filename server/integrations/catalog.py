"""Official-source capability evidence checked 2026-10-11.

Catalog metadata is not a connected account. Remote endpoints still require owner
credentials, access enrollment, discovery and an explicit tool allowlist.
"""

CATALOG = [
    {
        "id": "google_ads",
        "publisher": "Google",
        "status": "official_mcp",
        "source": "https://developers.google.com/google-ads/api/docs/developer-toolkit/mcp-server",
        "repository": "https://github.com/googleads/google-ads-mcp",
        "scope": "Account discovery and campaign reporting, read-only",
        "note": "Self-host the official server or deploy to Cloud Run; cannot create or pause ads.",
        "template": {
            "id": "google-ads",
            "transport": "streamable_http",
            "url": "https://YOUR-GOOGLE-ADS-MCP-HOST/mcp",
            "enabled": False,
            "permission": "read_only",
            "tools": {
                "search": True,
                "get_resource_metadata": True,
                "list_accessible_customers": True,
            },
        },
    },
    {
        "id": "email",
        "publisher": "Google / Gmail",
        "status": "official_mcp_preview",
        "source": "https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server",
        "scope": "Search/read threads, labels, create drafts; Developer Preview",
        "note": "Requires Google Cloud project, Gmail MCP API and preview eligibility; no send-email claim.",
        "template": {
            "id": "gmail",
            "transport": "streamable_http",
            "url": "https://gmailmcp.googleapis.com/mcp/v1",
            "enabled": False,
            "permission": "read_only",
            "tools": {"search_threads": True, "get_thread": True, "list_labels": True},
        },
    },
    {
        "id": "hotline",
        "publisher": "Twilio",
        "status": "official_docs_only",
        "source": "https://www.twilio.com/docs/ai/mcp",
        "scope": "Public API documentation, not account operation",
        "note": "Official docs MCP cannot place calls or send SMS; do not map these tools as send tools.",
        "template": {
            "id": "twilio-docs",
            "transport": "streamable_http",
            "url": "https://mcp.twilio.com/docs",
            "enabled": False,
            "permission": "read_only",
            "tools": {"twilio__search": True, "twilio__retrieve": True},
        },
    },
    *[
        {
            "id": channel,
            "publisher": publisher,
            "status": "official_mcp_not_verified",
            "source": source,
            "scope": "Official platform API documentation",
            "note": "No first-party business-operation MCP verified. No community server is auto-installed.",
            "template": None,
        }
        for channel, publisher, source in [
            ("zalo", "Zalo", "https://developers.zalo.me/docs"),
            ("facebook", "Meta", "https://developers.facebook.com/docs/messenger-platform/"),
            ("instagram", "Meta", "https://developers.facebook.com/docs/instagram-platform/"),
            (
                "tiktok",
                "TikTok",
                "https://developers.tiktok.com/doc/en/content-posting-api-get-started",
            ),
            ("sms", "Carrier-dependent", "https://developers.zalo.me/docs"),
        ]
    ],
    {
        "id": "website",
        "publisher": "Owner's website",
        "status": "owner_managed",
        "source": None,
        "scope": "Website/CRM MCP defined by the website operator",
        "note": "No universal platform issuer. Connect your website's trusted MCP server.",
        "template": None,
    },
]
