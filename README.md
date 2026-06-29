# Spotify realtime-lyrics Discord widget

A personal Discord profile widget that displays your current Spotify track **and the live
lyric line**, updated in near-realtime by a small local Python script.

```
Spotify (now playing + position)  ─┐
                                   ├─> widget.py  ──PATCH──>  Discord widget identity
LRCLIB (time-synced lyrics)       ─┘                          (your profile widget)
```

## Files

| File | What it is |
|---|---|
| **[SETUP.md](SETUP.md)** | **Start here.** Full from-scratch walkthrough (Discord app, editor, OAuth, Spotify, running it). |
| `widget.py` | The realtime updater loop. `python widget.py` |
| `get_spotify_token.py` | One-time Spotify OAuth helper that writes your refresh token. |
| `config.example.json` | Template → copy to `config.json` and fill in. |
| `widget_sample_data.json` | The exact Key/Type/Value rows to enter in the editor's Sample Data tab. |
| `sample_album_art.png` | Placeholder cover to upload for the Sample Data preview + any image fallback (the editor's image picker is upload-only). |
| `requirements.txt` | `requests` (already installed here). |
| `start-widget.vbs` | Launches the updater **hidden** (no window/taskbar/tray). For the Startup folder. See SETUP.md Part 11. |
| `install_background.ps1` / `uninstall_background.ps1` | Optional: run it as an auto-restarting hidden Scheduled Task. |
| `widget.log` | Created at runtime — the log to check when it runs in the background. |

## Quick start

```powershell
Copy-Item config.example.json config.json   # then fill in IDs/secrets per SETUP.md
python get_spotify_token.py                 # one-time: authorize Spotify
python widget.py                            # run it; play a song
```

See **[SETUP.md](SETUP.md)** for the Discord-side steps (the parts that need your browser).

> Use responsibly — this rides a Discord experiment; abuse risks the feature being removed for everyone.
