"""Vercel serverless entry point: Telegram POSTs each new message here."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bot  # noqa: E402

SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
_seen_updates = set()  # Telegram may retry slow deliveries; skip ones already handled.


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._reply(200, "Skin content bot is running. Message it on Telegram: "
                         "https://t.me/Skincontent_assignmentmesa_bot")

    def do_POST(self):
        if SECRET and self.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET:
            self._reply(401, "unauthorized")
            return
        length = int(self.headers.get("Content-Length", 0))
        update = json.loads(self.rfile.read(length) or b"{}")
        update_id = update.get("update_id")
        if update_id not in _seen_updates and "message" in update:
            _seen_updates.add(update_id)
            bot.handle(update["message"])
        self._reply(200, "ok")

    def _reply(self, code, text):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(text.encode())
