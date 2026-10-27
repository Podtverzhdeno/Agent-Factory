"""Private test-appliance readiness endpoint. Not a production API."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/readyz":
            self.send_error(404)
            return
        body = json.dumps({"kind": "agent-factory-runtime-quality-integration",
                           "status": "cross-service-tests-passed",
                           "production_ready": False}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *_args):
        return

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
