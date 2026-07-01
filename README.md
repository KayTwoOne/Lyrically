<div align="center">

<img src="docs/lyricallyicon.png" alt="Lyrically" width="200">

# 🎵 Lyrically

**Live, time-synced Spotify lyrics on your Discord profile.**

Lyrically is a small Python service that follows your Spotify playback, fetches synced lyrics, and
pushes the current line to a custom Discord profile widget in near-realtime.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20cross--platform%20core-blue)

</div>

---

## How it works

The widget itself has no logic: it's a layout with named data slots that Discord renders from
whatever was last pushed to your profile. All the realtime behaviour lives in [`widget.py`](widget.py):

```
 Spotify Web API ─┐  (current track + exact position)
                  ├─►  widget.py  ──PATCH──►  Discord profile widget
 LRCLIB ──────────┘  (time-synced .lrc lyrics)
```

1. **Poll** Spotify for the current track and playback position.
2. **Fetch** time-synced lyrics for that track from [LRCLIB](https://lrclib.net) (free, no key).
3. **Track the position locally** with a monotonic clock between polls, re-syncing to kill drift.
4. **Push** the current line to Discord the moment it changes, as fast as Discord's rate-limit bucket allows, keeping a small token reserve so a lyric-dense passage can't stall the widget.

## Features

- **Live synced lyrics**: the current line updates as the song plays.
- **Drift-corrected timing**: advances locally and re-syncs from Spotify, so lines stay aligned.
- **Adaptive rate limiting**: reads Discord's live rate-limit headers and sends each new line the instant it changes while there's headroom, gliding only as the bucket runs low and always keeping a reserve so it never bottoms out or halts. It never blocks, and after any 429 it backs off and resumes with the *current* line.
- **Graceful states**: handles pause, nothing-playing, instrumentals, and tracks with no lyrics.
- **Now-playing metadata**: track, artist, album, album art, and a song-progress bar.
- **Optional album-art fix**: reshapes each cover (transparent top strip + rounded top-right corner) so it sits inside the widget frame, hosted via a Discord webhook. Pure-Python port of [D.W.I.F](https://github.com/AjaxFNC-YT/D.W.I.F).
- **Hidden background mode**: a `pythonw` launcher and optional Windows Scheduled Task; no window, taskbar button, or tray icon.
- **Secrets-safe**: read-only Spotify scopes, loopback-only OAuth, nothing sensitive ever logged, `config.json` git-ignored.

## Getting started

> ⏱️ First-time setup takes around 20-30 minutes, mostly the one-time, browser-based Discord
> configuration. **The full walkthrough is in [SETUP.md](SETUP.md)**; the steps below are the overview.

### Prerequisites

- **Python 3.9+**: [python.org](https://www.python.org/downloads/) or the Microsoft Store
- A **Discord account** and a **Spotify account** (Free or Premium)
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

### 5. Connect Spotify

Follow **[SETUP.md, Part 8](SETUP.md)**: create a free Spotify app, put its **Client ID** and
**Client Secret** into `config.json`, then run the one-time auth helper:

```bash
python get_spotify_token.py
```

A browser opens once to authorize; it writes your refresh token into `config.json` automatically.

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

Because it reads playback from the Spotify **cloud** API (not your local app), Lyrically can run on a
free server and keep your widget updating even when your PC is off. Secrets can be supplied via
environment variables (`DISCORD_BOT_TOKEN`, `SPOTIFY_REFRESH_TOKEN`, and friends) so no secrets file
sits on the host. See **[HOSTING.md](HOSTING.md)** for a secure, step-by-step Wispbyte walkthrough.

## Configuration

All runtime behaviour is tunable in `config.json` under `options`: poll/tick cadence, the rate-limit
floor and reserve (responsiveness vs. 429 safety margin), an optional `heartbeat_seconds` for smoother
progress-bar movement, the `username_format`, and placeholder text for no-lyrics / instrumental /
paused states. See the table in [SETUP.md](SETUP.md).

## Project structure

| File | Purpose |
|---|---|
| `widget.py` | The realtime updater service (poll, lyrics, push). |
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

## License

[MIT](LICENSE) © 2026 Kay
