#!/usr/bin/env python3
"""Realtime Spotify lyrics -> Discord profile widget updater.

The loop, every tick:
  1. (every poll_interval) ask Spotify what's playing + the exact position.
  2. when the track changes, fetch time-synced lyrics from LRCLIB (free, no key).
  3. advance the position locally between polls using a monotonic clock.
  4. PATCH your Discord widget identity *only when the visible lyric line changes*
     (keeps us well under Discord's rate limits while still feeling realtime).

Run:   python widget.py
Stop:  Ctrl+C

Field names this script pushes (must match the Data Field names you set in the
Discord widget editor):  track, artist, album, album_art, lyric, lyric_prev,
lyric_next, progress, progress_pct, status
"""
from __future__ import annotations

import base64
import bisect
import json
import logging
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from io import BytesIO
from logging.handlers import RotatingFileHandler

import requests

# Pillow is optional — only needed for the album-art "widget fix" feature.
try:
    from PIL import Image, ImageChops, ImageDraw
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
LOG_PATH = os.path.join(HERE, "widget.log")

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
LRCLIB_GET = "https://lrclib.net/api/get"
LRCLIB_SEARCH = "https://lrclib.net/api/search"
DISCORD_API = "https://discord.com/api/v9"

UA_DISCORD = "DiscordBot (https://github.com/spotify-rpc-lyrics-widget, 1.0.0)"
UA_LRCLIB = "spotify-rpc-lyrics-widget v1.0 (personal use)"


def _build_logger() -> logging.Logger:
    """Log to a rotating file always, and to the console when one exists.

    Under pythonw.exe (background mode) there is no console — sys.stdout is None —
    so a plain print() would crash. The file handler is what makes the background
    process diagnosable; the console handler is added only when interactive.
    """
    logger = logging.getLogger("spotify_lyrics_widget")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    fmt = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    try:
        fh = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass  # e.g. read-only dir — fall back to console only
    if getattr(sys, "stdout", None) is not None:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger


_logger = _build_logger()


def log(msg: str) -> None:
    _logger.info(msg)


def die(msg: str) -> None:
    """Log a fatal startup message (so it's visible in widget.log under pythonw) then exit."""
    log("FATAL: " + msg)
    sys.exit(msg)


# Secrets/IDs may come from environment variables (preferred when hosting, so no
# secrets file sits on the server). Env values override config.json when set.
_ENV_MAP = {
    ("discord", "application_id"): "DISCORD_APPLICATION_ID",
    ("discord", "user_id"):        "DISCORD_USER_ID",
    ("discord", "bot_token"):      "DISCORD_BOT_TOKEN",
    ("spotify", "client_id"):      "SPOTIFY_CLIENT_ID",
    ("spotify", "client_secret"):  "SPOTIFY_CLIENT_SECRET",
    ("spotify", "refresh_token"):  "SPOTIFY_REFRESH_TOKEN",
    ("discord", "image_webhook_url"): "DISCORD_IMAGE_WEBHOOK_URL",
}


def load_config() -> dict:
    """Load config.json if present, then overlay any matching environment variables.

    Either source alone is enough: locally you use config.json; on a host you can
    skip the file entirely and provide the six secrets/IDs as env vars.
    """
    cfg: dict = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    cfg.setdefault("discord", {})
    cfg.setdefault("spotify", {})
    cfg.setdefault("options", {})
    for (section, key), env_name in _ENV_MAP.items():
        value = os.environ.get(env_name)
        if value:
            cfg[section][key] = value
    if not cfg["discord"].get("bot_token") or cfg["discord"]["bot_token"].startswith("YOUR_"):
        die("No Discord bot token. Set it in config.json or the DISCORD_BOT_TOKEN env var.")
    return cfg


# --------------------------------------------------------------------------- #
# Spotify                                                                      #
# --------------------------------------------------------------------------- #
@dataclass
class Track:
    id: str
    name: str
    artist: str
    album: str
    art_url: str
    duration: float   # seconds
    position: float   # seconds, as reported by Spotify at the moment of the poll
    is_playing: bool


class SpotifyClient:
    def __init__(self, cfg: dict):
        sp = cfg["spotify"]
        self.client_id = sp["client_id"]
        self.client_secret = sp["client_secret"]
        self.refresh_token = sp.get("refresh_token", "")
        self._access_token = ""
        self._expires_at = 0.0
        if not self.refresh_token:
            die("No spotify.refresh_token in config.json. Run:  python get_spotify_token.py")

    def _refresh(self) -> None:
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        resp = requests.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": self.refresh_token},
            headers={"Authorization": f"Basic {basic}",
                     "Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._expires_at = time.time() + data.get("expires_in", 3600) - 60
        if data.get("refresh_token"):
            self.refresh_token = data["refresh_token"]
        log("Spotify access token refreshed.")

    def _token(self) -> str:
        if not self._access_token or time.time() >= self._expires_at:
            self._refresh()
        return self._access_token

    def now_playing(self) -> dict | None:
        resp = requests.get(
            SPOTIFY_NOW_PLAYING_URL,
            headers={"Authorization": f"Bearer {self._token()}"},
            timeout=15,
        )
        if resp.status_code == 204:
            return None  # nothing is playing
        if resp.status_code == 401:
            self._refresh()
            resp = requests.get(
                SPOTIFY_NOW_PLAYING_URL,
                headers={"Authorization": f"Bearer {self._token()}"},
                timeout=15,
            )
            if resp.status_code == 204:
                return None
        resp.raise_for_status()
        return resp.json()


def parse_track(data: dict) -> Track | None:
    item = data.get("item")
    if not item:
        return None
    artists = ", ".join(a.get("name", "") for a in item.get("artists", []) if a.get("name"))
    album = item.get("album", {}) or {}
    images = album.get("images", []) or []
    return Track(
        id=item.get("id") or item.get("uri", "") or item.get("name", ""),
        name=item.get("name", ""),
        artist=artists,
        album=album.get("name", ""),
        art_url=images[0]["url"] if images else "",
        duration=item.get("duration_ms", 0) / 1000.0,
        position=data.get("progress_ms", 0) / 1000.0,
        is_playing=bool(data.get("is_playing")),
    )


# --------------------------------------------------------------------------- #
# Lyrics (LRCLIB)                                                              #
# --------------------------------------------------------------------------- #
_TS_RE = re.compile(r"\[(\d+):(\d+(?:[.:]\d+)?)\]")


def parse_lrc(lrc: str) -> list[tuple[float, str]]:
    out: list[tuple[float, str]] = []
    for line in lrc.splitlines():
        stamps = _TS_RE.findall(line)
        if not stamps:
            continue
        text = _TS_RE.sub("", line).strip()
        for mm, ss in stamps:
            seconds = int(mm) * 60 + float(ss.replace(":", "."))
            out.append((seconds, text))
    out.sort(key=lambda x: x[0])
    return out


class Lyrics:
    def __init__(self, lines: list[tuple[float, str]], instrumental: bool = False):
        self.lines = lines
        self.times = [t for t, _ in lines]
        self.instrumental = instrumental

    def index_at(self, pos: float) -> int:
        if not self.lines:
            return -1
        return bisect.bisect_right(self.times, pos) - 1


def fetch_lyrics(track: Track) -> Lyrics:
    primary_artist = track.artist.split(",")[0].strip() if track.artist else ""
    params = {
        "track_name": track.name,
        "artist_name": primary_artist,
        "album_name": track.album,
        "duration": int(round(track.duration)),
    }
    try:
        resp = requests.get(LRCLIB_GET, params=params, headers={"User-Agent": UA_LRCLIB}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("instrumental"):
                return Lyrics([], instrumental=True)
            if data.get("syncedLyrics"):
                return Lyrics(parse_lrc(data["syncedLyrics"]))
    except requests.RequestException as exc:
        log(f"LRCLIB get error: {exc}")

    # Fallback: fuzzy search and take the first hit that has synced lyrics.
    try:
        resp = requests.get(
            LRCLIB_SEARCH,
            params={"track_name": track.name, "artist_name": primary_artist},
            headers={"User-Agent": UA_LRCLIB},
            timeout=15,
        )
        if resp.status_code == 200:
            for hit in resp.json():
                if hit.get("syncedLyrics"):
                    return Lyrics(parse_lrc(hit["syncedLyrics"]))
    except requests.RequestException as exc:
        log(f"LRCLIB search error: {exc}")

    return Lyrics([])  # nothing found


# --------------------------------------------------------------------------- #
# Discord                                                                      #
# --------------------------------------------------------------------------- #
class DiscordWidget:
    def __init__(self, cfg: dict):
        dc = cfg["discord"]
        opt = cfg.get("options", {})
        self.url = (f"{DISCORD_API}/applications/{dc['application_id']}"
                    f"/users/{dc['user_id']}/identities/0/profile")
        self.headers = {
            "Authorization": f"Bot {dc['bot_token']}",
            "Content-Type": "application/json",
            "User-Agent": UA_DISCORD,
        }
        # Keep this many requests in the bucket unspent as a 429 safety buffer. Once
        # the bucket drops to it, we glide on the reset window instead of firing, so
        # a busy passage can never bottom out the bucket and halt the widget.
        self.reserve = max(1, int(opt.get("rate_limit_reserve", 1)))
        # Log the live rate-limit bucket on every send (so you can see the real
        # headroom in widget.log). Pacing is always logged regardless.
        self.log_rate_limits = bool(opt.get("log_rate_limits", True))

    def patch(self, username: str, dynamic: list[dict]) -> tuple[bool, float]:
        """Send one update. Returns (sent, cooldown_seconds).

        Non-blocking: never sleeps. `cooldown_seconds` is how long the caller should
        wait before the next attempt — derived from the rate-limit bucket headers on
        success (to pace evenly and avoid 429s), or from retry_after on a 429.
        """
        body = {"username": username, "data": {"dynamic": dynamic}}
        try:
            resp = requests.patch(self.url, json=body, headers=self.headers, timeout=15)
        except requests.RequestException as exc:
            log(f"Discord PATCH network error: {exc}")
            return False, 5.0

        if resp.status_code == 429:
            try:
                retry = float(resp.json().get("retry_after", 1))
            except Exception:
                retry = float(resp.headers.get("Retry-After", 1) or 1)
            return False, min(retry, 60.0)

        if not resp.ok:
            # resp.text is Discord's error body, never our token; safe to log a slice.
            log(f"Discord PATCH {resp.status_code}: {resp.text[:300]}")
            return False, 5.0

        # Success — decide how long to wait before the NEXT send. While the bucket
        # has comfortable headroom we return 0, so a fresh lyric line goes out the
        # moment it changes (the main loop still enforces min_patch_interval). Only
        # once we're down to the reserve do we glide on the reset window, so a busy
        # passage paces itself to the refill instead of slamming into a 429 and
        # halting. This is reactive instead of the old "spread evenly across the
        # whole window", which sat out a full cooldown even with budget to spare.
        cooldown = 0.0
        try:
            remaining = int(float(resp.headers.get("X-RateLimit-Remaining", "1")))
            reset_after = float(resp.headers.get("X-RateLimit-Reset-After", "0"))
            if remaining <= 0:
                cooldown = max(reset_after, 1.0) + 0.25          # empty: wait for the refill
            elif remaining <= self.reserve:
                cooldown = (reset_after / remaining) if reset_after > 0 else 1.0  # last tokens: glide
            # else: healthy budget -> cooldown stays 0, fire on the next line change
            if self.log_rate_limits or cooldown > 0:
                limit = resp.headers.get("X-RateLimit-Limit", "?")
                log(f"[ratelimit] limit={limit} remaining={remaining} "
                    f"reset_after={reset_after:.1f}s -> next send in {cooldown:.1f}s")
        except (TypeError, ValueError):
            cooldown = 0.0
        return True, min(cooldown, 60.0)


# --------------------------------------------------------------------------- #
# Album-art "widget fix" — Python port of D.W.I.F (Discord Widget Image Fixer) #
#   Adds a transparent top strip + rounds the top-right corner so the cover    #
#   sits inside the widget frame instead of bleeding past it. Algorithm and    #
#   the 512->17/36 / 1844x853->54/172 calibration are from D.W.I.F by          #
#   AjaxFNC-YT (https://github.com/AjaxFNC-YT/D.W.I.F); ported to Pillow here   #
#   so it runs anywhere Python does (no Node required).                         #
# --------------------------------------------------------------------------- #
_REF = 512
_STRIP_BASE, _RADIUS_BASE = 17, 36
_STRIP_EXP = math.log(54 / 17) / math.log(math.sqrt(1844 * 853) / _REF)
_RADIUS_EXP = math.log(172 / 36) / math.log(math.sqrt(1844 * 853) / _REF)


def _auto(base: float, exponent: float, w: int, h: int) -> int:
    return max(0, round(base * (math.sqrt(w * h) / _REF) ** exponent))


def fix_widget_image(cover: "Image.Image", top_strip: int, radius: int) -> "Image.Image":
    """Shift the image down by `top_strip` (transparent strip on top) and round the
    top-right corner by `radius`, matching D.W.I.F's single-frame transform."""
    cover = cover.convert("RGBA")
    w, h = cover.size
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(cover, (0, top_strip))                      # pasting low clips the bottom strip
    radius = min(radius, w, max(h - top_strip, 0))
    if radius > 0:
        mask = Image.new("L", (w, h), 255)
        md = ImageDraw.Draw(mask)
        md.rectangle([w - radius, top_strip, w, top_strip + radius], fill=0)   # clear corner box
        cx, cy = w - radius, top_strip + radius
        md.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=255)  # restore the quarter-circle
        r, g, b, a = canvas.split()
        canvas = Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, mask)))
    return canvas


def process_cover(raw_url: str, webhook_url: str) -> str:
    """Download the Spotify cover, apply the widget fix, upload it to a Discord
    webhook, and return the resulting CDN URL. Falls back to the original URL on
    any problem (missing Pillow, network, etc.) so album art always shows."""
    if not raw_url or not webhook_url or not _HAS_PIL:
        if raw_url and webhook_url and not _HAS_PIL:
            log("Album-art fix skipped: Pillow not installed (pip install Pillow).")
        return raw_url
    try:
        resp = requests.get(raw_url, timeout=15)
        resp.raise_for_status()
        cover = Image.open(BytesIO(resp.content)).convert("RGBA").resize((_REF, _REF), Image.LANCZOS)
        fixed = fix_widget_image(cover, _auto(_STRIP_BASE, _STRIP_EXP, _REF, _REF),
                                 _auto(_RADIUS_BASE, _RADIUS_EXP, _REF, _REF))
        buf = BytesIO()
        fixed.save(buf, format="PNG")
        sep = "&" if "?" in webhook_url else "?"
        up = requests.post(f"{webhook_url}{sep}wait=true",
                           files={"file": ("cover.png", buf.getvalue(), "image/png")}, timeout=20)
        up.raise_for_status()
        url = up.json()["attachments"][0]["url"]
        log("Fixed + hosted album art via webhook.")
        return url
    except Exception as exc:  # noqa: BLE001 — never let art break the loop
        log(f"Album-art fix failed ({exc}); using the original cover.")
        return raw_url


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def build_dynamic(track: Track, line: str, prev: str, nxt: str,
                  pos: float, status: str, no_lyrics_text: str, art_url: str) -> list[dict]:
    pct = int(max(0, min(100, (pos / track.duration * 100) if track.duration else 0)))
    dynamic = [
        {"type": 1, "name": "track", "value": track.name or "Unknown"},
        {"type": 1, "name": "artist", "value": track.artist or "Unknown"},
        {"type": 1, "name": "album", "value": track.album or ""},
        {"type": 1, "name": "lyric", "value": line or no_lyrics_text},
        {"type": 1, "name": "lyric_prev", "value": prev},
        {"type": 1, "name": "lyric_next", "value": nxt},
        {"type": 1, "name": "progress", "value": f"{fmt_time(pos)} / {fmt_time(track.duration)}"},
        {"type": 2, "name": "progress_pct", "value": pct},
        {"type": 2, "name": "progress_sec", "value": int(pos)},
        {"type": 2, "name": "duration_sec", "value": int(track.duration)},
        {"type": 1, "name": "status", "value": status},
    ]
    if art_url:
        dynamic.append({"type": 3, "name": "album_art", "value": {"url": art_url}})
    return dynamic


# --------------------------------------------------------------------------- #
# Main loop                                                                    #
# --------------------------------------------------------------------------- #
def main() -> None:
    cfg = load_config()
    opt = cfg.get("options", {})
    poll_interval = float(opt.get("poll_interval_seconds", 5))
    tick = float(opt.get("tick_interval_seconds", 0.5))
    min_patch = float(opt.get("min_patch_interval_seconds", 0.75))
    heartbeat = float(opt.get("heartbeat_seconds", 0))  # 0 = push only on lyric-line change
    username_fmt = opt.get("username_format", "{track} — {artist}")
    no_lyrics_text = opt.get("no_lyrics_text", "♪")
    instrumental_text = opt.get("instrumental_text", "♪ Instrumental ♪")
    show_when_paused = bool(opt.get("show_when_paused", True))
    image_webhook = cfg["discord"].get("image_webhook_url", "")
    if image_webhook:
        log("Album-art widget-fix enabled (covers will be reshaped + hosted via webhook).")

    spotify = SpotifyClient(cfg)
    discord = DiscordWidget(cfg)

    track: Track | None = None
    current_id: str | None = None
    art_url = ""             # resolved album-art URL for the current track (fixed+hosted, or raw)
    lyrics = Lyrics([])
    sync_pos = 0.0           # last position reported by Spotify
    sync_mono = time.monotonic()
    is_playing = False
    last_poll = 0.0
    spotify_backoff_until = 0.0   # skip Spotify polls until here (honours Spotify's Retry-After on 429)
    last_sent = None         # dedupe key for the last pushed state
    last_patch_at = 0.0
    cooldown_until = 0.0     # don't PATCH again until this monotonic time (rate-limit pacing)

    log("Started. Watching Spotify… (Ctrl+C to stop)")
    while True:
        now = time.monotonic()

        # 1) Poll Spotify on its own cadence (respecting any Spotify back-off).
        if now - last_poll >= poll_interval and now >= spotify_backoff_until:
            last_poll = now
            data = None
            poll_ok = True
            try:
                data = spotify.now_playing()
            except requests.RequestException as exc:
                poll_ok = False
                resp = getattr(exc, "response", None)
                if resp is not None and resp.status_code == 429:
                    # Honour Spotify's Retry-After so we stop hammering during the penalty.
                    try:
                        retry = float(resp.headers.get("Retry-After", 5) or 5)
                    except (TypeError, ValueError):
                        retry = 5.0
                    spotify_backoff_until = now + min(max(retry, 1.0), 300.0)
                    log(f"Spotify rate limited; backing off {retry:.0f}s (keeping current state).")
                else:
                    log(f"Spotify error: {exc}")

            # Only act on a *successful* poll. On an error we keep the current
            # track/state instead of flipping the widget to 'nothing playing'.
            if poll_ok and data is None:
                track = None
                current_id = None
                state = ("idle",)
                if state != last_sent and now >= cooldown_until and (now - last_patch_at) >= min_patch:
                    sent, cooldown = discord.patch("Not listening", [
                        {"type": 1, "name": "status", "value": "⏹ Nothing playing"},
                        {"type": 1, "name": "lyric", "value": no_lyrics_text},
                    ])
                    if sent:
                        last_sent = state
                        last_patch_at = now
                        log("Idle — nothing playing.")
                    if cooldown > 0:
                        cooldown_until = now + cooldown
            elif poll_ok:
                parsed = parse_track(data)
                if parsed:
                    is_playing = parsed.is_playing
                    sync_pos = parsed.position
                    sync_mono = now
                    track = parsed
                    if parsed.id != current_id:
                        current_id = parsed.id
                        log(f"Now playing: {parsed.name} — {parsed.artist}")
                        # Resolve album art once per track (fix + host, or raw fallback).
                        art_url = process_cover(parsed.art_url, image_webhook) if image_webhook else parsed.art_url
                        lyrics = fetch_lyrics(parsed)
                        if lyrics.instrumental:
                            log("Track is instrumental.")
                        elif lyrics.lines:
                            log(f"Loaded {len(lyrics.lines)} synced lyric lines.")
                        else:
                            log("No synced lyrics found for this track.")

        # 2) Estimate the live position and the visible line.
        if track is not None:
            pos = sync_pos + ((now - sync_mono) if is_playing else 0.0)
            if track.duration:
                pos = min(pos, track.duration)

            if lyrics.instrumental:
                idx, line, prev, nxt = -2, instrumental_text, "", ""
            elif lyrics.lines:
                idx = lyrics.index_at(pos)
                line = lyrics.lines[idx][1] if idx >= 0 else no_lyrics_text
                prev = lyrics.lines[idx - 1][1] if idx - 1 >= 0 else ""
                nxt = lyrics.lines[idx + 1][1] if 0 <= idx + 1 < len(lyrics.lines) else ""
            else:
                idx, line, prev, nxt = -3, no_lyrics_text, "", ""

            if not is_playing and not show_when_paused:
                idx, line, prev, nxt = -4, "⏸ Paused", "", ""

            status = "▶ Now Playing" if is_playing else "⏸ Paused"
            state = (current_id, idx, is_playing)

            # 3) Push when the visible state changed, or on a heartbeat while playing
            #    (so a progress bar can advance between lyric-line changes).
            #    cooldown_until paces us under the rate limit; because we recompute the
            #    line every tick, whatever we send after a cooldown is always current.
            changed = state != last_sent
            beat = heartbeat > 0 and is_playing and (now - last_patch_at) >= heartbeat
            if (changed or beat) and now >= cooldown_until and (now - last_patch_at) >= min_patch:
                username = username_fmt.format(track=track.name, artist=track.artist, album=track.album)
                dynamic = build_dynamic(track, line, prev, nxt, pos, status, no_lyrics_text, art_url)
                sent, cooldown = discord.patch(username, dynamic)
                if sent:
                    last_sent = state
                    last_patch_at = now
                    log(f"♪ {line}")
                else:
                    log(f"Rate limited — holding {cooldown:.1f}s, will resume with the live line.")
                if cooldown > 0:
                    cooldown_until = now + cooldown

        time.sleep(tick)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Stopped (Ctrl+C).")
    except Exception:
        import traceback
        # Log the full traceback to widget.log, then exit non-zero so a Task
        # Scheduler "restart on failure" rule can bring it back up.
        log("FATAL (unhandled):\n" + traceback.format_exc())
        sys.exit(1)
