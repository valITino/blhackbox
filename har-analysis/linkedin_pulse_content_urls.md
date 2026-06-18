# LinkedIn Pulse HAR — content-construction URLs

**Source page:** https://www.linkedin.com/pulse/how-structure-your-linkedin-content-more-views-graham-riley

Scope: the post HTML document + **all `*.licdn.com`** assets (media + static), plus images referenced in the HTML but not separately fetched. Telemetry, anti-bot, and Google/Play are excluded.


## The post (server-rendered document)

| method | status | mime | url |
|---|---|---|---|
| GET | 200 | text/html; charset=utf-8 | `https://www.linkedin.com/pulse/how-structure-your-linkedin-content-more-views-graham-riley` |

_Comments: embedded in this HTML (`commentCount`, `CommentAction`); no separate comment fetch occurred._


## Pictures — fetched from the media CDN

| subtype | status | bytes | url |
|---|---|---|---|
| article-cover_image | 200 | 1474688 | `https://media.licdn.com/dms/image/v2/C5612AQHS1flUGdsipA/article-cover_image-shrink_720_1280/article-cover_image-shrink_720_1280/0/1650491835717?e=2147483647&v=beta&t=yZEnOmgmJmplxtWg_Cy656d7sJjQalfOldcZTs-yh5o` |
| profile-displayphoto | 200 | 24704 | `https://media.licdn.com/dms/image/v2/D5603AQEx9gIpnH-iDQ/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1674949661120?e=2147483647&v=beta&t=zFp2UMwFh6xj-v5e30E3jIMJQ-4vg-3NOM5r8K7Lu6E` |
| article-inline_image | 200 | 32896 | `https://media.licdn.com/dms/image/v2/C5612AQHZLo3YQmyRbQ/article-inline_image-shrink_400_744/article-inline_image-shrink_400_744/0/1650491884370?e=2147483647&v=beta&t=TP20fIYGGsLrpVhOKU8xGdwa99vIRCwKce4qLKfh6wU` |

## Pictures — referenced in the HTML (not separately fetched)

| subtype | upload_date | asset_id | url |
|---|---|---|---|
| article-inline_image | 2022-04-20 | C5612AQEILL7_4-dbIg | `https://media.licdn.com/dms/image/v2/C5612AQEILL7_4-dbIg/article-inline_image-shrink_1500_2232/article-inline_image-shrink_1500_2232/0/1650492455321?e=2147483647&v=beta&t=YHzcWPJm-sykVJRi_A5p78xjlN8CCeVZas-l9uOVspM` |
| article-inline_image | 2022-04-20 | C5612AQGWLLkHt0pIwg | `https://media.licdn.com/dms/image/v2/C5612AQGWLLkHt0pIwg/article-inline_image-shrink_1000_1488/article-inline_image-shrink_1000_1488/0/1650492247072?e=2147483647&v=beta&t=iHbI2ywguRXgiQAuT8CtJsPHBUrRcoLVoPhKqUv-XzI` |
| article-inline_image | 2022-04-20 | C5612AQHtfJ0p8yhmUA | `https://media.licdn.com/dms/image/v2/C5612AQHtfJ0p8yhmUA/article-inline_image-shrink_1000_1488/article-inline_image-shrink_1000_1488/0/1650492744928?e=2147483647&v=beta&t=gP32sJyag0pD1OJoe1UCp2JtUteCRl1Qgsmcrms1b08` |
| article-cover_image | 2026-01-28 | D4E12AQEgMUQHrcP-Ww | `https://media.licdn.com/dms/image/v2/D4E12AQEgMUQHrcP-Ww/article-cover_image-shrink_720_1280/B4EZwFOeM1JgAQ-/0/1769614206740?e=2147483647&v=beta&t=AReViLGnRRlyzLTcyIJkxDipdM15j0XqClyCkC0-1i4` |
| article-cover_image | 2026-01-12 | D5612AQEDSeCuohyetQ | `https://media.licdn.com/dms/image/v2/D5612AQEDSeCuohyetQ/article-cover_image-shrink_720_1280/B56ZuzsihLHcAI-/0/1768246357132?e=2147483647&v=beta&t=7aoGa4kSr0AYuL9M22z3hDNB_s5jXcM1BQ8gPgKJnYE` |
| article-cover_image | 2026-01-12 | D5612AQEGBBPGHoJQNQ | `https://media.licdn.com/dms/image/v2/D5612AQEGBBPGHoJQNQ/article-cover_image-shrink_720_1280/B56ZuzuQYlGwAM-/0/1768246807100?e=2147483647&v=beta&t=VNPcS0uyqGXx_q1GFXQ7zeqvJ1QFajx-he8i4czXF_k` |
| article-cover_image | 2026-01-12 | D5612AQEa3rO2Sq935w | `https://media.licdn.com/dms/image/v2/D5612AQEa3rO2Sq935w/article-cover_image-shrink_720_1280/B56ZuztimdHgAI-/0/1768246619389?e=2147483647&v=beta&t=YGWJ4u6vijjRlsZaEaQi9olephGNQQK2lPhuAfZB2pU` |
| series-logo_image | 2026-01-12 | D5612AQEa5urutCr8Jg | `https://media.licdn.com/dms/image/v2/D5612AQEa5urutCr8Jg/series-logo_image-shrink_100_100/B56ZuztV8tIYAc-/0/1768246567336?e=2147483647&v=beta&t=Y3YPlJUBlPpUXYbSQ8KN-xLIsWPzcu_TAU_wNzP_HBE` |
| article-cover_image | 2026-01-12 | D5612AQEmtbuGvP5OTg | `https://media.licdn.com/dms/image/v2/D5612AQEmtbuGvP5OTg/article-cover_image-shrink_720_1280/B56ZuzsF5qIoAI-/0/1768246239808?e=2147483647&v=beta&t=IuoEOvNl5eohnK0M6POP6fesIAGL40_KvRQMLv3WhFU` |
| article-cover_image | 2026-01-12 | D5612AQF0ZVMw4TZMIg | `https://media.licdn.com/dms/image/v2/D5612AQF0ZVMw4TZMIg/article-cover_image-shrink_720_1280/B56ZuzukDMG4AM-/0/1768246887576?e=2147483647&v=beta&t=jc3YLG5MwtX8M68oSGhYow3ux8Hlt09VhEf9mdXgOYk` |
| article-cover_image | 2026-02-17 | D5612AQFXkgClsVC1Dw | `https://media.licdn.com/dms/image/v2/D5612AQFXkgClsVC1Dw/article-cover_image-shrink_720_1280/B56ZxrxiAQIIAM-/0/1771334673324?e=2147483647&v=beta&t=cVKdhvCQ8feIJV84N3zOeCf9zaP8UECzG4ZYV0goRHg` |
| article-cover_image | 2026-04-08 | D5612AQFjSaP6ry5vXA | `https://media.licdn.com/dms/image/v2/D5612AQFjSaP6ry5vXA/article-cover_image-shrink_720_1280/B56Z1usodSGgAI-/0/1775678688612?e=2147483647&v=beta&t=Ww1tsOz2d_Y_JIZajYJ8QjM4BaPC9IP-Yvfm8dTKi-I` |
| article-cover_image | 2026-01-14 | D5612AQGSs3zdfrnTWg | `https://media.licdn.com/dms/image/v2/D5612AQGSs3zdfrnTWg/article-cover_image-shrink_720_1280/B56Zu80Jw1H4AI-/0/1768399347600?e=2147483647&v=beta&t=VedtlwVg3PSsek8QV4W-THe4jnIBag-X23ZNssB_0Vo` |
| article-cover_image | 2026-04-08 | D5612AQH_VBmr239bag | `https://media.licdn.com/dms/image/v2/D5612AQH_VBmr239bag/article-cover_image-shrink_720_1280/B56Z1usIKaLIAI-/0/1775678556371?e=2147483647&v=beta&t=ye4g-n7Q0nyDhhxzUw7G8kpywRyBD9F-OAgiBKcMd4E` |

## Static app assets (static.licdn.com)

| subtype | status | bytes | url |
|---|---|---|---|
| css | 200 | 62035 | `https://static.licdn.com/aero-v1/sc/h/dz0j0kmvbejzicgfmsjd8eudd` |
| js | 200 | 322855 | `https://static.licdn.com/aero-v1/sc/h/4w1iremrnsuxf3bjq4udk3vti` |
| js | 200 | 580208 | `https://static.licdn.com/aero-v1/sc/h/5uuxwnwdmq2n9de6so4ojuvzv` |
| favicon | 200 | 24838 | `https://static.licdn.com/aero-v1/sc/h/al2o9zrvru7aqj8e1x2rzsrca` |
| svg_icon | 200 | 89312 | `https://static.licdn.com/aero-v1/sc/h/5k9cgtx8rhoyqkcxfoncu1svl` |
| svg_icon | 200 | 52576 | `https://static.licdn.com/aero-v1/sc/h/9c8pery4andzj6ohjkjp54ma2` |
| svg_icon | 200 | 2435 | `https://static.licdn.com/aero-v1/sc/h/ddi43qwelxeqjxdd45pe3fvs1` |
| js | 200 | 224639 | `https://static.licdn.com/aero-v1/sc/h/29rdkxlvag0d3cpj96fiilbju` |
| svg_icon | 200 | 56768 | `https://static.licdn.com/aero-v1/sc/h/asiqslyf4ooq7ggllg4fyo4o2` |
| svg_icon | 200 | 62688 | `https://static.licdn.com/aero-v1/sc/h/a0e8rff6djeoq8iympcysuqfu` |
| svg_icon | 200 | 274 | `https://static.licdn.com/aero-v1/sc/h/gs508lg3t2o81tq7pmcgn6m2` |
| svg_icon | 200 | 288 | `https://static.licdn.com/aero-v1/sc/h/9w7euj0n5gnk6np2akf853sm3` |
| svg_icon | 200 | 571 | `https://static.licdn.com/aero-v1/sc/h/4zqr0f9jf98vi2nkijyc3bex2` |
| svg_icon | 200 | 2958 | `https://static.licdn.com/aero-v1/sc/h/8fkga714vy9b2wk5auqo5reeb` |
| svg_icon | 200 | 563 | `https://static.licdn.com/aero-v1/sc/h/5ofmdgombsj3cqmfn03qb7h60` |
| svg_icon | 200 | 351 | `https://static.licdn.com/aero-v1/sc/h/7kb6sn3tm4cx918cx9a5jlb0` |
| svg_icon | 200 | 737 | `https://static.licdn.com/aero-v1/sc/h/8wykgzgbqy0t3fnkgborvz54u` |
| svg_icon | 200 | 335 | `https://static.licdn.com/aero-v1/sc/h/92eb1xekc34eklevj0io6x4ki` |
| svg_icon | 200 | 1503 | `https://static.licdn.com/aero-v1/sc/h/29h8hsjuomfp50lam5ipnc3uh` |
| svg_icon | 200 | 340 | `https://static.licdn.com/aero-v1/sc/h/admayac2rnonsqhz9v3rzwcyu` |
| svg_icon | 200 | 177 | `https://static.licdn.com/aero-v1/sc/h/671xosfpvk4c0kqtyl87hashi` |
| svg_icon | 200 | 260 | `https://static.licdn.com/aero-v1/sc/h/iq0x9q37wj214o129ai1yjut` |
| svg_icon | 200 | 796 | `https://static.licdn.com/aero-v1/sc/h/3djuegvxjnk75fm1bl5ugf342` |
| svg_icon | 200 | 411 | `https://static.licdn.com/aero-v1/sc/h/1p9aa0o2ms48w7ipecq9amsti` |
| svg_icon | 200 | 1291 | `https://static.licdn.com/aero-v1/sc/h/aup4g97pdky3ff73gv9lyhjvx` |
| svg_icon | 200 | 533 | `https://static.licdn.com/aero-v1/sc/h/2uoxvguhsfspfnmr6tvfuyw4y` |
| svg_icon | 200 | 556 | `https://static.licdn.com/aero-v1/sc/h/5xkjpykqkamtr6skk0vodqwd2` |
| svg_icon | 200 | 336 | `https://static.licdn.com/aero-v1/sc/h/2pdd1nk5ocycpv963y85l3bt4` |
| svg_icon | 200 | 228 | `https://static.licdn.com/aero-v1/sc/h/l7s88viq07vqke49pnrbl5e4` |
| svg_icon | 304 | 1354 | `https://static.licdn.com/aero-v1/sc/h/bn39hirwzjqj18ej1fkz55671` |
| svg_icon | 200 | 237 | `https://static.licdn.com/aero-v1/sc/h/c4cba545dp8erex8bfiynf35e` |
| svg_icon | 200 | 201 | `https://static.licdn.com/aero-v1/sc/h/cyolgscd0imw2ldqppkrb84vo` |
| svg_icon | 200 | 201 | `https://static.licdn.com/aero-v1/sc/h/4chtt12k98xwnba1nimld2oyg` |
| js | 200 | 737056 | `https://static.licdn.com/aero-v1/sc/h/985sqoiudwdfnuemt74raqc27` |
| svg_icon | 200 | 0 | `https://static.licdn.com/aero-v1/sc/h/bn39hirwzjqj18ej1fkz55671` |
