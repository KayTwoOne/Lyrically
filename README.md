<div align="center">

<img src="docs/lyricallyicon.png" alt="Lyrically" width="200">

# 🎵 Lyrically

**Live, time-synced lyrics on your Discord profile.**

Lyrically is a small program that watches what music you're playing, looks up the lyrics, and shows
the exact line you're hearing on a widget on your Discord profile, updating in near-realtime.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20cross--platform%20core-blue)

</div>

---

## What is this, in plain English?

Discord has an experimental feature that lets a profile show a small "widget" card. Lyrically fills
that card with your current song: title, artist, album art, a progress bar, and the **lyric line
you're hearing right now**.

The widget itself is just a display. The actual work is done by a small Python script
([`widget.py`](widget.py)) that runs on your PC (or a server): it checks what you're playing,
fetches the song's synced lyrics, and sends the current line to Discord every few seconds.

```
 Music source ────┐  (what's playing + how far into the song:
                  │   Discord presence, Spotify API, Windows media, or Last.fm)
                  ├─►  widget.py  ──►  your Discord profile widget
 LRCLIB ──────────┘  (the time-synced lyrics)
```

## What you'll need

- A **Windows PC** (macOS/Linux work for the core script too)
- A **Discord account**
- **About 30 minutes** for the one-time setup
- A music source from the table below. **Spotify Premium is NOT required** unless you choose the
  Spotify API source.

## Music sources

Lyrically can read "what's playing" from four places. You pick one during setup:

| Source | Lyric sync | Works with | Extra requirements |
|---|---|---|---|
| **Discord presence** (recommended) | Exact | Free or Premium Spotify | Join one Discord server (Lanyard); keep "Display Spotify as your status" on |
| **Spotify API** | Exact | Spotify **Premium only** | A free Spotify developer app + a one-time login |
| **Windows media (SMTC)** | Exact | **Any** music app on your PC | One extra install; must run on the PC that plays the music; no album art |
| **Last.fm** | Approximate (no position data, so lyrics are estimated) | Anything that scrobbles to Last.fm | Free Last.fm API key |

---

## Getting started (no experience needed)

Never touched Python, pip, or a terminal? Follow these parts in order. Each one explains itself.

### Part A: Install Python

Python is a free programming language runtime. Lyrically's code is written in it, so your PC needs
Python installed to run it.

**Windows (pick one):**
- **python.org (recommended):** download the latest Python from
  [python.org/downloads](https://www.python.org/downloads/), run the installer, and on the very
  first screen **tick the box that says "Add python.exe to PATH"** before clicking Install. That
  box is what lets you type `python` in a terminal later.
- **Microsoft Store:** search "Python" in the Store app and install the newest version (3.11+).
  No checkboxes to worry about.

**macOS:** use the installer from [python.org/downloads](https://www.python.org/downloads/).
**Linux:** Python is usually preinstalled; otherwise use your package manager.

**Check it worked:** open a terminal (Windows: press **Start**, type `powershell`, press Enter) and type:

```
python --version
```

If it prints something like `Python 3.12.4`, you're good. If it says *"python is not recognized"*,
see [Troubleshooting](#troubleshooting-for-first-timers) below.

### Part B: Download Lyrically

- Click the green **Code** button at the top of this page, then **Download ZIP**.
- Right-click the downloaded file, **Extract All**, and put the folder somewhere you'll keep it
  (for example `Documents\Lyrically`).
- (If you use git: `git clone` works too, of course.)

Now open a terminal **in that folder**: on Windows 11, open the folder in File Explorer,
right-click empty space, and choose **Open in Terminal**. (On Windows 10: hold **Shift**,
right-click, "Open PowerShell window here".) Every command below is typed into that window.

### Part C: Install the libraries (this is what "pip" is)

`pip` is Python's built-in package installer: it downloads the ready-made libraries a script needs.
Lyrically needs two small ones, listed in [`requirements.txt`](requirements.txt). Install them with:

```
python -m pip install -r requirements.txt
```

You'll see it download and finish with "Successfully installed...". That's it, pip's whole job is done.

### Part D: Create your config file

Lyrically reads your personal settings (IDs, tokens, chosen source) from a file called
`config.json`. Make yours by copying the template:

- In File Explorer: copy [`config.example.json`](config.example.json), paste it in the same
  folder, and rename the copy to exactly **`config.json`**.
- ⚠️ Windows hides file extensions by default, which can silently give you `config.json.txt`.
  In File Explorer turn on **View → Show → File name extensions** first, so you can see what
  you're renaming.

You don't need to fill anything in yet: the next step does most of it for you.

### Part E: The Discord side (one paste does almost all of it)

This creates the Discord app and the widget, adds it to your profile, and hands you a filled-in
`config.json` to swap in. It's a guided, form-based script you paste into your browser once:

➡️ **Follow [SETUP.md → Express setup](SETUP.md)** (it also asks which music source you want and
explains what each needs, with accuracy labels).

Prefer to do everything by hand, or want to understand each step? The same file contains the full
manual walkthrough (Parts 1-12).

### Part F: Connect your music source

Whatever you picked in Part E has a small one-time step, detailed in
**[SETUP.md, Part 8](SETUP.md)**:

- **Discord presence** (recommended): join the [Lanyard Discord server](https://discord.gg/lanyard)
  and make sure Discord's Settings → Connections → Spotify has **"Display Spotify as your status"**
  turned on. No keys needed.
- **Spotify API** (Premium): create a free developer app, put its Client ID/Secret in
  `config.json`, then run `python get_spotify_token.py` once (a browser opens, you click Agree).
- **Windows media**: run `python -m pip install winsdk`. Done.
- **Last.fm**: put your username and free [API key](https://www.last.fm/api/account/create) in
  `config.json`.

### Part G: Run it

In your terminal (still in the Lyrically folder):

```
python widget.py
```

Play a song. Within a few seconds you should see lines like:

```
Started. Source: Discord presence via Lanyard ...
Now playing: <song> - <artist>
Loaded 42 synced lyric lines.
♪ <the current lyric line>
```

...and your Discord profile widget comes alive. Press **Ctrl+C** in the terminal to stop it.
Everything it does is also written to `widget.log` in the same folder.

### Part H (optional): Run it invisibly in the background

Once it works, you don't need a terminal window sitting around: double-click
**`start-widget.vbs`** to run it with no window at all, or see **[SETUP.md, Part 11](SETUP.md)** to
start it automatically at every logon. Want it running 24/7 even with your PC off? See
**[HOSTING.md](HOSTING.md)** for a free-server walkthrough.

---

## Troubleshooting for first-timers

- **"python is not recognized"** in the terminal: Python isn't on your PATH. Easiest fixes: try
  `py --version` instead (the python.org installer adds a `py` shortcut), or re-run the python.org
  installer and tick **"Add python.exe to PATH"**, then open a **new** terminal window.
- **"pip is not recognized"**: use the form we use everywhere here, `python -m pip ...`, which
  always works when `python` does.
- **You double-clicked `widget.py` and a window flashed and vanished**: that's normal; run it from
  a terminal instead so you can read what it says.
- **The widget shows "Nothing playing"** while music is on: read the newest lines in `widget.log` -
  Lyrically tells you exactly why (for the Discord source it's usually your status being set to
  Invisible, or the Spotify status toggle being off).
- **`config.json` seems ignored**: check it isn't actually `config.json.txt` (see Part D).

## Everyday knobs (optional)

All tuning lives in `config.json` under `options`: how often to poll, `pacing` (`smooth` = steady
even updates, `burst` = fastest possible updates in clumps), placeholder texts, and more. The full
table is in [SETUP.md](SETUP.md). The defaults are sensible; you don't have to touch any of it.

## Project structure

| File | Purpose |
|---|---|
| `widget.py` | The program that watches your music and updates the widget. |
| `lyrically-setup.js` | One-paste browser script that automates the whole Discord setup. |
| `lyrically_widget_config.json` | The widget layout, importable by a widget-configurator extension. |
| `get_spotify_token.py` | One-time Spotify login helper (Spotify API source only). |
| `config.example.json` | Settings template; copy to `config.json`. |
| `widget_sample_data.json` | Reference values for the widget editor's Sample Data tab. |
| `sample_album_art.png` | Placeholder cover for the editor's image picker. |
| `start-widget.vbs` | Runs Lyrically hidden, with no window. |
| `install_background.ps1` / `uninstall_background.ps1` | Optional auto-start task for Windows. |
| `SETUP.md` | Full setup guide (express + manual + all sources). |
| `HOSTING.md` | Run it 24/7 on a free server. |

## Security

Your `config.json` holds a Discord bot token (and possibly Spotify/Last.fm keys). It stays on your
machine, is ignored by git, and must **never** be shared or uploaded. The tokens involved are
deliberately low-power: they can update your widget, not control your account. Spotify access is
read-only. Nothing sensitive is ever printed to logs. Full threat model in [SETUP.md](SETUP.md).

## Disclaimer

Lyrically uses an **experimental, unofficial** Discord feature (Social SDK profile widgets) gated
behind developer experiments, which may change or be removed at any time. It is provided for
**personal and educational use**. Use it responsibly. Not affiliated with or endorsed by Discord,
Spotify, or Last.fm; all trademarks belong to their respective owners.

## Credits

- Method based on [Chloe Cinders' "How to make Discord Widgets"](https://chloecinders.com/blog/discord-widgets) guide.
- Profile-injection technique from the **Discord Previews** community.
- Lyrics from [LRCLIB](https://lrclib.net).
- Album-art widget-fix algorithm ported from **[D.W.I.F](https://github.com/AjaxFNC-YT/D.W.I.F)** by [AjaxFNC-YT](https://github.com/AjaxFNC-YT).
- Automated setup script (`lyrically-setup.js`) and importable widget config adapted from **[aamiaa's Widget Creator](https://gist.github.com/aamiaa/7cdd590e3949cd654758bc90bcb4710b)** and the community "Discord Widget Configurator" extension built on it.

## License

[MIT](LICENSE) © 2026 Kay
