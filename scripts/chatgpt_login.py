#!/usr/bin/env python3
"""Local loopback relay for the official ChatGPT OAuth flow; never receives AI tokens."""

import argparse
import http.server
import secrets
import threading
import urllib.parse
import webbrowser


def main():
    parser = argparse.ArgumentParser(description="Connect a ChatGPT plan to your own SoloOS server")
    parser.add_argument("--site", required=True, help="HTTPS address of your SoloOS installation")
    args = parser.parse_args()
    site = urllib.parse.urlsplit(args.site)
    if (
        site.scheme != "https"
        or not site.hostname
        or site.username
        or site.query
        or site.fragment
        or site.path not in {"", "/"}
    ):
        parser.error("--site must be the HTTPS origin of your own SoloOS server")
    origin = args.site.rstrip("/")
    relay = secrets.token_urlsafe(32)

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Authorization codes and state must never appear in logs.

        def do_GET(self):
            parsed = urllib.parse.urlsplit(self.path)
            if (
                self.headers.get("Host") != "127.0.0.1:1455"
                or parsed.path != "/auth/callback"
                or len(self.path) > 16000
            ):
                self.send_error(404)
                return
            query = urllib.parse.parse_qs(parsed.query)
            if "state" not in query or not ("code" in query or "error" in query):
                self.send_error(400)
                return
            callback = "http://127.0.0.1:1455" + self.path
            # Fragment stays out of HTTP access logs. SoloOS validates state/nonce/PKCE and identity.
            target = origin + "/admin#chatgpt-callback=" + urllib.parse.quote(callback, safe="")
            self.send_response(303)
            self.send_header("Location", target)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Length", "0")
            self.end_headers()
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    server = http.server.HTTPServer(("127.0.0.1", 1455), Handler)
    print(
        "Local login relay ready. Complete sign-in in your browser. No API key is required.",
        flush=True,
    )
    webbrowser.open(origin + "/admin#connect-chatgpt=" + relay)
    timeout = threading.Timer(600, server.shutdown)
    timeout.daemon = True
    timeout.start()
    try:
        server.serve_forever()
    finally:
        timeout.cancel()
        server.server_close()


if __name__ == "__main__":
    main()
