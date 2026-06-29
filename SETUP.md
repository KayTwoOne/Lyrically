# Spotify realtime-lyrics Discord widget — full setup

This builds a personal Discord profile widget that shows your **current Spotify song +
the live lyric line**, driven by a small Python script running on your PC.

There are two halves:

- **One-time setup** (browser + dashboards) — Discord app, the widget layout, OAuth, and a Spotify app. You do these once.
- **The updater** (`widget.py`) — leave it running; it pushes the current lyric line to your widget in near-realtime.

> **How "realtime" works:** the widget itself has no logic. The script asks Spotify what's
> playing, looks up time-synced lyrics, figures out the current line locally, and `PATCH`es
> your widget identity **only when the line changes** (every few seconds). That keeps you
> under Discord's rate limits while still feeling live. Expect a sub-second-to-~1s lag on
> line changes — not karaoke-frame-perfect, but close.

Method based on Chloe Cinders' guide (the saved blog in this folder). Use responsibly —
abuse gets the whole feature pulled for everyone.

---

## Part 0 — Prerequisites (already done on this machine)

- Python 3.13 ✅ and the `requests` library ✅ (verified). If you ever move machines:
  `pip install -r requirements.txt`
- Copy the config template and keep it private (it will hold tokens):

  ```powershell
  Copy-Item config.example.json config.json
  ```

You'll fill `config.json` in as you go.

---

## Part 1 — Create the Discord application + get Social SDK access

1. Go to the **[Discord Developer Portal](https://discord.com/developers/applications)** → **New Application**. Name it anything (e.g. `spotify-lyrics`). Create.
2. Copy the **Application ID** (General Information page) → paste into `config.json` at `discord.application_id`.
3. In the sidebar go to **Games → Social SDK**. Fill out the access form and **Submit**. You do **not** need a real game; access is granted instantly. (This is what unlocks "widgets v2".)

---

## Part 2 — Unlock the widget editor (experiment override)

> 🛑 **Read the security section (bottom of this file) before pasting ANY console snippet.**
> Running JavaScript in the console of a site you're logged into can fully hijack that account
> if the code is malicious. The snippet below is small and readable — **read it, understand it,
> and never paste console code you can't follow.** This applies doubly to Part 10's snippets,
> which come from a third-party server.

The editor is behind a dev-portal experiment. With your application page open:

1. Open your browser **DevTools** (F12) → **Console** tab.
2. Paste and run this snippet (read it first — it only registers an experiment override; it does
   not touch your token, cookies, or send anything to a network):

   ```js
   let _mods = webpackChunkdiscord_developers.push([[Symbol()],{},r=>r.c]);
   webpackChunkdiscord_developers.pop();
   let findByProps = (...props) => {
     for (let m of Object.values(_mods)) {
       try {
         if (!m.exports || m.exports === window) continue;
         if (props.every((x) => m.exports?.[x])) return m.exports;
         for (let ex in m.exports) {
           if (props.every((x) => m.exports?.[ex]?.[x]) && m.exports[ex][Symbol.toStringTag] !== 'IntlMessagesProxy') return m.exports[ex];
         }
       } catch {}
     }
   }
   findByProps("getAll").getAll().find(e => e.getName() === "ApexExperimentStore").createOverride("2026-03-widget-config-editor", 1)
   ```

3. Click the **back arrow** (top-left) and **re-open your application's page**. ⚠️ **Do not refresh** — a full reload wipes the override and you'd rerun the snippet.
4. Under **Games** in the sidebar you'll now see **Widget** → open it → **Create Widget**.

---

## Part 3 — Build the widget layout

In the editor you must create three sections: **Widget Top**, **Widget Bottom**, and **Add Widget Preview**, and fill all required fields.

For each field choose a **Value Type**:
- **User Data** = changes per user / per update (this is what the script drives). You also type a **Data Field** name and a **Fallback**.
- **Custom String / Application Asset** = static for everyone.

### Field map (set the Data Field names EXACTLY as below)

The `name` here must match what `widget.py` pushes, or that field stays on its fallback.

| Editor slot (Widget Top) | Value Type | Data Field (`name`) | Type | Fallback suggestion |
|---|---|---|---|---|
| Image | User Data | `album_art` | Image | (leave blank or a default cover) |
| Title | User Data | `track` | Text | `Nothing playing` |
| Subtitle 1 | User Data | `artist` | Text | `—` |
| Subtitle 2 | User Data | `album` | Text | `` |
| Subtitle 3 | User Data | `lyric` | Text | `♪` |

**Widget Bottom** — the editor makes you pick one of three layouts. For a now-playing lyrics
widget, here's how they rank:

- **Progress ✅ (recommended)** — an image + a progress bar + label text. This is the natural
  "now playing" bar and matches the Spotify-widget look. Map the script's playback fields into it.
- **Stats Grid** (alternative) — a grid of label/value cells (the FFXIV-style stat blocks). Fine if
  you'd rather show metadata than a bar.
- **Collection** (not recommended) — a list of items with thumbnails (e.g. a queue / recently
  played). The script doesn't fetch queue data, so you'd have nothing to fill it with.

Click into a layout to reveal its fields. For every field: set **Value Type → User Data**, then in
the **Value** box type the Data Field `name` from the tables below (that box IS the data-field name
for User Data). Set a **Fallback** if the editor offers one.

*If you choose **Progress*** — it has an **Objective** group and a **Progress** group:

| Group → field | Value Type | Value (`name`) | Type |
|---|---|---|---|
| Objective → **Image** (required) | User Data | `album_art` | Image |
| Objective → **Name** (required) | User Data | `track` | Text |
| Objective → **Description** (toggle on, optional) | User Data | `artist` | Text |
| Progress → **current / value** | User Data | `progress_sec` | Number |
| Progress → **max / total** | User Data | `duration_sec` | Number |
| Progress → *or* a single **percentage** | User Data | `progress_pct` | Number |

> The Progress group may ask for a **current + max** pair (use `progress_sec` + `duration_sec`) or a
> **single 0–100 value** (use `progress_pct`). Both are sent, so use whichever it shows.
>
> **Lyrics-forward alternative:** set Objective → Name to `status` and Description to `lyric_next`,
> so the bottom shows playback status + the upcoming line above the progress bar.

*If you choose **Stats Grid**:* fill cells with any of `status`, `progress` (text "1:23 / 3:45"),
`album`, `lyric_next`, `lyric_prev` (Text) and/or `progress_pct` (Number).

> The script sends a bar as both a **percentage** (`progress_pct`, 0–100) **and** as
> **current/max** (`progress_sec` / `duration_sec`) — so whichever shape the Progress layout
> expects, the value is there. Use the field(s) it asks for; ignore the rest.

> ⏱️ **Bar movement:** by default the widget only updates when the lyric line changes, so a
> progress bar advances in steps. If you want it to creep smoothly, set `heartbeat_seconds` in
> `config.json` (e.g. `10`) — see the Tuning table. Leave it at `0` to minimize requests.

> You don't have to use every field. Only the names you actually create need to match —
> extra fields the script sends are simply ignored. At minimum use `album_art`, `track`,
> `artist`, `lyric`, and `status`.

> 🖼️ **About the image (`album_art`):** set the Image field's Value Type to **User Data** so the
> **live** cover comes from Spotify as a URL — that works (it's how the blog's example pulls an
> external portrait, and how Spotify widgets show covers). The only place that needs an *uploaded*
> image is the **Sample Data preview** and any **Fallback** image (the editor's image picker is
> upload-only). Use the included `sample_album_art.png` for those.

### The "Add Widget Preview" section (required)

This is the **static teaser** shown in the **+ Add Widget** menu *before* any live data loads —
the "cover" people see when deciding to add your widget. It has **no effect on the live widget**, so
make it look nice and move on.

Because there's no live user at that point, fill every field with **Custom String** (for text) or an
**Application Asset / Custom** image — **not User Data**.

It offers two layouts:
- **Hero ✅ (recommended)** — large image-forward card; great for showing off album art.
- **Contained** — more compact card with a smaller image. Use if you prefer a tidier teaser.

Click a layout, then for each field set Value Type to **Custom String** (or **Application Asset** for
the image) and type a representative example, e.g.:

| Field | Value Type | Example value |
|---|---|---|
| Image / cover | Application Asset (or Custom) | an album-art-style image you upload to the app |
| Title / name | Custom String | `It's Not Like That Anymore` |
| Subtitle / artist | Custom String | `Tiffany Day` |
| Extra line (if present) | Custom String | a sample lyric, e.g. `…it's never that personal` |
| Tagline / description (the footer) | Custom String | `Live Spotify lyrics on your profile` |

> **Application Asset image:** if the image field only accepts an Application Asset, upload one first
> under the app's **Rich Presence → Art Assets** page in the Developer Portal, then pick it here. If a
> **Custom** image option accepts a URL, you can paste any cover URL instead.

Tip: a "My Music" header looks good as a **Custom String** at the top (static), like the
example widgets.

---

## Part 4 — Sample Data + Generate JSON

1. At the bottom, open the **Sample Data** tab (or the pencil next to any User Data field).
2. For each User Data field, click **+ Add Field** and enter three things:
   - **Key** = the data-field `name` (e.g. `track`, `album_art`)
   - **Type** = pick from the dropdown — **String** (text), **Number**, or **Media** (image)
   - **Value** = a demo value. ⚠️ **Media fields here do NOT take a URL** — click **Choose Image**
     and upload a local image (use the included **`sample_album_art.png`**). This is *preview-only*;
     it does **not** affect the live widget.

   [`widget_sample_data.json`](widget_sample_data.json) lists every Key/Type/Value to enter, in
   order. Only add the Keys you actually used in Widget Top/Bottom. (The static **Add Widget
   Preview** fields are *not* entered here.)
3. The preview should fill in. When it looks right, click **Generate JSON** (top-right of the Sample
   Data window) and keep that JSON somewhere — it's the body shape the script sends.
4. Close the modal → **Save Changes** → **Publish** (top-right).

---

## Part 5 — OAuth2: let the app manage *your* widget

1. Sidebar → **OAuth2** (under Overview).
2. Under **Redirects**, add a redirect URI. Easiest is `https://discord.com` (used only as a landing page). **Save Changes**.
3. Scroll to the **OAuth2 URL Generator**. Check scopes **`openid`** and **`sdk.social_layer`**. Pick your redirect URI. **Copy** the generated URL.
4. In the copied URL, change `response_type=code` to **`response_type=token`**.
5. Open that URL once and **Authorize**.
   - If you get *invalid scopes*, your Social SDK form (Part 1) isn't approved yet — recheck it.
   - The consent screen lists a lot of permissions — that's expected for the social layer scope.

---

## Part 6 — Confirm permissions (REQUIRED for a personal-only widget)

Skipping this makes the widget show *"Your game stats are still syncing. Keep playing!"* to others.

1. Discord app → **User Settings → Authorized Apps**. Find your application.
2. It must have: *Send you direct messages*, *Manage your Discord friends list and blocked users*,
   *Access your server and channel membership details*, *Access your Friends list and their online status*,
   *Update your activity status on Discord*, *Send and receive messages from Discord*, *Access your profile information*.
   (These come from the `sdk.social_layer` scope you authorized in Part 5.)

---

## Part 7 — Bot token + your IDs → `config.json`

1. Developer Portal → your app → **Bot** → **Reset Token** → copy it → `config.json` → `discord.bot_token`.
2. Your **Discord user ID**: enable Developer Mode (Discord Settings → Advanced), then right-click your name → **Copy User ID** → `config.json` → `discord.user_id`.
3. Confirm `discord.application_id` from Part 1 is filled.

`config.json` Discord block should now look like:

```json
"discord": {
  "application_id": "123...",
  "user_id": "456...",
  "bot_token": "MTA5...."
}
```

---

## Part 8 — Spotify Developer app (for current song + position)

1. Go to the **[Spotify Developer Dashboard](https://developer.spotify.com/dashboard)** → **Create app**.
2. Name/description: anything. **Redirect URI:** add exactly **`http://127.0.0.1:8888/callback`**
   (Spotify requires the loopback IP, not `localhost`). APIs: "Web API". Save.
3. Open the app → **Settings** → copy **Client ID** and **Client Secret** → `config.json` →
   `spotify.client_id` / `spotify.client_secret`. Leave `spotify.refresh_token` empty.
4. Get your refresh token (one-time):

   ```powershell
   python get_spotify_token.py
   ```

   A browser opens → **Agree**. The script captures the redirect and writes
   `spotify.refresh_token` into `config.json` automatically. You should see `✅ Success!`.

---

## Part 9 — Issue your widget identity (first run does this)

The widget won't show to others until the app has pushed data to your identity at least once.
Running the updater does exactly that — so just start it:

```powershell
python widget.py
```

Play something on Spotify. You should see logs like `Now playing: …`, `Loaded N synced
lyric lines.`, and `♪ <current line>`. Leave it running.

<details>
<summary>Optional: issue the identity manually with one PowerShell command</summary>

Equivalent to the guide's step (the script already does this on first PATCH). Replace the
placeholders:

```powershell
Invoke-RestMethod -Uri "https://discord.com/api/v9/applications/{APP_ID}/users/{USER_ID}/identities/0/profile" `
  -Method PATCH `
  -Headers @{ "Content-Type"="application/json"; "Authorization"="Bot {BOT_TOKEN}"; "User-Agent"="DiscordBot (https://github.com/discord/discord-api-docs, 1.0.0)" } `
  -Body '{"username":"me","data":{"dynamic":[{"type":1,"name":"track","value":"Hello"}]}}'
```
No error = identity issued.
</details>

> ℹ️ **We intentionally skip the blog's "Widget Management using Bots" chapter.** That chapter is
> for building a *multi-user service* (slash commands so other people can link their accounts). For
> a personal, just-for-you widget it's not needed — `widget.py` pushes your data directly with the
> bot token, exactly as the blog says you can ("if you get no errors … skip the Widget Management
> using Bots chapter").

---

## Part 10 — Add the widget to your profile

Discord no longer exposes a simple button for this; you add it via a client-side snippet.

> 🛑 **HIGHEST-RISK STEP.** You'll run JavaScript in the console of your **logged-in Discord
> client** — where your real user/login token lives. A malicious snippet here can steal that
> token and **take over your whole Discord account** (this is the "console self-XSS" attack
> Discord's own warning banner is about). Before pasting anything from the thread:
> - **Read every line.** It should only call internal widget/profile functions.
> - 🚩 Refuse it if it references `localStorage`, `document.cookie`, `token`, `fetch(`/`XMLHttpRequest`
>   to any non-Discord domain, `eval`, base64 blobs, or anything obfuscated/minified you can't read.
> - When unsure, **paste it back to me and I'll review it line by line before you run it.**

1. Join the **Discord Previews** server (invite: <https://discord.gg/discord-603970300668805120>),
   then open this thread:
   <https://discord.com/channels/603970300668805120/1509942620762276011>
2. Run the "add widget" snippet in your **Discord client console** (desktop-app DevTools or the web
   client — `webpackChunkdiscord_app` only exists there, not the dev-portal page). The snippet below
   is the community version, **reviewed line-by-line and found clean on 2026-06-29** (it only uses
   Discord's own internal API client to read your profile and write your widgets list — no token
   access, no external requests, no `eval`). Replace `APPLICATION_ID` with your app ID.

   ```js
   let _mods=webpackChunkdiscord_app.push([[Symbol()],{},e=>e.c]);webpackChunkdiscord_app.pop();
   let findByProps=(...e)=>{for(let t of Object.values(_mods))try{if(!t.exports||t.exports===window)continue;if(e.every(e=>t.exports?.[e]))return t.exports;for(let r in t.exports)if(e.every(e=>t.exports?.[r]?.[e])&&"IntlMessagesProxy"!==t.exports[r][Symbol.toStringTag])return t.exports[r]}catch{}};

   api = findByProps("Bo", "Cu").Bo
   async function addWidget(appId) {
       id = findByProps("getCurrentUser").getCurrentUser().id;
       current_widgets = (await api.get("/users/" + id + "/profile")).body.widgets
       if (current_widgets.map(x=>x.data?.application_id).includes(appId)) {return console.log("Already in your widgets — remove it via Discord client to re-add")}
       current_widgets.unshift({"data": {"type": "application","application_id": appId}})
       await api.put({url: "/users/@me/widgets",body:{widgets: current_widgets}})
   }
   // Usage — put YOUR Discord application ID here (same as config.json discord.application_id)
   addWidget("APPLICATION_ID")
   ```

   > ⚠️ **Re-verify if it changes.** This was clean *as of the date above*. The minified names
   > (`Bo`/`Cu`) are version-specific — if it errors with "cannot read property 'Bo' of undefined",
   > that's a harmless Discord-update drift, not a risk; ask the thread for the current names. If you
   > ever get a *different* snippet, re-read it against the red-flag list above before running it.

3. Also set the client experiment **`2026-03-application-widget-v2-renderer`** to **Variant 1** —
   this is the renderer that actually draws v2 widgets on profiles. ⚠️ Note this is a **Discord
   *client* experiment**, not the dev-portal one from Part 2, so Part 2's snippet won't set it.
   Use whatever method the thread provides, or ask in the server's #general.

With `widget.py` running and a song playing, your profile widget should now scroll the lyrics live. 🎵

---

## Part 11 — Run it hidden in the background (Windows)

Goal: the updater runs with **no window, no taskbar button, and no tray icon**, starts on its
own, and sips resources (it mostly sleeps). This works by running the script with
**`pythonw.exe`** (Python with no console) instead of `python.exe`.

> Do this only **after** `config.json` is filled and `python get_spotify_token.py` has run.
> Run `python widget.py` once interactively first to confirm it works (you'll see the logs).
> When running hidden you can't see stdout — so the script logs to **`widget.log`** next to it.

### Method A — Startup folder (recommended on this machine) ✅

Most reliable here because your Python is the **Microsoft Store** build (its `pythonw.exe` is an
app-execution alias that resolves cleanly in your normal logon session). Already verified working
on your setup.

1. Double-click **`start-widget.vbs`** — the updater starts hidden immediately. (Check `widget.log`
   to confirm it's alive.)
2. To auto-start at every logon: press **Win+R**, type **`shell:startup`**, Enter. Right-drag
   `start-widget.vbs` into that folder → **Create shortcuts here**.

That's it — it'll launch hidden at each logon.

- **Stop it now:** Task Manager → **Details** tab → end **`pythonw.exe`**.
- **Disable auto-start:** delete the shortcut from the `shell:startup` folder.

### Method B — Scheduled Task (optional; adds auto-restart on crash)

Gives you start-at-logon **plus** automatic restart if it ever crashes. From a normal PowerShell
window **in this folder**:

```powershell
.\install_background.ps1      # register + start it (no admin needed)
.\uninstall_background.ps1    # stop + remove it
```

Manage it:

```powershell
Get-ScheduledTask -TaskName SpotifyLyricsWidget | Get-ScheduledTaskInfo   # status
Stop-ScheduledTask -TaskName SpotifyLyricsWidget                          # stop now
Get-Content -Wait .\widget.log                                            # live logs
```

> ⚠️ Store-Python caveat: Task Scheduler occasionally fails to launch Store Python's
> app-alias `pythonw.exe`. If the task shows as "Running"/"Ready" but `widget.log` never
> updates and no `pythonw.exe` appears in Task Manager, use **Method A** instead, or install
> Python from python.org (a normal install removes the alias quirk entirely).

### Resource footprint

Tiny. The loop sleeps `tick_interval_seconds` between checks, only calls Spotify every
`poll_interval_seconds`, and only PATCHes Discord when the lyric line changes — so CPU is
near-idle and memory is just the Python + `requests` baseline (~20–30 MB). `widget.log` is
size-capped (rotates at ~1 MB, keeps 2 old copies).

---

## Daily use

- If you set up Part 11, it just runs — nothing to do. Otherwise start it manually with
  `python widget.py` (Ctrl+C to stop).
- It auto-refreshes the Spotify token, follows track changes, handles pause/idle, and retries on rate limits.
- Check on a background instance any time by reading **`widget.log`**.

## Tuning (`config.json` → `options`)

| Option | Default | Meaning |
|---|---|---|
| `poll_interval_seconds` | 5 | How often to re-sync true position from Spotify (drift correction). |
| `tick_interval_seconds` | 0.5 | How often to recompute the current line locally. |
| `min_patch_interval_seconds` | 0.75 | Hard floor between pushes. The script *also* paces itself automatically from Discord's rate-limit headers, so you rarely need to change this — raise it (e.g. `3`) only if you want to be extra conservative. |
| `heartbeat_seconds` | 0 | `0` = push only when the lyric line changes. Set e.g. `10` to also refresh every 10s while playing, so a progress bar advances smoothly (costs ~6 extra pushes/min). |
| `username_format` | `{track} — {artist}` | The identity `username`. Placeholders: `{track}`, `{artist}`, `{album}`. |
| `no_lyrics_text` | `♪` | Shown for intros/gaps and tracks with no synced lyrics. |
| `instrumental_text` | `♪ Instrumental ♪` | Shown for instrumental tracks. |
| `show_when_paused` | `true` | If false, shows `⏸ Paused` instead of the frozen line while paused. |

## Troubleshooting

- **Widget shows "still syncing" to others** → Part 6 permissions missing, or identity never issued (run `widget.py` once while a song plays).
- **`No spotify.refresh_token`** → run `python get_spotify_token.py`.
- **Spotify `INVALID_CLIENT` / redirect mismatch** → the redirect URI in the dashboard must be exactly `http://127.0.0.1:8888/callback`.
- **No lyrics for many songs** → LRCLIB is community-sourced; some tracks lack synced lyrics. The widget still shows track/artist/album and `♪`.
- **`Discord PATCH 401/403`** → bad/expired bot token, or you haven't authorized the app with `sdk.social_layer` (Part 5), or wrong `user_id`.
- **Lyrics slightly off-beat** → lower `poll_interval_seconds` (e.g. 3) for tighter drift correction.
- **Frequent "Rate limited" lines** → the script now auto-paces from Discord's rate-limit headers and
  won't block or fall behind (it resumes with the *current* line). Occasional notices are normal on
  fast songs. The endpoint simply caps how often a profile can update, so very rapid lines are shown
  at the fastest cadence Discord allows rather than every single line.

## Security / threat model

Ranked by how badly it can hurt you.

### 1. Console snippets = the real account-hijacking risk (Parts 2 & 10) 🔴
Pasting JavaScript into the console of a site you're logged into runs with **your full session**.
A malicious snippet on `discord.com` can read your login token and **take over your account**
— password, email, 2FA-protected actions, the lot. This is the single most dangerous part of
this whole process, far more than any token in `config.json`.
- Only paste console code you have **read and understood**.
- Part 2's snippet is included here in full and only registers an experiment override.
- Part 10's snippets come from a **third-party server** — treat them as hostile until you've read
  them. Red flags: `document.cookie`, `localStorage`, `token`, network calls to non-Discord
  domains, `eval`, or obfuscated/minified blobs. **Send them to me and I'll review before you run them.**

### 2. Never hand your token to a "widget service" 🔴
The whole reason this guide exists is to avoid paid third-party widget services. **Never paste
your Discord token, bot token, or authorize a random site** that offers to "make widgets for you" —
that is literally giving away account/identity control. Do it yourself with the steps here.

### 3. `config.json` secrets 🟠
It holds your **Discord bot token** and **Spotify client secret + refresh token**.
- It's already in `.gitignore`; never commit, screenshot, or paste it.
- **Blast radius if the bot token leaks:** an attacker can control your *application/bot* and
  deface your widget identity. It is **not** your user login token — it can't read your DMs,
  change your password, or log in as you. Still, rotate it: Developer Portal → Bot → Reset Token.
- **If the Spotify secret/refresh token leaks:** the scopes are **read-only**
  (`user-read-currently-playing`, `user-read-playback-state`) — an attacker could see what you're
  listening to, but **cannot** control playback, edit playlists, or change your account. Rotate via
  Dashboard → Settings (regenerate secret) and re-run `get_spotify_token.py`.

### 4. Least-privilege choices already baked in 🟢
- Spotify scopes are read-only (above) — no `user-modify-playback-state`, no playlist scopes.
- The local OAuth helper binds to **loopback only** (`127.0.0.1`), validates the OAuth `state`
  (CSRF), handles a single result, and HTML-escapes anything it echoes back.
- All API traffic is HTTPS; the only `http://` is the loopback redirect. Every network call has a timeout.
- The script only ever **reads** from Spotify/LRCLIB and **writes** to your own widget identity — it
  has no other Discord reach.

### 5. Discord OAuth implicit token (Part 5) 🟡
The guide uses `response_type=token`, so an access token lands in the redirect URL fragment in your
browser history. It's scoped to your own app (`openid sdk.social_layer`) and goes to `discord.com`,
not a third party, but if you're cautious: clear that history entry afterward, or use a redirect URI
you control. Low risk for personal use.

**If you think you ran a bad snippet:** immediately change your Discord password (this invalidates
existing login tokens), confirm 2FA is on, and review Settings → Authorized Apps and Devices.
