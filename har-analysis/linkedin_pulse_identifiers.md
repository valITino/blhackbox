# LinkedIn Pulse HAR — identifiers & indicators

**Source page:** https://www.linkedin.com/pulse/how-structure-your-linkedin-content-more-views-graham-riley  
**Session:** logged-out guest (urn:li:member:0, isGuest=true)

> Session/CSRF/security tokens are MASKED. This file contains no full secret values.


## Author (who posted)

| field | value |
|---|---|
| public_handle | grahamkeithriley |
| profile_url | https://www.linkedin.com/in/grahamkeithriley |
| display_name | Graham Riley |
| profile_photo_asset | urn:li:digitalmediaAsset:D5603AQEx9gIpnH-iDQ |
| numeric_member_id | NOT EXPOSED (guest view; would require authenticated Voyager call) |

## Post / content identifiers

URNs with creation time decoded from the ID (`creation_ms = id >> 22`):

| urn | decoded creation (UTC) |
|---|---|
| urn:li:ugcPost:6922668744561360896 | 2022-04-20 22:14:05Z |
| urn:li:linkedInArticle:6922664509425807360 | 2022-04-20 21:57:15Z |
| urn:li:article:8483198953102629138 | (not time-decodable) |

## Media assets (each a `urn:li:digitalmediaAsset`)

| upload_date | type | source | asset_id |
|---|---|---|---|
| 2022-04-20 | article-inline_image | html_reference | C5612AQEILL7_4-dbIg |
| 2022-04-20 | article-inline_image | html_reference | C5612AQGWLLkHt0pIwg |
| 2022-04-20 | article-cover_image | network_request | C5612AQHS1flUGdsipA |
| 2022-04-20 | article-inline_image | network_request | C5612AQHZLo3YQmyRbQ |
| 2022-04-20 | article-inline_image | html_reference | C5612AQHtfJ0p8yhmUA |
| 2026-01-28 | article-cover_image | html_reference | D4E12AQEgMUQHrcP-Ww |
| 2023-01-28 | profile-displayphoto | network_request | D5603AQEx9gIpnH-iDQ |
| 2026-01-12 | article-cover_image | html_reference | D5612AQEDSeCuohyetQ |
| 2026-01-12 | article-cover_image | html_reference | D5612AQEGBBPGHoJQNQ |
| 2026-01-12 | article-cover_image | html_reference | D5612AQEa3rO2Sq935w |
| 2026-01-12 | series-logo_image | html_reference | D5612AQEa5urutCr8Jg |
| 2026-01-12 | article-cover_image | html_reference | D5612AQEmtbuGvP5OTg |
| 2026-01-12 | article-cover_image | html_reference | D5612AQF0ZVMw4TZMIg |
| 2026-02-17 | article-cover_image | html_reference | D5612AQFXkgClsVC1Dw |
| 2026-04-08 | article-cover_image | html_reference | D5612AQFjSaP6ry5vXA |
| 2026-01-14 | article-cover_image | html_reference | D5612AQGSs3zdfrnTWg |
| 2026-04-08 | article-cover_image | html_reference | D5612AQH_VBmr239bag |

## Viewer fingerprint cookies (values masked)

| cookie | purpose | value (masked) |
|---|---|---|
| JSESSIONID | Guest session / CSRF token (ajax: prefix) | ajax:2…[masked] (len 24) |
| PLAY_LANG | Play framework UI language | de (len 2) |
| PLAY_SESSION | Play framework session (JWT) | eyJhbG…[masked] (len 513) |
| __cf_bm | Cloudflare bot-management token | Ci.cSe…[masked] (len 199) |
| _px3 | PerimeterX security token (~60s lifetime) | 03e696…[masked] (len 651) |
| _pxvid | PerimeterX/HUMAN persistent visitor/device ID (up to ~1 year) | 24fdd724-68b… (len 36) |
| bcookie | Persistent browser UUID — LinkedIn's primary cross-session browser identifier | "v=2&3cc7b5d… (len 42) |
| bscookie | Signed secure browser cookie (embeds issue date) | "v=1&2…[masked] (len 88) |
| lang | UI language preference | v=2&lang=de-… (len 14) |
| li_alerts | Alerts state (base64) | e30= (len 4) |
| li_gc | Guest cookie-consent record | MTswOz…[masked] (len 72) |
| lidc | LinkedIn datacenter routing | "b=TGST03:s=… (len 108) |
| pxcts | PerimeterX client timestamp token | clscvm…[masked] (len 237) |
| sdui_ver | Server-driven-UI version | sdui-flagshi… (len 41) |
| timezone | Client timezone | Europe/Zuric… (len 13) |

## Geo / locale

| field | value |
|---|---|
| timezone_cookie | Europe/Zurich |
| lang_cookie | v=2&lang=de-DE |
| play_lang_cookie | de |
| html_meta_locale | de_DE |
| html_lang_attr | de |
| inference | Viewer in German-speaking Switzerland (Europe/Zurich + de locale) |

## Page & tracking

| field | value |
|---|---|
| page_key | d_flagship2_pulse_read |
| page_instance | urn:li:page:d_flagship2_pulse_read;hlXGC6YHRsiTZ3J/ZuHfvA== |
| member_urns | urn:li:member:0 |
| ingraphs_beacon | `{"pageKey":"d_flagship2_pulse_read_jsbeacon","metricsType":"seoPageView"}` |

## Anti-bot / anti-scraping

| field | value |
|---|---|
| vendor | HUMAN Security / PerimeterX (white-labeled as protechts.net) |
| app_id | PXdOjV695v |
| tenant | msft (Microsoft — LinkedIn parent) |
| use_case_flag | scraping |
| device_id_masked | 27833d71e767… |
| r_id_masked | AAZUgZz3kgis… |
| endpoints | client.protechts.net/PXdOjV695v/main.min.js, collector-pxdojv695v.protechts.net/api/v2/msft, collector-pxdojv695v.protechts.net/api/v2/msft/beacon, li.protechts.net/index.html, tzm.protechts.net/ns |

## Temporal intelligence

| field | value |
|---|---|
| post_created | 2022-04-20 (from ugcPost / linkedInArticle URN + image upload dates) |
| recommended_thumbnail_dates | 2026-01-12, 2026-01-12, 2026-01-12, 2026-01-12, 2026-01-12, 2026-01-14, 2026-01-28, 2026-02-17, 2026-04-08, 2026-04-08 |
| capture_dated_by_recommendations | Jan–Apr 2026 thumbnails imply capture ~mid-2026 |
