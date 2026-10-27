"""Private smoke-test readiness probe, not an Agent Factory API."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path not in ("/healthz", "/readyz"):
            self.send_error(404)
            return
        payload = json.dumps({
            "kind": "agent-engine-integration-gate",
            "status": "all-required-checks-passed",
            "production_ready": False,
        }, separators=(",", ":")).encode("ascii")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return  # Do not log query tokens from accidental inbound requests.


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    if not 1 <= port <= 65535:
        raise RuntimeError("Invalid Railway PORT")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
