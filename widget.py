#!/usr/bin/env python3
"""Realtime music lyrics -> Discord profile widget updater.

The loop, every tick:
  1. (every poll_interval) ask the configured MUSIC SOURCE what's playing.
     Sources ("source" in config.json):
       spotify : Spotify Web API   - exact position; requires Spotify Premium
       discord : Discord presence  - exact position via Lanyard; free Spotify OK
       smtc    : Windows media     - exact position; any local player; Windows only
       lastfm  : Last.fm           - approximate position (estimated); any scrobbler
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
    ("lastfm", "username"):        "LASTFM_USERNAME",
    ("lastfm", "api_key"):         "LASTFM_API_KEY",
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
    cfg.setdefault("lastfm", {})
    cfg.setdefault("discord_presence", {})
    cfg.setdefault("options", {})
    for (section, key), env_name in _ENV_MAP.items():
        value = os.environ.get(env_name)
        if value:
            cfg[section][key] = value
    # Which music source feeds the widget (spotify | discord | smtc | lastfm).
    cfg["source"] = os.environ.get("LYRICALLY_SOURCE", cfg.get("source", "spotify"))
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
    duration: float           # seconds (0 = unknown)
    position: float | None    # seconds at poll time; None = source can't report it (estimated locally)
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
# Music sources — where "what's playing right now" comes from.                 #
# Every source exposes .poll() -> Track | None (None = nothing playing) and    #
# may raise requests.RequestException (the main loop backs off and retries).   #
# --------------------------------------------------------------------------- #
class SpotifySource:
    """Spotify Web API. Exact position. Requires Spotify Premium (2026 API rules)."""
    name = "Spotify Web API (exact sync, Premium required)"

    def __init__(self, cfg: dict):
        self.client = SpotifyClient(cfg)

    def poll(self) -> Track | None:
        data = self.client.now_playing()
        return parse_track(data) if data else None


class DiscordPresenceSource:
    """Your Discord 'Listening to Spotify' presence, read via Lanyard.

    Exact position (presence carries start/end timestamps) and works with FREE
    Spotify. Needs: Spotify linked to Discord with 'Display Spotify as your
    status' on, and your account in the Lanyard Discord server (discord.gg/lanyard)
    or a self-hosted Lanyard (set discord_presence.lanyard_url).
    Note: pausing removes the presence, so pause shows as 'nothing playing'.
    """
    name = "Discord presence via Lanyard (exact sync, free Spotify OK)"

    def __init__(self, cfg: dict):
        dp = cfg.get("discord_presence", {})
        self.user_id = dp.get("user_id") or cfg["discord"].get("user_id", "")
        self.base = (dp.get("lanyard_url") or "https://api.lanyard.rest").rstrip("/")
        self._hinted = False   # log the "why is nothing showing" hint once per dry spell
        if not self.user_id or str(self.user_id).startswith("YOUR_"):
            die("The discord source needs your Discord user id (discord.user_id in config.json).")

    def poll(self) -> Track | None:
        resp = requests.get(f"{self.base}/v1/users/{self.user_id}", timeout=15)
        if resp.status_code == 404:
            die("Lanyard doesn't know this user - join https://discord.gg/lanyard with this account "
                "(or self-host Lanyard and set discord_presence.lanyard_url).")
        resp.raise_for_status()
        data = resp.json().get("data") or {}
        sp = data.get("spotify")
        if not data.get("listening_to_spotify") or not sp:
            # Tell the user WHY nothing is showing (once per dry spell).
            if not self._hinted:
                if data.get("discord_status", "offline") == "offline":
                    log("Discord shows you as OFFLINE/INVISIBLE - presence (and your Spotify status) is "
                        "hidden from everyone, including this widget. Set yourself Online/Idle/DND on any "
                        "Discord client and it will pick up within a few seconds.")
                else:
                    log("You're online but Discord shows no 'Listening to Spotify' status. Check: "
                        "Settings -> Connections -> Spotify -> 'Display Spotify as your status' is ON, "
                        "Settings -> Activity Privacy -> 'Share your detected activities' is ON, "
                        "music is actually playing, and you're not in a Spotify Private Session. "
                        f"You can see exactly what the widget sees at {self.base}/v1/users/{self.user_id}")
                self._hinted = True
            return None
        self._hinted = False
        ts = sp.get("timestamps") or {}
        start, end = ts.get("start") or 0, ts.get("end") or 0
        duration = max((end - start) / 1000.0, 0.0)
        position = max((time.time() * 1000 - start) / 1000.0, 0.0) if start else None
        if duration and position is not None:
            position = min(position, duration)
        return Track(
            id=sp.get("track_id") or f"{sp.get('song')}|{sp.get('artist')}",
            name=sp.get("song") or "",
            artist=(sp.get("artist") or "").replace("; ", ", "),
            album=sp.get("album") or "",
            art_url=sp.get("album_art_url") or "",
            duration=duration,
            position=position,
            is_playing=True,   # presence only exists while actually playing
        )


class LastFmSource:
    """Last.fm now-playing. Works with ANY scrobbling player (free Spotify included)
    but Last.fm reports no playback position, so the lyric sync is APPROXIMATE:
    we start a local clock when we first see the track (late joins run behind,
    seeks aren't detected). Duration comes from track.getInfo when available.
    """
    name = "Last.fm (approximate sync - no position data)"
    API = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self, cfg: dict):
        lf = cfg.get("lastfm", {})
        self.user = lf.get("username", "")
        self.key = lf.get("api_key", "")
        if not self.user or not self.key or str(self.key).startswith("YOUR_"):
            die("The lastfm source needs lastfm.username and lastfm.api_key in config.json "
                "(free key: https://www.last.fm/api/account/create).")
        self._dur_cache: dict[tuple[str, str], float] = {}

    def _duration(self, artist: str, track_name: str) -> float:
        key = (artist, track_name)
        if key not in self._dur_cache:
            dur = 0.0
            try:
                r = requests.get(self.API, params={
                    "method": "track.getInfo", "artist": artist, "track": track_name,
                    "api_key": self.key, "format": "json"}, timeout=15)
                if r.ok:
                    dur = float((r.json().get("track") or {}).get("duration") or 0) / 1000.0
            except (requests.RequestException, ValueError, TypeError):
                pass
            self._dur_cache[key] = dur
        return self._dur_cache[key]

    def poll(self) -> Track | None:
        r = requests.get(self.API, params={
            "method": "user.getrecenttracks", "user": self.user,
            "api_key": self.key, "format": "json", "limit": 1}, timeout=15)
        r.raise_for_status()
        tracks = (r.json().get("recenttracks") or {}).get("track") or []
        t = tracks[0] if isinstance(tracks, list) and tracks else None
        if not t or (t.get("@attr") or {}).get("nowplaying") != "true":
            return None
        name = t.get("name") or ""
        artist = (t.get("artist") or {}).get("#text") or ""
        imgs = t.get("image") or []
        art = (imgs[-1].get("#text") or "") if imgs else ""
        return Track(
            id=f"{name}|{artist}",
            name=name, artist=artist,
            album=(t.get("album") or {}).get("#text") or "",
            art_url=art,
            duration=self._duration(artist, name),
            position=None,        # unknown -> the main loop estimates from first sighting
            is_playing=True,
        )


class SmtcSource:
    """Windows System Media Transport Controls. Exact position for ANY local
    player (free Spotify desktop, YouTube Music, browsers...). Windows-only and
    must run on the PC that's playing. No album-art URL is available, so the
    widget shows its fallback image. Needs:  pip install winsdk
    """
    name = "Windows media / SMTC (exact sync, any local player)"

    def __init__(self, cfg: dict):
        if sys.platform != "win32":
            die("The smtc source only works on Windows (it reads the system media controls).")
        try:
            import asyncio
            import winsdk.windows.media.control as wmc
        except ImportError:
            die("The smtc source needs the winsdk package:  pip install winsdk")
        self._asyncio = asyncio
        self._wmc = wmc

    async def _read(self) -> Track | None:
        wmc = self._wmc
        mgr = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
        session = mgr.get_current_session()
        if session is None:
            return None
        props = await session.try_get_media_properties_async()
        if not props or not (props.title or "").strip():
            return None
        info = session.get_playback_info()
        playing = info.playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING
        tl = session.get_timeline_properties()
        duration = tl.end_time.total_seconds() if tl.end_time else 0.0
        position = tl.position.total_seconds() if tl.position else 0.0
        return Track(
            id=f"{props.title}|{props.artist}|{props.album_title}",
            name=props.title or "", artist=props.artist or "",
            album=props.album_title or "", art_url="",
            duration=duration, position=position, is_playing=playing,
        )

    def poll(self) -> Track | None:
        return self._asyncio.run(self._read())


SOURCES = {"spotify": SpotifySource, "discord": DiscordPresenceSource,
           "lastfm": LastFmSource, "smtc": SmtcSource}


def build_source(cfg: dict):
    key = str(cfg.get("source") or "spotify").strip().lower()
    cls = SOURCES.get(key)
    if not cls:
        die(f"Unknown source '{key}'. Valid options: " + ", ".join(sorted(SOURCES)))
    return cls(cfg)


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
        # (Only used by "burst" pacing.)
        self.reserve = max(1, int(opt.get("rate_limit_reserve", 1)))
        # How to spend the fixed rate-limit budget:
        #   smooth (default): spread sends evenly across the bucket window - a
        #                     steady, even cadence with no bursts.
        #   burst           : send the instant a line changes while there's
        #                     headroom, then glide near the reserve - lowest
        #                     latency, but lines arrive in bursts.
        self.pacing = str(opt.get("pacing", "smooth")).strip().lower()
        if self.pacing not in ("smooth", "burst"):
            log(f"Unknown pacing '{self.pacing}' - using 'smooth'.")
            self.pacing = "smooth"
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

        # Success — decide how long to wait before the NEXT send, based on the
        # bucket headers and the configured pacing strategy. Note the cooldown is
        # a *gate*, not a schedule: after it expires we still wait for the next
        # real lyric-line change, so updates land on line boundaries either way.
        cooldown = 0.0
        try:
            remaining = int(float(resp.headers.get("X-RateLimit-Remaining", "1")))
            reset_after = float(resp.headers.get("X-RateLimit-Reset-After", "0"))
            if remaining <= 0:
                cooldown = max(reset_after, 1.0) + 0.25          # empty: wait for the refill
            elif self.pacing == "smooth":
                # Steady cadence: spread the remaining budget evenly across the
                # window. No bursts, no long stalls - the smoothest a fixed
                # budget allows.
                cooldown = (reset_after / (remaining + 1)) if reset_after > 0 else 0.0
            elif remaining <= self.reserve:
                cooldown = (reset_after / remaining) if reset_after > 0 else 1.0  # burst: glide on last tokens
            # else (burst pacing, healthy budget): cooldown 0 -> fire on next change
            if self.log_rate_limits or cooldown > 0:
                limit = resp.headers.get("X-RateLimit-Limit", "?")
                log(f"[ratelimit] limit={limit} remaining={remaining} "
                    f"reset_after={reset_after:.1f}s -> next send in {cooldown:.1f}s ({self.pacing})")
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

    source = build_source(cfg)
    discord = DiscordWidget(cfg)

    track: Track | None = None
    current_id: str | None = None
    art_url = ""             # resolved album-art URL for the current track (fixed+hosted, or raw)
    lyrics = Lyrics([])
    sync_pos = 0.0           # last known/estimated position
    sync_mono = time.monotonic()
    is_playing = False
    last_poll = 0.0
    source_backoff_until = 0.0    # skip source polls until here (honours Retry-After on 429)
    last_sent = None         # dedupe key for the last pushed state
    last_patch_at = 0.0
    cooldown_until = 0.0     # don't PATCH again until this monotonic time (rate-limit pacing)

    log(f"Started. Source: {source.name}. (Ctrl+C to stop)")
    while True:
        now = time.monotonic()

        # 1) Poll the music source on its own cadence (respecting any back-off).
        if now - last_poll >= poll_interval and now >= source_backoff_until:
            last_poll = now
            fresh: Track | None = None
            poll_ok = True
            try:
                fresh = source.poll()
            except requests.RequestException as exc:
                poll_ok = False
                resp = getattr(exc, "response", None)
                if resp is not None and resp.status_code == 429:
                    # Honour the service's Retry-After so we stop hammering during a penalty.
                    try:
                        retry = float(resp.headers.get("Retry-After", 5) or 5)
                    except (TypeError, ValueError):
                        retry = 5.0
                    wait = min(max(retry, 1.0), 3600.0)   # honour it, but re-check at least hourly
                    source_backoff_until = now + wait
                    log(f"Source rate limited; waiting {wait:.0f}s "
                        f"(Retry-After: {retry:.0f}s; keeping current state).")
                else:
                    log(f"Source error: {exc}")

            # Only act on a *successful* poll. On an error we keep the current
            # track/state instead of flipping the widget to 'nothing playing'.
            if poll_ok and fresh is None:
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
            elif poll_ok and fresh is not None:
                parsed = fresh
                is_playing = parsed.is_playing
                track = parsed
                new_track = parsed.id != current_id
                if parsed.position is not None:
                    # Source reports a real position: re-anchor the local clock to it.
                    sync_pos, sync_mono = parsed.position, now
                elif new_track:
                    # Source can't report position (e.g. Last.fm): estimate from the
                    # moment we first saw the track; keep the clock running otherwise.
                    sync_pos, sync_mono = 0.0, now
                if new_track:
                    current_id = parsed.id
                    log(f"Now playing: {parsed.name} — {parsed.artist}"
                        + (" (position estimated)" if parsed.position is None else ""))
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
