# Hosting Lyrically (Wispbyte or any always-on host)

`widget.py` reads your playback from the **Spotify Web API** — a cloud API tied to your account,
not your local Spotify app. So it sees what you're playing on **any** device, and can run on a
remote server instead of your PC. Hosted, it updates your profile **24/7, even when your PC is off**.

This guide uses **Wispbyte** (a free [Pterodactyl](https://pterodactyl.io)-based host), but the same
steps apply to any host that runs a Python process (Railway, Fly.io, a VPS, a Raspberry Pi…).

> Exact panel labels may differ slightly; the concepts (Console, File Manager, Startup, Variables)
> are standard Pterodactyl.

---

## Read first: the security model (why this is low-risk)

Putting secrets on a third-party host always means *trusting that host's operators* — they can
technically read files/variables on your server. That's true of **any** host. What makes this safe is
that the credentials involved have a **deliberately small blast radius**:

- **Discord bot token** → can only write to *your widget identity*. It is **not** your Discord
  login token: it **cannot** read your DMs, change your password, or log in as you. Worst case if
  leaked: someone could change what your widget displays. Rotate it and it's dead.
- **Spotify credentials** → the scopes are **read-only** (`user-read-currently-playing`,
  `user-read-playback-state`). They **cannot** control playback, edit playlists, or change your
  account. Worst case if leaked: someone could see what you're listening to.

So even a total compromise of the host can't take over your Discord or Spotify account. Combined with
the practices below, hosting this is genuinely low-risk.

### Security checklist
- ✅ Use the **dedicated, single-purpose** Discord app + bot token you already made — never reuse it.
- ✅ Keep Spotify scopes **read-only** (the defaults — don't add write scopes).
- ✅ Protect the panel account: **strong, unique password + 2FA**.
- ✅ **Never commit `config.json`** or paste tokens anywhere public (it's git-ignored already).
- ✅ Prefer **environment variables** over an on-disk secrets file (Step 4, Option A).
- ✅ Know how to **rotate** (bottom of this page) and do it if you stop using the host or suspect anything.

---

## Before you start (do these locally, once)

> **Which sources can be hosted?** `discord`, `spotify` and `lastfm` read cloud APIs and host fine.
> The `smtc` source reads *this PC's* media controls and **cannot** run on a server — switch source
> if you want 24/7 hosting. Set the source on the host via `LYRICALLY_SOURCE` (or `config.json`).

1. **Finish the Discord setup + your music source** in [SETUP.md](SETUP.md) — the widget should
   already be published, authorized, and on your profile. Hosting only moves *where `widget.py` runs*.
2. **Spotify source only — get your refresh token locally.** The auth flow needs a browser +
   loopback redirect, which a server can't do, so run this on your PC:
   ```bash
   python get_spotify_token.py
   ```
   It prints your `SPOTIFY_REFRESH_TOKEN` at the end — copy it.
   (The `discord` source needs no keys at all; `lastfm` just needs `LASTFM_USERNAME` + `LASTFM_API_KEY`.)
3. **Collect your values** (from `config.json` / the dashboards):
   `LYRICALLY_SOURCE`, `DISCORD_APPLICATION_ID`, `DISCORD_USER_ID`, `DISCORD_BOT_TOKEN`, plus for
   the Spotify source `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, or for
   Last.fm `LASTFM_USERNAME`, `LASTFM_API_KEY`.

---

## Step-by-step on Wispbyte

### 1. Create the account
Sign up at Wispbyte. Use a **strong, unique password** and **enable 2FA** in account settings.

### 2. Create a server
Create a new server and pick a **Python** egg (e.g. "Generic Python" / a Python-capable bot egg).
Give it a small resource plan — this app needs very little (~30–60 MB RAM).

### 3. Get the code onto it
Two options — pick one:

- **A) Pull from GitHub (recommended).** If the egg has a Git option, point it at your public repo:
  `https://github.com/KayTwoOne/Lyrically`. This pulls the **code only** — `config.json` is
  git-ignored, so no secrets come down with it.
- **B) Upload manually.** Use the **File Manager** to upload at least `widget.py` and
  `requirements.txt`.

### 4. Provide your secrets
Pick **one** approach:

- **A) Environment variables (preferred — no secrets file on disk).**
  In the server's **Startup** tab, add these variables (if the egg lets you add custom variables):

  | Variable | Value |
  |---|---|
  | `DISCORD_APPLICATION_ID` | your app ID |
  | `DISCORD_USER_ID` | your Discord user ID |
  | `DISCORD_BOT_TOKEN` | your bot token |
  | `SPOTIFY_CLIENT_ID` | your Spotify client ID |
  | `SPOTIFY_CLIENT_SECRET` | your Spotify client secret |
  | `SPOTIFY_REFRESH_TOKEN` | the token printed by `get_spotify_token.py` |

  `widget.py` reads these automatically (env overrides any file).

- **B) Upload a `config.json`.** If the egg doesn't allow custom variables, create a `config.json`
  locally with your values and upload it via the **File Manager**. This is fine — just remember it's
  a secrets file living on the host (don't share it; the low-blast-radius tokens keep it safe-ish).

> You can mix them: upload a `config.json` with only the **non-secret** bits (app/user IDs, options)
> and put the three secrets in env vars.

### 5. Install dependencies & set the start command
Set the server's **startup command** to install the dependency and run the script, e.g.:

```bash
pip install -r requirements.txt && python3 widget.py
```

(Some eggs install `requirements.txt` automatically and just need the file to run set to `widget.py`.)

### 6. Start it
Click **Start** and watch the **Console**. You should see:
```
Started. Watching Spotify…
Now playing: <song> — <artist>
Loaded N synced lyric lines.
♪ <current line>
```

### 7. Test
Play a song on Spotify (any device). Within a few seconds the console shows lyric lines and your
Discord profile widget updates. Done — it now runs without your PC.

---

## Day-to-day

- The panel keeps the process alive and restarts it if it stops. The script auto-refreshes the
  Spotify token, retries on errors, and resumes — restarts are harmless.
- Logs appear in the **Console** and in `widget.log` (File Manager).
- **Updating the code:** re-pull from Git (Option 3A) or re-upload the changed files, then restart.
- The Windows helpers (`start-widget.vbs`, `install_background.ps1`) are **not used** on a host —
  they're only for running locally on Windows.

## Rotating credentials (do this if you stop hosting or suspect a leak)

- **Discord bot token:** Developer Portal → your app → **Bot** → **Reset Token**, then update the
  host's `DISCORD_BOT_TOKEN` / `config.json`.
- **Spotify:** Developer Dashboard → your app → **Settings** → regenerate the **Client Secret**,
  then re-run `python get_spotify_token.py` locally and update `SPOTIFY_REFRESH_TOKEN`.

Because both are low-privilege, rotating instantly neutralizes any leaked copy.
