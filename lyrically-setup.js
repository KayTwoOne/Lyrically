/* ============================================================================
 *  Lyrically — Express Setup  (run in the Discord Developer Portal console)
 *
 *  One paste sets up the ENTIRE Discord side and hands you a ready config.json:
 *  it prompts for your Spotify keys, creates the app, enables the Social SDK,
 *  creates + configures the widget with Lyrically's exact layout, publishes it,
 *  authorizes it, adds it to your profile, resets the bot token, opens the
 *  editor, and downloads a config.json filled with everything it collected.
 *
 *  You provide: an app name (optional) + your Spotify Client ID/Secret.
 *  It fetches automatically: Discord Application ID, your User ID, Bot token,
 *  and imports the full widget structure.
 *
 *  HOW TO RUN
 *    1. Open https://discord.com/developers/applications  (logged in)
 *    2. F12 (or Ctrl+Shift+I) -> Console tab
 *    3. Paste this whole file, press Enter. Fill the form, click Start.
 *       Solve the captcha / 2FA if prompted.
 *    4. Click "Download config.json", drop it in your Lyrically folder, then run
 *       get_spotify_token.py and widget.py.
 *
 *  Discord-API automation adapted from aamiaa's "Widget Creator":
 *  https://gist.github.com/aamiaa/7cdd590e3949cd654758bc90bcb4710b  (credit: aamiaa)
 *  Widget layout imported from Lyrically's own config.
 * ========================================================================== */
(async () => {
  "use strict";

  // Lyrically's exact widget config (display_name + surfaces + base64 preview asset).
  const LYRICALLY_CONFIG = JSON.parse("{\"display_name\": \"Now Playing\", \"surfaces\": {\"widget_bottom\": {\"layout\": \"widget_bottom_progress\", \"components\": {\"progress\": {\"fields\": {\"current\": {\"value_type\": \"data\", \"presentation_type\": \"number\", \"value\": \"progress_sec\"}, \"max\": {\"value_type\": \"data\", \"presentation_type\": \"number\", \"value\": \"duration_sec\"}}}, \"objective\": {\"fields\": {\"description\": {\"value_type\": \"data\", \"presentation_type\": \"text\", \"value\": \"artist\"}, \"image\": {\"value_type\": \"data\", \"presentation_type\": \"image\", \"value\": \"album_art\"}, \"name\": {\"value_type\": \"data\", \"presentation_type\": \"text\", \"value\": \"track\"}}}}}, \"add_widget_preview\": {\"layout\": \"add_widget_preview_hero\", \"components\": {\"hero_image\": {\"fields\": {\"image\": {\"value_type\": \"application_asset\", \"presentation_type\": \"image\", \"value\": \"widgetpreview\"}}}}}, \"widget_top\": {\"layout\": \"widget_top_hero\", \"components\": {\"title\": {\"fields\": {\"text\": {\"value_type\": \"data\", \"presentation_type\": \"text\", \"value\": \"track\", \"fallback\": {\"value_type\": \"custom_string\", \"presentation_type\": \"text\", \"value\": \"Nothing Playing\"}}}}, \"subtitle_1\": {\"fields\": {\"text\": {\"value_type\": \"data\", \"presentation_type\": \"text\", \"value\": \"artist\", \"fallback\": {\"value_type\": \"custom_string\", \"presentation_type\": \"text\", \"value\": \"—\"}}}}, \"subtitle_3\": {\"fields\": {\"text\": {\"value_type\": \"data\", \"presentation_type\": \"text\", \"value\": \"lyric\", \"fallback\": {\"value_type\": \"custom_string\", \"presentation_type\": \"text\", \"value\": \"♪\"}}}}, \"hero_image\": {\"fields\": {\"image\": {\"value_type\": \"data\", \"presentation_type\": \"image\", \"value\": \"album_art\", \"fallback\": {\"value_type\": \"application_asset\", \"presentation_type\": \"image\", \"value\": \"music-resized\"}}}}, \"subtitle_2\": {\"fields\": {\"text\": {\"value_type\": \"data\", \"presentation_type\": \"text\", \"value\": \"album\"}}}}}}, \"assets\": {\"widgetpreview\": {\"asset_type\": \"image\", \"content_type\": \"image/png\", \"image\": \"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAfxUlEQVR4nOVdWYwcx3n+queenb0v3hRPkbqow5JNObbMOJAAxzYSAXGMBA6StwAGAuQhD3mJEdgPAfIUIAGCBAgQB3Ycx4YPWZJtWZdNxZIoiTIl3lqSy10uyeWec59dQVX3zFR3V/Ux07M7S//Y2emprq6urvrrr//4qpqcOHHinxASUUrNA/ZHLWmWb/O8Nc24gh1TSolx2MpDmsc80frbUp7lYxTuSOe5+S2p5JwiXXEPe357Psd5yfOKeZRtJrav7bgbigI4jJCJEqMhlMS713aN5TRpMpAzp3CymdJmu1bp4m04w5jnDcYCIe4VDJOsT9b8TWWN4EmdXOPNAAdCLVHaR0GfrtX5zR9iy4nn3Draz40cpEyXXcT5yJboYP72hWIRhBhSaHO732CAbSGX6VlN2VlLW6qfVGQK4Xcrs2fnh0mkOc34fHIxt0wCeHZwDziAMcBAuEV61lHs61ZniaPBVAEUV8tOhdcyRMWgknRZNd1qYmFySSavaaEDqeqLAcIZMULdCPWcAojrtBFG//vjCeKYYpR1dBYmvYUL84pMLs9FezG1upIWWkkkXFVJmY83sPpa90TXzifCR5Hdxz3cKk8kqqvfa0PU/HvDAAJ1zaVuDyppOKIYLQGI2MrxJT8ok+lBSMK81vPup0nQ+20WA3RSUaYVCz/CMUUltxGzwHaJZDr3uEngWglHzuK9HrsHAqBXEqCTa+RPb08l3Y02KrcgDQrMdgEvsMwAMg3AS0L0gHojAbrlEBoCcxFfJVDhm4hGiUxCOG8R1JC3skDX5fUrA3j6ASSdI0psUXw7VHPaLRM6BC1p38twHtuVQfNAon0GG7HefE/8T5P9zQAeD+KR6KrASQxIKbmZ03JPI8wWlrGnz7q4k5sC4pbaS99WjxggTCKu86RabCo5oCnqqcSlrFAcwhl5XqZuWzbZz4pe8N86BnDXzdXdrBq1Dl2aSIqy++uCDVhVlXxPARunC/SGAcKsv63V/E+DNKB1ADFC2MxkTg0KyRCyZPZ6toC+jU1kABJeNr9TvkfvENWMgk7qELAqvqk7P9HWmwLEPqKhP7VlNAs/HKOcernZ1VpGwMp5ZPcqjdx1OoDAAaRT00h5wmLTC+W53IgonFEugalg85dH7i4ZZMvpAH4cH/4VJ7/3VOoAKieQASCyUVM5cKapf3uSBwf0wlG0yVOAHxu+ZxoxVUQAHb8luA9prZyuw6B192KZu0wJVEY3RN3AI0IiHRUtM196U1HDpwq3r7U4BnBwq2TYpNR87zIJ4Ic8pwCiSlSKbZm3j5gXtv5518JHtg6jms5i6BaTAD6pE7vW3xjw7bchbUnAWpnXh/grTcVg4oWdjVh7d/fSLbTJOoD3o6ncdu3fKulsudI+xzs8fKR96JjK5WwqC+eiS7IW0Ltxv5WmAI9WlSpallhPO0U4dvARbTOGL2Ve6svvuquESUqkHoqAzZ0C/PhSPWEyHd+eit8mikmUuq4l+6p6UIboHJqyRSWAr+f0sI0DKVrEa5qlQWrmKcKDlmKNQCj913ePDtCVJ75ZhqwQhUePBJpKiCJCaP7yYRl2qRRsRExwk62AEMpQeulkP92Cx8R+qV0f8BGItnkGAz+gPO5/11oBPXs0qxYlqPdSC4+YKCG5waHoRCLFZ3X7PPJb9hIruMkM0KOAqmLylUgGIvy0i3xekkuE0Jca2BlRq4LSg/UA4tKwzSNZkyvyxZJAbBBIDFHEByniGZBYGogNALEUQTQJRBIEWhREi7bFL1+K3wD0BkW9AtRKFPUyRaVAUcnqqBYpSms6Ka3pKKzoqOR0Witb3MXyKnmsgDdu7r8prBcYDdP+1dptwdImYQiGzWUAG5EIkBymSE/pSE9Qwr5T4xSpMYpoCiBazwMppFGjKK9T5BcbyN5uYP1GHWvsM19HOdsQVjBLOEA2ifgJ8suhC5LrhYSQZoVwGUC2Xt6F4kM6Bnc2kNmlk8yOBgamWUdvhO6rpkiMYGCCfTRM3xdrpbPHKq40sDJbx9KVKhYvVfk3kyCdPr9RsI8sPWyScBnApaasbWIZHYN7Gxi+p06G7qkjMSINtfclEQIMjEf4Z/ejCZ7GpMXqXA03z1awcLaC2xfKqJbC662WkGkyVg8YgZw4cUIPt//N2cpkBhKhGH+gisljVTKwvcHFOO/0LdLxQaheobh1oYK500Vcf6+E9Zs1Ye8gyx5Iin2B2ruGyH/L9wvqIwagluPhQzXsOVEm8WEdRDP0Ztb5vWAAqpsf04nb2oFCUOc0zdQjNoD5KAVWZqu48mYBM/+Xx9qNqmVjKiNPs4PtG0gZKiBnmebAF9Jb+fqVAZiJvPOpEpl8pNpq8I4ZgALVIlBeISivwfisA5UsUM1TWi2Ymn2FcpHMPkzj5+2lm1FeVogGaFHKrYRIjNLYAEF8ACQ+ACRHCJLDGtJjxtyfGtUQT4fHJawud2YquPzLHD46mUd+pdZqL7cdwZoMoDrflwzAOnzP00UydqTKG513OGcCc753YYBakaC4SJC/SZC/RVBYJLS0xDrYMOMcotMmVj23erOmE7blXPNbPEc0ShJDBIPbIxjermFkVxSje6MY3h5BJN4dYzTqFLPvFHHupXVcP11Ao65LOr6tTyk7XoZT6wcG2P5kmUw/XjFQLG4MAKC4rCF7LYLcPKG5eQ3FJcI7ulmWo9OMH8JvUyz63h9QzhjUui8hUV0TiQPDOyOYOBjD1KE4pg7HkB6NdNxe2ds1fPjTNZx9aR2l9XrrXq1v8VmENu5bBhjYUcOBPywQZs/LGKBRI1g5H8X6lSjNXtdQzRFXpchto0W3TpWmKaQFNc4ZE4UgEQTGUEoT9kzD26PYdn8cu44lMX0kgVgyuISolXVceDWL0z9awep8pf0MLnO/qHD3BwMQ4NCXciQ91TBHuZUBlj6M4frLCVorGtmVHW0b1dI8HTCAkC6Kfph9ze0suQSQ7yoqu0c0QbD9vgT2PJ7CnkdTSI8Ekw5M+s28mcep7y5h8aPShugAkX379n0tjIIG99Yw+XDFCM7ZxP3CGwk693ICes3H6HB5LrvQk0N1lNEbvzEY4lq+SxF6A9z0Y3P8hy9kcfNcGXqdIjMZ48zhWYZGML4ngQeeGcXUwSTWFqoorNTd6tw/DLDt42WSHNctHc8+azNRzP485d+b5dZPtjKkRaruI68AMcq1+GLFopgZ0RFshVkgucU6rp0q4sMX17F8rYp4SsPgFAtWuBfJ7ji2y2CEzHgMc2fyXHl0veFmMgAT8Ts/XSJarK3hN5tt5odpWi95tKEYk3OTALa+kEGuVKFTtxpQdTampKBbYlJgZa6GS6/ncOm1HJ/zR3bEEEu5B2PZ404fSuGejw3iyls5VEuhqWvhMkB8UMfkI4b4bzGABuQXIrh9ynCbupIj4NG5BJCkOQBWzhsRdQX8+qq9spmMVCk0cONMEWdeWOcinkmEgVF3j/zAWBT7nhjExV+uc+YJUq0NYYDEiI6xo1UrAzDxfzmO7LWA4Qa3B/Pz0EodwFexBJ0S9V8tpnOyKWLpagVnf76OhXMlZMajGJpiIlR+fWooiumDKVx4db3l7ewfCTCsY/SIkwGy16I0N+fNABYcVoAHCwLK8VEuMa8OZWw54YF2tFn7KHuriguvGI6h5FAEozsTUj4e3hZHca2OW5eYhdBHiCDakO+uE036w8WKuYIAN9VqnSRZDRIiTRyRo+gu5KwDxeNRFGPQmxdK+Mk35vHc1+f4VCGj4386hXi6GVHrEwZQKXks+udrPPlkZ7vSJ1tXoFpIYmOeFtoK8gqYLOFfoXSiDf1q7c4TV9/O40dfm0O96jyXHoniyIkRhEWhMEAtr6FRdjZLelsDqXFTaXErQODmIKJNJl9U+DnbbGG7DVFAwORlSZVP0ulWuPILF84X8fb/3JGeO/LUiOeKqQ0FhLAwbGEhiuEDRpRLfM5dnymTy99PN93tigKodDG+at8WZm4yLGB8gLJvEs+AB2kYJjCSYMEc0nI/8xBxwwBv1MoGHpBFD8tZhv+jtLjW4Kge2va3tG9vVEwiZpzIH88t8hXP74YtfP/HK3js2XEkBqwexe33phBNaaiFYBaGhghavRinwwdNV5/QZMP769j1VJnMv5Zw8V4KjdNsXALEMxTpaR0DU5SkJinDCSI5SpEYZKFd+/WyY08i7LaMMcrrOskt6sjdapDszQbW5htYX6iTapE3so0ROhh9Qk9bYYBqDmD3njtTwMHjQ5b0aELD0FQcy7Nl9A0D5K7FUF6OIDUhKC9mk23/eBWJYZ3MvpSg1bxsQFGOHMrs0DG4WydDu3VkduqcAdyBoCEQMVDFsVQEg9siwEMxiwMnd1vH0pUaWZqp4faFKrK36tzl61BI7XhOYgS6ZBls77xyZaiV6xXguDM9mek8CtkTBmDPunAySQ/8QUE6C4/dV8Po4TpZuRhFdjZCWSRQi1GkJxtkcLeOwV06F9/9RFqU8PAv+xz4VJKnsSnj9vkqbpyp4MaZMoqrDflAlm0+L5MAHo/cUIQCGLqp70Ch+bkY7rwfx9SjFel51uGTD9Yw+ZCfqFB/Unokgn3HU/yj6+DI4OunSrj2toEB9DewVdzgpOFtbYkkUq3SR0pgk5hoWziZovEhnYwcsjXGXUiaBkwdjPPPY18e5szw0ckCZt4ooMQlQ3edxHAVe4453+nFFNvcShVhUOgLQ1jlrr2YprsrJTLxYDXczqcMeWtgAsurBj6QYQIrOYp6CXxFT71MKRObtEGJrlPDKtQosxxINMEUKMOCSGQI4oNAekxDepRhAklXcC92n8kDcf554k9GcP3dEs7/Iof5M0VuhdgeQ3psp8OfHEJmwikB1herKC7LHUWbygBNs415BmdfSnE38K4TJcKWcgUlvQ6OD8wxfOACQf42aHHJAIM68YEtcIYJomkCPSxooNZvERMItlENBWXTU2qEkMFtGp/zR3ZHOA6QgUSDOt3Y4pJ9n0jzz9pCDWd/msWFV3KoFk19wWprKpngY380IU2/8mYutGBAqJAwGWJFi1NMHqtg8uEqSU208QJ2alQJsnME61c0rF/XaG6BoFEJBw5mpotQL9U1REjnph8Dh47vi2DqSAzTR+IcIKp1oICXczrO/mwdHzy/hsIaMyPc4eFMGv3ldw4jGtccEvabX72MpavlUFBBPWeANniRIjGqgy0BS4w2SCRhjPJqHijc0mjuhoZGtXs8oCkCbPksUsKCBqbthhcgYsaxrHwGH99+fxw7j7FPwvDLByAWzj37syxO/2AVhVUXeDgovvIvBzC+1xpOv3RyHc9947oFOdw/qGD+z45dM86IHWM9r+50Ox6vYwkg3NsxDYDfxDLyhXMKdLFRL+aR3H5fnFsEDAMYC7CWgHnx3n9uDad/sMIDP7L22PlAGl/8u90tT+DybAXf+9urfF1B/4FCGclWrjTRuALYUzxv7+hmmqMzJRBw/1OAUTmZ+KcG6kcEhLpKAIMhzJU7IiA0SbD38RTuPTGA6XsTvh1YLLx76jvL+ODFNei6c4Aw2PneRzKolhq4eiqHWqXdXXRLSADXjpfPf51PAe1yrJ1sOOodo582dUZrmhfTtJZuKeoysjOKo08P4tCnB3xPEdfeyeOn/7jQCgO7tZe9rfsCFMqoFVLTKEaP1pj3j8TSlLuIXaFeQQp3u6i5DMxO3rAE4oSCKRpXUZSYu5Rt8AWi53+eQyXfwOiuOAeEutHIjjh2PZTG5ZM5HrjyU+EwKFQGYMS0/H1fLJJtT1QIW/s/dqROkhMNsnqhO4vT/+aJMqCov1tAtM5U5fvmC8Lj+bculLkZWFytY2xv3FUiMJt/dGccl09mvad32ocMwOo0uLuOHU+WOXajCRFLTeocG1jNagosv7+yO83kIgCI8N2M+PmFLvgm5rdY/KjCzUC2y8jkfraCSM4IY7sT3KXMzLyNEAGhxtqIueuHkyiLBppHvSQV7stx12bYmjZnUztKSNW+3dSfSYTfPLeGb311FmeeX1NO4ce/MsmdSRtBIccCDGAIN5HEdJ0gfyPawdAVjhUuM6ZtM8cMW7jJfAt8bYKx8IKwYA1tEFqvUlIrU1ovU9Ko8QhbU5MiZsEO5cHkDEkveERvfFC1oONX/36Ho4JPfHXaIVUYOnj/xweNqaDHFLIrmK3j1zD/aooyJBBzr7LlYGxNYGVVgOdLB6Ssd41kvnnUCEVmik0nlKTHTWDIEAONMPApe92P6rWPbTHPvGgMEVQtgO8KVlzRkb+ts5g/YZtBMUBIvWoyg+HXllB4MowtEZ8+lMT9zww7zh18cgsyQJOWziSweilGmeePbezAQaOtgeajUimKoT06hvfoHCuQ2WbsEtYtMWnBnDVse7mBSWaZWH26bJOJ7EKDLF+p485HdSxeqhnxfhoA+hWQ3vneMo7+3hC0iJV7tx0J4YE3c5u4RomgUIq0/QJu2DhCMbhDx+jhBhk92EBmu85H/UZTNEEwti/KP4c+a1SdwcMWPqjixvsVvjNYo6Y7q9+FXGDrB1fnqw6Xb2bMWFDK4GpbSgewH7fsKvGVzeaSy4EdDUw8UCfjR+tIDPf2QTshQoDhHREM70jh6DMptokk5t+v4OqvS3xnsCZax9iCtvP6sxXAdgZgSmAkSmCF2W4BHcDZDM0eN74iUYqpR6qYfqxGmHm4lSgxqOHAp1L8w/YMnDlZwuXXC+ZuYJ2XmxpyijuGR2TYw15T73cKbQ59CrC9AQ98oUzYWsIwqFFl+woZGAEG9WbHLI0vpWa3YKpHxNjahSmKbO5PDBpAkGhc+Z5IX5Qei+DBL2bwwOczmD9TxrkX87hxphSYEVLDEYztcS6gLWYbFr//1mUAs0EmjlWx73Mlvo9vUGKdyjaN4sCQW0BhEbS4TFHJGXh/90CQM525qmMDhKTHgcyUhqEdGkZ2s82gIohnSGDFcvfDSf5hewCc+XEWV35dbO115EXHPj8qtfkXL5d67TTpLQO0XGtsHj1Q553vV7FjHc72EFqd0bB2ldDcTUCv2Tq3tW6jTX61cyZay+s6La+BLM80qMgYA1MamTwcxfS9UUwdjXHomF8avyeOE381gYefreG9/13DzJsFwEWM7z6WxiPPjkrPXXk7j42gkLeKdR4y823f54rEKzzKtohbuRjB0jmNrl3RuEnGyxFGsRepTTSlY5+KvMoYI7tgbBB9+RW+pyC3CHY/Gseux+LITPjj4NFdMXz2ryfx4EdDeOu/VrBw1oreYXBzZvsf/8oEV/TsxAJIl3/Vex/AhiCC2KqgbcfLjp1DeB4dWL0cxe3TEbr6UcQVESQeq/ABagCHJV8bGgY1UMR2DWXcNXkohv2fTGLvE0m+mMRfgwBL16q4db6ESlFHZiKKXQ+l+KYPKnrjPxf5RlGy9hQZKQw8QM/MQEZM5HNksISKixoufi9JGfCzk4eRrRv0aYw5qglrurE4zfp6Ee5FZCuD2OfUt7PYdzyJo08PYHiHRxMSYGJfnH/80O1LJZz+4Qo2inpqBrLl4dF0O6XZovUiwblvpWg169Zl7t0ZxuJY0vb5W6rI9zhzWbNXK1Jc/EURF18uYtfDcTz4hUFMHfbXwW6Uu1PDC/9wwx0P0H0oYuOsgPSkfH+A2+/FUOOd70Y2Bc/uffO7Nb9bg1FXhLb9nPNyneL6u2X+2fFQAo99aQgT+ztjhJX5Kp77+zlkFz1cPyFbBj1kAIJoWpc2XG4+Iryo029pnT27y0AmkjCwedy6wrcJcOM3Ze4H2H88jUf/eBhDU/6aljHRuV9k8av/WERVsSvIFjUD2dp86Zu6uW4QOKAicAAL/7LFJqlxIDlqYPd5VDBl+PO5r8EMPjHoOVtHxx1GeYrSqhkFXDS+GzUHEMRgTnMtga+6mfViegJbGnblrQIO/s4A7v3dDF8pZA/0NGFjV9/Kc3zA0rXyRpj8GywBCDgCyDy00Mj+Olk+H/HNAyzsO7xXx9AeSgZ3UmTYq2WS9oKlIEHXcusVStjy79XZBpZnGrhzucbfFcRBpIxoZ+KJWTMXX8njwss5JIc0jO0xNpVm5h8DfbLt4VbmqsZO4eZ14cYY+4AB2AAq3ORD3dEPk8dquP1uDPmbcucA8xkM7aQYP9IgY4d1pKd6s09ANEEwuifCP/s/xSqdQmFJJzc/rGH+/SoWz1dR7yQaIzBEab2BGx80pGapNTIqzkhuSmAH7yXaTD/A/X+RI+np5gbSbWZgjp8rzyfo8vmI+aYP421hU8fqZPKBBn+f0GZTJa9j7t0qrr5R5tgAhtuXw86t/gTH62FsMHK/cHi3b/txHzIA/8/fF7T/88UWSNQuDdiOIeVVDfGMzlE//bqUfG2+jksvlzDzRomv6nFfJ8Cu8LeeoXnslmb5FgzXMBggdFi4HcdduqOxKCBh8X4ZA7BIHTvHET992vmM2Fy+8+EEDn8mxSOJq9fr7W3cHPX2sOOdh77JbS/l/pIAxg9+HB9q4OifFUiCIYZD6GSm0edvs0Wl7K0jQGmVbfIEynb7qhXM9wZxcc3DwWxfAMp3FcuApEaB9ATB4LSGoZ0akkPmjmIdTA9nX8jj7It5HregIU0B4rVbegqwv+YkOdbAvV8ukuRY8NtVsgSrMwSrV0DXZwkKdwz72TM24BIibjJochhkdF8Ek/dqmD4SNTaKCkCF5Qbe/U6Wm3+qutjrIP4W2+yu0gHai0LbkiCS0LH7s2UydazmifkrrxPcOaPhzjmNZuear4QLvi7Qma8dDGIkpPFfmSmN7Hwkhj1PsL0A2Ltv4E0UeO2flzHzRlE64nm8n7B9CnUlcwh1caTJvu3HfS8BxO/EaINvFDW839hJlO0Oxhw2lTUN67Ma7nyo0fVr7AVS3SwUdWUAI5Xy/5Z3BAnnyMieCA58OoF7PpHwjP4xjOALX1+0SBfG5E/++SgOf2aQ6z8zv87j9X+9YzBCp1ZAyEpgyH4AoUIu5ixbOzD3Wpxef9XYv4ftE8hGeOt9fwEwALJb+8gpYv6ps7bc2MbqbB2nvlnD+9/P4+BTKRx5OoXUsNp3Ya/MI88O475n2ps8Hn5qkG/++Mt/u6OutKedH240KGT3SnuUePZfk4vZq93rxmi38k8wbdHfvuSt0s3do2CPA7RmLZGqeYqzPyngR3+zjPe+m+cKoJ0YOFSsPaN7Hk878u3/RMbjQTyqHqITqMeu4A48VgJzB3WMqscFdQsDUltGezDIks5AmowRLr9WxAO/P4C9jyc5APXcz/K4/Lr5OjTBrWtuM2uh5kZRHdNWCgcHZRDLhtKBH1SVWVWQJc0iP2w4f0GsGelsfcA7/53FqW+zt3fIyjbyMYDotiPJ9vRAgdM/WFNvJ+v6HP5O90800ONt53LhQDtfgiVdcaRsMLfFv8QiiIS8/mtk5Jp9t4jnv34L9z8zCBIhuPBKFlffKvSuN/tLArg/HFf8HFnaTU97y4QyPAJpn3NgBdzuIqltO+3GByX+EZ1CgYvzfzow9WwvbtWLG9rkPC9eot6iw5ZRXZxPhyxsmEBhwNuLkj5TB3pO60pJG3jyXLj+8p4xgGsHWjO2SRQJLgzkt2yXxhRHN7XWhPa41cVpTnbWTZcJn3q4G79/2HTr0PpuNZdr/AJ1fDEKEe7I0KCBpGxgc9XyhixZBjf1pAMklQf1+nUMapIq5oJ3xgXt47cRTH5yb1FYJYBZtsgEHspM51NA2DZ9nzGAx8NJEVzEXyMHEy7UY9gSixRonyHWb/lNO3F1tH8E0Sm23BQQnGSaGSdfprKkn1Xi1ClCqO220tlZRmG9wrVVnu3bfn9y1+kAfoaTrSjjHfXe95P2v3xaIE03cHDARcDnFHUe2Wk3VbST+204A5Buhr1qxNp0AL+LRaVlOc5QIbsRtw3wFIFjVh46YIsB/TVFHzJAq0F8toyPbHazr3ux2+o2Yhf7VKnWE//vL3a5jnTYfK2pIWTFsc+mAEWyrSiZAyUQCd59WCUAd0DLaqT0PXjqugF9/QrTpWWShKx0aP2r+ak5wL98Vt2SyPQtKim99UPpxPXoEJkJ4k52V7i1mltICfRJtIdQWCVDWSJH1CoFaHCVIlSyW512d8SWmQJCJLsS2G15xsRNxJSWJaDQsohisneIeN+TvKJqTTmkyheyFth7BvDUkfw8kE0JdJQRtE6Gvof21aJtIEqEdr5ggkFNpLvm6n8rwE6eFaah+9u9y1Z49dC6mVMzaVfCtcLd9k9T0Dgj5b/VOoD7RWoVoXWhlxZJbCfcakV8B3u8s3sW367RXaoD+GseGeBCOEuCFuBoRGoLEXc+0Gzc6DssriCHX2jL6QAbQAGnCJWJjVBGl11hDam/mr4P0VdN7gYG8NdAHra2Epgpz26eI4qMMs+NQv76ieYF1lDll5kdLzI77c9YAAl99HrYAJ2OBSp8mxzhFiOQ3chYzOlaFels40ZWnbPtAkZPqIexAL/Z/VgB7jeQQgTbLeafOwivTgA9wLbzpax6jp7z5zlsv3DXeln/I4ICsmrnJh484qquZ41bW8kY6eZUC18kY0YPhvCg9oi3GiZN6yKU9uonCdBxC3mleRdAHdFAq37laXfJO8M+JXTWYa3KeISHt74S6KP/5fE51ySvhhedOlRRREcmYVgC2gl66Y0SsPmAkDCKlHKRKnhncQOLxJaqsG/f8VvZfGyXCp0qb05VQum96i8GUOLwVPlDeAqpIFbWQxlJoGbAx+7yVdfQxwzQAcbMLNo0+8wGkpXTl2bgpmx36HOlkItdRmSlts+Tjpm9U6WtbYx07JXeJAmwAVf4udyj/+3zO1X8di9LcsKJXupOArRDAEGY3D/9P9VO950W8JttAAAAAElFTkSuQmCC\"}, \"music-resized\": {\"asset_type\": \"image\", \"content_type\": \"image/png\", \"image\": \"data:image/png;base64,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\"}}}");

  /* ---- tiny DOM helpers + panel ---------------------------------------- */
  const el = (tag, css, txt) => { const n = document.createElement(tag); if (css) n.style.cssText = css; if (txt != null) n.textContent = txt; return n; };
  const panel = el("div", `position:fixed;top:20px;right:20px;width:370px;z-index:2147483647;
    background:#0b0e14;color:#e7e9f0;border:1px solid #1c2030;border-radius:12px;
    font:13px/1.5 ui-sans-serif,system-ui,sans-serif;box-shadow:0 12px 40px rgba(0,0,0,.5);overflow:hidden`);
  const head = el("div", `padding:12px 14px;background:#0f1420;border-bottom:1px solid #1c2030;font-weight:700;display:flex;align-items:center;gap:8px`);
  head.append(el("span", "color:#14c46c;font-size:16px", "♪"), el("span", null, "Lyrically · Express Setup"));
  const body = el("div", "padding:12px 14px;max-height:70vh;overflow:auto");
  panel.append(head, body); document.body.appendChild(panel);

  const btn = (txt, bg) => el("button", `margin:8px 6px 0 0;padding:8px 14px;border:0;border-radius:8px;cursor:pointer;
    font:600 12px/1 ui-sans-serif;background:${bg || "#14c46c"};color:#04140b`, txt);
  const label = (t) => el("div", "color:#8a90a4;font-size:11px;margin:10px 0 3px", t);
  const mkInput = (ph, type) => { const i = document.createElement("input"); i.type = type || "text"; i.placeholder = ph || "";
    i.style.cssText = "width:100%;box-sizing:border-box;background:#0f1420;border:1px solid #1c2030;border-radius:7px;padding:8px 9px;color:#e7e9f0;font:13px ui-monospace,monospace"; return i; };
  const link = (txt, href) => { const a = el("a", "color:#14c46c;text-decoration:none;font-weight:600", txt); a.href = href; a.target = "_blank"; a.rel = "noreferrer"; return a; };

  /* ---- 1) input form --------------------------------------------------- */
  const inputs = await new Promise((resolve) => {
    body.append(el("div", "color:#9aa0b4", "You only need your Spotify keys. Discord app, bot token and the widget are created for you."));
    body.append(label("App name (shown in the Developer Portal)"));
    const nameI = mkInput("Lyrically"); nameI.value = "Lyrically"; body.append(nameI);
    body.append(label("Spotify Client ID"));
    const idI = mkInput("from the Spotify dashboard"); body.append(idI);
    body.append(label("Spotify Client Secret"));
    const secI = mkInput("from the Spotify dashboard", "password"); body.append(secI);
    const hint = el("div", "margin-top:8px;color:#8a90a4;font-size:12px");
    hint.append("Get these at ", link("Spotify Developer Dashboard ↗", "https://developer.spotify.com/dashboard"),
      " — create an app and add redirect URI ");
    hint.append(el("code", "color:#e7e9f0", "http://127.0.0.1:8888/callback"), ". You can also leave these blank and fill config.json later.");
    body.append(hint);
    const go = btn("Start setup ▶");
    go.onclick = () => { go.disabled = true; body.innerHTML = "";
      resolve({ appName: (nameI.value || "Lyrically").trim(), spotifyId: idI.value.trim(), spotifySecret: secI.value.trim() }); };
    body.append(go);
  });

  /* ---- progress helpers ------------------------------------------------ */
  let row;
  const line = (txt) => { row = el("div", "display:flex;gap:8px;padding:3px 0;align-items:flex-start");
    row._i = el("span", "color:#8a90a4;flex:0 0 14px", "…"); row._t = el("span", "flex:1", txt); row.append(row._i, row._t);
    body.appendChild(row); body.scrollTop = body.scrollHeight; return row; };
  const ok = () => { if (row) row._i.textContent = "✓", row._i.style.color = "#14c46c"; };
  const warn = (m) => { if (row) row._i.textContent = "⚠", row._i.style.color = "#e0a96d"; if (m) { const w = line("   " + m); w.style.color = "#e0a96d"; } };
  const step = (t) => { ok(); line(t); };
  const fail = (e) => { if (row) row._i.textContent = "✗", row._i.style.color = "#e2554a";
    const b = el("div", "margin-top:8px;padding:8px;background:#2a1416;border:1px solid #e2554a;border-radius:8px;color:#ffb4ac");
    b.textContent = "Error: " + (e && e.message ? e.message : e) + " — reload the page and run it once more."; body.appendChild(b); };
  const copyBtn = (val) => { const b = btn("Copy", "#1c2030"); b.style.color = "#e7e9f0";
    b.onclick = () => { navigator.clipboard.writeText(val); b.textContent = "Copied"; setTimeout(() => b.textContent = "Copy", 1200); }; return b; };
  const field = (lab, val) => { const w = el("div", "margin:8px 0"); w.append(el("div", "color:#8a90a4;font-size:11px", lab));
    const r = el("div", "display:flex;gap:6px;align-items:center;margin-top:2px");
    r.append(el("code", "flex:1;background:#0f1420;border:1px solid #1c2030;border-radius:6px;padding:5px 7px;overflow:auto;white-space:nowrap", val), copyBtn(val));
    w.appendChild(r); return w; };

  /* ---- 2) automation --------------------------------------------------- */
  try {
    step("Hooking into the Developer Portal…");
    const wp = webpackChunkdiscord_developers.push([[Symbol()], {}, r => r]); webpackChunkdiscord_developers.pop();
    const findm = (fn) => Object.values(wp.c).find(fn);
    const ApexStore = findm(x => x?.exports?.A?.createOverride).exports.A;
    const UserStore = findm(x => x?.exports?.A?.__proto__?.getCurrentUser).exports.A;
    const FluxDispatcher = findm(x => x?.exports?.A?.__proto__?.flushWaitQueue).exports.A;
    const api = findm(x => x?.exports?.Bo?.get).exports.Bo;
    const userId = UserStore.getCurrentUser().id;
    ok();

    step(`Creating the application “${inputs.appName}” (solve captcha if prompted)…`);
    const appRes = await api.post({ url: "/applications", body: { name: inputs.appName, team_id: null } });
    FluxDispatcher.dispatch({ type: "APPLICATION_CREATE_SUCCESS", application: appRes.body });
    const appId = appRes.body.id;
    ok();

    step("Enabling the Social SDK…");
    await api.post({ url: `/applications/${appId}/social-sdk/enable`, body: {
      name: inputs.appName, business_email: "foo@bar.com", game_or_studio_name: inputs.appName, game_or_studio_url: "",
      email_updates_consent: false, country_or_region: "United States", title_role: "Founder",
      target_platforms: [], form_type: "Dev Solutions", sfdc_leadsource: "Dev Portal", utm_campaign: "SDK Enable Form" } });
    ok();

    step("Creating the widget…");
    const cfgRes = await api.post({ url: `/applications/${appId}/widget-configs`, body: { display_name: LYRICALLY_CONFIG.display_name || "Now Playing" } });
    const configId = cfgRes.body.config_id;
    ok();

    step("Uploading widget images…");
    try {
      for (const [name, a] of Object.entries(LYRICALLY_CONFIG.assets || {})) {
        const blob = await (await fetch(a.image)).blob();               // asset.image is a data: URL
        const ext = ((a.content_type || blob.type || "image/png").split("/")[1] || "png").replace("jpeg", "jpg");
        const slot = (await api.post({ url: `/applications/${appId}/assets/upload`, body: { filename: `${name}.${ext}`, file_size: blob.size } })).body;
        await fetch(slot.upload_url, { method: "PUT", body: blob });     // upload bytes to the storage slot
        await api.post({ url: `/applications/${appId}/assets`, body: { key: name, upload_filename: slot.upload_filename, visibility: "public" } });
      }
      ok();
    } catch (e) { warn("Some images didn't upload — you can add them in the editor. (" + e.message + ")"); }

    step("Importing Lyrically's widget layout…");
    try {
      await api.patch({ url: `/applications/${appId}/widget-configs/${configId}`,
        body: { display_name: LYRICALLY_CONFIG.display_name || "Now Playing", surfaces: LYRICALLY_CONFIG.surfaces } });
      ok();
    } catch (e) { warn("Layout import failed — shape it in the editor. (" + e.message + ")"); }

    step("Publishing the widget…");
    try { await api.post({ url: `/applications/${appId}/widget-configs/${configId}/publish` }); ok(); }
    catch (e) { warn("Publish needs a tweak in the editor. (" + e.message + ")"); }

    step("Authorizing + adding it to your profile…");
    await api.patch({ url: `/applications/${appId}`, body: { redirect_uris: ["https://discord.com"] } });
    await api.post({ url: `/oauth2/authorize?client_id=${appId}&response_type=token&scope=sdk.social_layer_presence`, body: { authorize: true } });
    const profile = await api.get({ url: `/users/${userId}/profile` });
    const widgets = profile.body.widgets || [];
    widgets.unshift({ data: { type: "application", application_id: appId } });
    await api.put({ url: `/users/@me/widgets`, body: { widgets } });
    ok();

    step("Resetting the bot token (enter 2FA if prompted)…");
    const tokRes = await api.post({ url: `/applications/${appId}/bot/reset` });
    const botToken = tokRes.body.token;
    ok();

    step("Opening the widget editor…");
    ApexStore.createOverride("2026-03-widget-config-editor", 1);
    try {
      document.querySelector(`a[href="/developers/applications/${appId}"]`)?.click();
      const sleep = ms => new Promise(r => setTimeout(r, ms));
      for (let i = 0; i < 50 && !document.querySelector(`a[href="/developers/applications/${appId}/widget"]`); i++) await sleep(100);
      document.querySelector(`a[href="/developers/applications/${appId}/widget"]`)?.click();
    } catch (_) {}
    ok();

    /* ---- 3) success card + config.json download ------------------------ */
    const config = {
      discord: { application_id: appId, user_id: userId, bot_token: botToken, image_webhook_url: "" },
      spotify: { client_id: inputs.spotifyId || "YOUR_SPOTIFY_CLIENT_ID", client_secret: inputs.spotifySecret || "YOUR_SPOTIFY_CLIENT_SECRET",
                 redirect_uri: "http://127.0.0.1:8888/callback", refresh_token: "" },
      options: { poll_interval_seconds: 3, tick_interval_seconds: 0.25, min_patch_interval_seconds: 0.5,
                 rate_limit_reserve: 1, log_rate_limits: true, heartbeat_seconds: 0,
                 username_format: "{track} — {artist}", no_lyrics_text: "♪", instrumental_text: "♪ Instrumental ♪", show_when_paused: true } };

    const card = el("div", "margin-top:12px;padding:10px;background:#08120c;border:1px solid #14c46c;border-radius:10px");
    card.append(el("div", "color:#14c46c;font-weight:700;margin-bottom:2px", "✓ Discord side done!"),
      field("Application ID", appId), field("Your User ID", userId), field("Bot token (keep secret)", botToken));
    const dl = btn("⬇ Download config.json");
    dl.onclick = () => { const a = el("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(config, null, 2)], { type: "application/json" })); a.download = "config.json"; a.click(); };
    card.append(dl);
    const next = el("div", "margin-top:10px;color:#9aa0b4;font-size:12px");
    next.append("Next: put config.json in your Lyrically folder, ");
    if (!inputs.spotifyId) next.append("fill in your Spotify keys, ");
    next.append("make sure your Spotify app has redirect URI ");
    next.append(el("code", "color:#e7e9f0", "http://127.0.0.1:8888/callback"), ", then run ");
    next.append(el("code", "color:#e7e9f0", "python get_spotify_token.py"), " and ");
    next.append(el("code", "color:#e7e9f0", "python widget.py"), ". The widget editor is open in this tab.");
    card.append(next); body.appendChild(card); body.scrollTop = body.scrollHeight;
    console.log("[Lyrically] Setup complete. App:", appId);
  } catch (err) { fail(err); console.error("[Lyrically] Setup failed:", err); }
})();
