"""Tiny read-only HTTP server exposing the agent's data for the fomp website.

GET /trades     -> full trade log
GET /positions  -> open positions
GET /summary    -> aggregate stats

Run: python stats_server.py
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

import config
from agent import tracker


def _read(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/trades":
            body = _read(config.TRADES_FILE, [])
        elif self.path == "/positions":
            body = _read(config.POSITIONS_FILE, {"positions": []})
        elif self.path == "/summary":
            body = tracker.summary()
        else:
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", config.STATS_SERVER_PORT), Handler)
    print(f"fomp-fomo-agent stats on http://localhost:{config.STATS_SERVER_PORT}")
    server.serve_forever()
