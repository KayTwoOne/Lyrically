<div align="center">

<img src="docs/lyricallyicon.png" alt="Lyrically" width="200">

# 🎵 Lyrically

**Live, time-synced Spotify lyrics on your Discord profile.**

Lyrically is a small Python service that follows your Spotify playback, fetches synced lyrics, and
pushes the current line to a custom Discord profile widget in near-realtime.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Spotify Premium](https://img.shields.io/badge/Spotify-Premium%20required-1DB954?logo=spotify&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20cross--platform%20core-blue)

</div>

---

## How it works

The widget itself has no logic: it's a layout with named data slots that Discord renders from
whatever was last pushed to your profile. All the realtime behaviour lives in [`widget.py`](widget.py):

```
 Music source ────┐  (current track + position: Discord presence,
                  │   Spotify API, Windows media, or Last.fm)
                  ├─►  widget.py  ──PATCH──►  Discord profile widget
 LRCLIB ──────────┘  (time-synced .lrc lyrics)
```

1. **Poll** Spotify for the current track and playback position.
2. **Fetch** time-synced lyrics for that track from [LRCLIB](https://lrclib.net) (free, no key).
3. **Track the position locally** with a monotonic clock between polls, re-syncing to kill drift.
4. **Push** the current line to Discord the moment it changes, as fast as Discord's rate-limit bucket allows, keeping a small token reserve so a lyric-dense passage can't stall the widget.

## Features

- **Live synced lyrics**: the current line updates as the song plays.
- **Four music sources**: Discord presence (free Spotify, exact sync), Spotify Web API (Premium), Windows media/SMTC (any local player), or Last.fm (any scrobbler, approximate).
- **Drift-corrected timing**: advances locally and re-syncs from the source, so lines stay aligned.
- **Adaptive rate limiting**: reads Discord's live rate-limit headers and paces updates evenly across the budget for a steady, unbroken cadence (or switch to `burst` pacing for lowest latency). It never blocks, and after any 429 it backs off and resumes with the *current* line.
- **Graceful states**: handles pause, nothing-playing, instrumentals, and tracks with no lyrics.
- **Now-playing metadata**: track, artist, album, album art, and a song-progress bar.
- **Optional album-art fix**: reshapes each cover (transparent top strip + rounded top-right corner) so it sits inside the widget frame, hosted via a Discord webhook. Pure-Python port of [D.W.I.F](https://github.com/AjaxFNC-YT/D.W.I.F).
- **Hidden background mode**: a `pythonw` launcher and optional Windows Scheduled Task; no window, taskbar button, or tray icon.
- **Secrets-safe**: read-only Spotify scopes, loopback-only OAuth, nothing sensitive ever logged, `config.json` git-ignored.

## Getting started

> ⚡ **Fast path:** most of the Discord setup can be done in **one console paste** with
> [`lyrically-setup.js`](lyrically-setup.js) (it creates the app + widget, adds it to your profile,
> and downloads a ready `config.json`). See [SETUP.md → Express setup](SETUP.md). The steps below are
> the full manual route.

> ⏱️ First-time setup takes around 20-30 minutes, mostly the one-time, browser-based Discord
> configuration. **The full walkthrough is in [SETUP.md](SETUP.md)**; the steps below are the overview.

### Prerequisites

- **Python 3.9+**: [python.org](https://www.python.org/downloads/) or the Microsoft Store
- A **Discord account**
- A music source (see the table below). **Spotify Premium is NOT required** unless you pick the
  Spotify API source.

### Music sources

Lyrically can read "what's playing" from four different places. Pick one with `source` in
`config.json` (the express setup asks you during install):

| `source` | Sync quality | Works with | Needs | Can run on a server 24/7 |
|---|---|---|---|---|
| `discord` (recommended) | **Exact** | Free or Premium Spotify (linked to Discord) | Join the [Lanyard server](https://discord.gg/lanyard), keep "Display Spotify as your status" on | ✅ |
| `spotify` | **Exact** | Spotify **Premium only** (2026 API rules) | A Spotify Developer app + one-time auth | ✅ |
| `smtc` | **Exact** | **Any** player on your Windows PC (free Spotify, YouTube Music, browsers...) | `pip install winsdk`; must run on the PC that plays the music; no album art | ❌ local only |
| `lastfm` | **Approximate** (Last.fm gives no playback position; lyrics are estimated) | Anything that scrobbles to Last.fm | Free [Last.fm API key](https://www.last.fm/api/account/create) + username | ✅ |

> ⚠️ **About Spotify Premium:** since February 2026 Spotify gates its Web API behind Premium, which
> is why the `spotify` source needs it. Free-Spotify users should pick `discord` (same exact sync,
> no Spotify keys needed at all) or `lastfm`/`smtc`.
- Windows is fully supported (including hidden background mode); the core script is cross-platform

### 1. Get the code

```bash
git clone https://github.com/<your-username>/Lyrically.git
cd Lyrically
```

### 2. Install the dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your config file

```powershell
Copy-Item config.example.json config.json   # Windows PowerShell
# cp config.example.json config.json          # macOS / Linux
```

You'll fill `config.json` in during the next two steps. It is git-ignored, so **never commit it**.

### 4. Set up the Discord app + widget

Follow **[SETUP.md, Parts 1-7](SETUP.md)**: create a Discord application, unlock the widget editor,
design the widget, authorize it, and copy your **Application ID**, **User ID**, and **Bot token**
into `config.json`.

### 5. Connect your music source

Set `source` in `config.json` and do that source's one-time step (full details in
**[SETUP.md, Part 8](SETUP.md)**):

- **`discord`** (recommended): join the [Lanyard server](https://discord.gg/lanyard) and keep
  "Display Spotify as your status" on. No keys needed.
- **`spotify`** (Premium): create a Spotify Developer app, put its **Client ID/Secret** into
  `config.json`, then run `python get_spotify_token.py` once.
- **`smtc`** (Windows): `pip install winsdk`. Nothing else.
- **`lastfm`** (approximate sync): put your **username** and free **API key** into `config.json`.

### 6. Run it

```bash
python widget.py
```

Play a song and you'll see it pick up the track and start pushing lyric lines.

### 7. Add the widget to your profile

Follow **[SETUP.md, Part 10](SETUP.md)** to add the published widget to your Discord profile.

### (Optional) Run it hidden in the background

Double-click **`start-widget.vbs`**, or see **[SETUP.md, Part 11](SETUP.md)** to auto-start it at
logon with no window.

### (Optional) Host it 24/7

The `discord`, `spotify` and `lastfm` sources read playback from cloud APIs, so Lyrically can run on
a free server and keep your widget updating even when your PC is off (`smtc` is the one local-only
source). Secrets can be supplied via environment variables (`DISCORD_BOT_TOKEN`,
`SPOTIFY_REFRESH_TOKEN`, `LASTFM_API_KEY`, `LYRICALLY_SOURCE`, and friends) so no secrets file sits
on the host. See **[HOSTING.md](HOSTING.md)** for a secure, step-by-step Wispbyte walkthrough.

## Configuration

All runtime behaviour is tunable in `config.json` under `options`: poll/tick cadence, the rate-limit
floor and reserve (responsiveness vs. 429 safety margin), an optional `heartbeat_seconds` for smoother
progress-bar movement, the `username_format`, and placeholder text for no-lyrics / instrumental /
paused states. See the table in [SETUP.md](SETUP.md).

## Project structure

| File | Purpose |
|---|---|
| `widget.py` | The realtime updater service (poll, lyrics, push). |
| `lyrically-setup.js` | Optional one-paste browser-console script that automates the whole Discord setup. |
| `lyrically_widget_config.json` | The widget layout, importable by a widget-configurator extension (or baked into the script above). |
| `get_spotify_token.py` | One-time Spotify OAuth helper; writes your refresh token. |
| `config.example.json` | Config template; copy to `config.json` (git-ignored). |
| `widget_sample_data.json` | Key/Type/Value reference for the editor's Sample Data tab. |
| `sample_album_art.png` | Placeholder cover for the editor's image picker / fallback. |
| `start-widget.vbs` | Launches the service hidden (for the Startup folder). |
| `install_background.ps1` / `uninstall_background.ps1` | Optional auto-restarting Scheduled Task. |
| `SETUP.md` | Full from-scratch setup guide. |
| `HOSTING.md` | Secure step-by-step guide to host it 24/7 (Wispbyte / any server). |

## Tech stack

**Python 3.9+** with [`requests`](https://pypi.org/project/requests/) and
[`Pillow`](https://pypi.org/project/Pillow/) · **Spotify Web API** (Authorization Code flow) for
playback · **LRCLIB** for synced lyrics · **Discord Social SDK** profile widgets.

## Security

`config.json` holds a Discord bot token and a Spotify client secret + refresh token. It is
**git-ignored and must never be committed**. Spotify scopes are read-only, the OAuth helper binds only
to loopback and validates the OAuth `state`, and no secret value is ever printed or logged. See the
threat-model section in [SETUP.md](SETUP.md).

## Disclaimer

Lyrically uses an **experimental, unofficial** Discord feature (Social SDK profile widgets) gated
behind developer experiments, which may change or be removed at any time. It is provided for
**personal and educational use**. Use it responsibly. Not affiliated with or endorsed by Discord or
Spotify; all trademarks belong to their respective owners.

## Credits

- Method based on [Chloe Cinders' "How to make Discord Widgets"](https://chloecinders.com/blog/discord-widgets) guide.
- Profile-injection technique from the **Discord Previews** community.
- Lyrics from [LRCLIB](https://lrclib.net).
- Album-art widget-fix algorithm ported from **[D.W.I.F](https://github.com/AjaxFNC-YT/D.W.I.F)** by [AjaxFNC-YT](https://github.com/AjaxFNC-YT).
- Automated setup script (`lyrically-setup.js`) and importable `lyrically_widget_config.json` adapted from **[aamiaa's Widget Creator](https://gist.github.com/aamiaa/7cdd590e3949cd654758bc90bcb4710b)** and the community "Discord Widget Configurator" extension built on it.

## License

[MIT](LICENSE) © 2026 Kay
