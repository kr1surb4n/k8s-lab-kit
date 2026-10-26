#!/usr/bin/env python3
"""Receive Alertmanager webhook deliveries and expose what arrived.

No dependencies: the image is python:3.12-alpine and the script is mounted from
a ConfigMap. The last 50 deliveries are kept in memory for inspection.
"""
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_DELIVERIES = 50
deliveries = []


# Send one JSON response with an explicit length.
def send_json(handler, status, payload):
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


# Reduce an Alertmanager payload to the fields this lab cares about.
def summarise(payload):
    return {
        "status": payload.get("status"),
        "receiver": payload.get("receiver"),
        "alerts": [
            {
                "name": alert.get("labels", {}).get("alertname"),
                "state": alert.get("status"),
                "summary": alert.get("annotations", {}).get("summary"),
            }
            for alert in payload.get("alerts", [])
        ],
    }


class Handler(BaseHTTPRequestHandler):
    # Answer the health and inspection endpoints.
    def do_GET(self):
        if self.path == "/healthz":
            send_json(self, 200, {"status": "ok", "received": len(deliveries)})
        elif self.path == "/alerts":
            send_json(self, 200, {"count": len(deliveries), "alerts": deliveries})
        else:
            send_json(self, 404, {"error": "not found"})

    # Accept one Alertmanager delivery and keep a bounded summary.
    def do_POST(self):
        if self.path != "/alert":
            send_json(self, 404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            send_json(self, 400, {"error": "invalid json"})
            return

        entry = summarise(payload)
        deliveries.append(entry)
        # Keep only the newest deliveries, so memory stays bounded.
        del deliveries[:-MAX_DELIVERIES]
        logging.info("alert delivery: %s", json.dumps(entry))
        send_json(self, 200, {"status": "received", "count": len(deliveries)})

    # Log requests in one line instead of the default two.
    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.address_string(), fmt % args)


# Start the HTTP server and serve until the pod stops.
def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    logging.info("alert webhook listening on :%s", port)
    server.serve_forever()


if __name__ == "__main__":
    main()
