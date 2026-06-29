#!/usr/bin/env python3
"""One-time helper: obtain a Spotify *refresh token* via the Authorization Code flow.

What it does
------------
1. Reads client_id / client_secret / redirect_uri from config.json.
2. Opens your browser to the Spotify consent screen.
3. Captures the redirect on a tiny local web server.
4. Exchanges the returned code for tokens.
5. Writes the long-lived refresh_token back into config.json.

You only ever need to run this once (re-run it if you revoke access or change scopes).

    python get_spotify_token.py
"""
from __future__ import annotations

import base64
import html
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")

# Scopes needed to read what's currently playing and the exact playback position.
SCOPES = "user-read-currently-playing user-read-playback-state"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

_result: dict[str, str] = {}
_expected_state = secrets.token_urlsafe(16)


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server API)
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = (params.get("code") or [""])[0]
        error = (params.get("error") or [""])[0]
        # Only record requests that actually carry the OAuth result, so a stray
        # request (e.g. /favicon.ico) can't clobber a captured code with blanks.
        if code or error:
            _result["code"] = code
            _result["state"] = (params.get("state") or [""])[0]
            _result["error"] = error
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        # html.escape the reflected value — never write query-string input raw.
        msg = ("Authorization failed: " + html.escape(error)) if error else \
            "Authorized! You can close this tab and return to the terminal."
        self.wfile.write(f"<html><body style='font-family:sans-serif'><h2>{msg}</h2></body></html>".encode())

    def log_message(self, *_):  # silence the default request logging
        pass


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        sys.exit("config.json not found. Copy config.example.json to config.json and fill in your Spotify "
                 "client_id / client_secret first.")
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def main() -> None:
    cfg = load_config()
    sp = cfg.get("spotify", {})
    client_id = sp.get("client_id", "")
    client_secret = sp.get("client_secret", "")
    redirect_uri = sp.get("redirect_uri", "http://127.0.0.1:8888/callback")

    if not client_id or client_id.startswith("YOUR_"):
        sys.exit("Set spotify.client_id in config.json first (from the Spotify Developer Dashboard).")
    if not client_secret or client_secret.startswith("YOUR_"):
        sys.exit("Set spotify.client_secret in config.json first.")

    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8888
    if host not in ("127.0.0.1", "localhost", "::1"):
        sys.exit(f"redirect_uri host must be loopback (got {host!r}). Use http://127.0.0.1:8888/callback.")

    # Bind only to loopback so nothing on the network can reach this server.
    server = HTTPServer((host, port), _CallbackHandler)

    def _serve() -> None:
        # Handle requests until we capture the OAuth result (ignores stray hits).
        while "code" not in _result and not _result.get("error"):
            server.handle_request()

    threading.Thread(target=_serve, daemon=True).start()

    query = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": _expected_state,
        "show_dialog": "false",
    })
    auth_link = f"{AUTH_URL}?{query}"
    print("Opening your browser to authorize Spotify...")
    print("If it doesn't open, paste this into your browser:\n", auth_link, "\n")
    webbrowser.open(auth_link)

    print(f"Waiting for the redirect on {redirect_uri} ...")
    deadline = time.time() + 300
    while "code" not in _result and not _result.get("error") and time.time() < deadline:
        time.sleep(0.25)

    if _result.get("error"):
        sys.exit(f"Spotify returned an error: {_result['error']}")
    if not _result.get("code"):
        sys.exit("Timed out waiting for the Spotify redirect.")
    if _result.get("state") != _expected_state:
        sys.exit("State mismatch — aborting for safety. Try again.")

    print("Got the authorization code, exchanging it for tokens...")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": _result["code"],
            "redirect_uri": redirect_uri,
        },
        headers={"Authorization": f"Basic {basic}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    if not resp.ok:
        sys.exit(f"Token exchange failed ({resp.status_code}): {resp.text}")

    data = resp.json()
    refresh = data.get("refresh_token")
    if not refresh:
        sys.exit("No refresh_token in the response — did you already authorize? Revoke access and retry.")

    cfg["spotify"]["refresh_token"] = refresh
    save_config(cfg)
    print("\n✅ Success! refresh_token saved to config.json.")
    print("You can now run:  python widget.py")


if __name__ == "__main__":
    main()
