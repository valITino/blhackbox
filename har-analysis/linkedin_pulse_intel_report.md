# LinkedIn Pulse HAR — Full Intelligence Extraction

**Source page:** https://www.linkedin.com/pulse/how-structure-your-linkedin-content-more-views-graham-riley

> Session/CSRF/JWT/PerimeterX tokens are MASKED. Public identifiers and article text are included verbatim.

> **Research caveat:** Primary vendor docs (MS Learn URN namespace, HUMAN/PerimeterX, cookie DBs, the post-ID decoder) returned HTTP 403 to the fetcher; annotations are synthesized from search results cross-checked against the empirical HAR data + established knowledge.


## 0. Capture summary

| field | value |
|---|---|
| captured_local | 2026-06-18T08:52:01.172+02:00 |
| captured_utc | Thu, 18 Jun 2026 06:52:01 GMT |
| timezone_inference | Europe/Zurich (+02:00 CEST); corroborated by Cloudflare edge colo ZRH |
| browser | Mozilla Firefox (response header x-firefox-spdy: h2) |
| http_version | HTTP/2 |
| total_requests | 73 |
| total_response_bytes | 4805798 |
| page_timings_ms | {"onContentLoad": 673, "onLoad": 746} |

## 1. Shared content (full reconstruction)

### Article

| field | value |
|---|---|
| title | How to Structure your LinkedIn Content for more Views |
| read time (min) | 7 |
| body word count | 1524 |
| accessible for free | True |

### Author

| field | value |
|---|---|
| name | Graham Riley |
| handle | grahamkeithriley |
| profile_url | https://www.linkedin.com/in/grahamkeithriley |
| numeric_member_id | 146172655 |
| affiliation_byline | Maverrik - North America |
| followers | 34996 |
| profile_photo_url | https://media.licdn.com/dms/image/v2/D5603AQEx9gIpnH-iDQ/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1674949661120?e=2147483647&v=beta&t=zFp2UMwFh6xj-v5e30E3jIMJQ-4vg-3NOM5r8K7Lu6E |

### Dates

| field | value |
|---|---|
| published | 2022-04-20T22:14:06.000+00:00 |
| modified | 2026-04-10T16:53:39.000+00:00 |

### Engagement

| metric | value |
|---|---|
| reactions | 62 |
| comments | 0 |
| views | not exposed to guests |

_JSON-LD is authoritative: 62 reactions, 0 comments. With commentCount=0 there are no comment bodies to reconstruct._


### Newsletter

| field | value |
|---|---|
| name | LinkedIn Success |
| slug | linkedin-success |
| urn_id | 6905523102084685824 |
| url | https://www.linkedin.com/newsletters/linkedin-success-6905523102084685824 |
| subscribers | 3758 |
| logo_url | https://media.licdn.com/dms/image/v2/D5612AQEa5urutCr8Jg/series-logo_image-shrink_100_100/B56ZuztV8tIYAc-/0/1768246567336?e=2147483647&v=beta&t=Y3YPlJUBlPpUXYbSQ8KN-xLIsWPzcu_TAU_wNzP_HBE |


### Related articles (more from this author)

| title | date (de) | date (iso) |
|---|---|---|
| Why LinkedIn Live Builds Trust Faster Than Content Alone | 21. Apr. 2026 | 2026-04-21 |
| Why Most LinkedIn Strategies Stall Before They Start | 8. Apr. 2026 | 2026-04-08 |
| LinkedIn Webinars Are Not an Event Strategy. They Are a Coherence Test. | 17. Feb. 2026 | 2026-02-17 |
| LinkedIn Isn’t Rewarding More Activity. It’s Rewarding System Coherence. | 28. Jan. 2026 | 2026-01-28 |
| Boosting Your Visibility With 360Brew | 14. Jan. 2026 | 2026-01-14 |
| Why Your Company Page Isn’t Driving Sales Pipeline | 17. Sept. 2025 | 2025-09-17 |
| Why Your LinkedIn Posts Fall Flat (And How to Fix It) | 3. Sept. 2025 | 2025-09-03 |
| Why Social Selling Breaks (and How to Fix It) | 21. Juli 2025 | 2025-07-21 |
| Not All Content Is Created Equal | 7. Juli 2025 | 2025-07-07 |
| Why LinkedIn Needs a Real Owner Inside Your Sales Org | 16. Juni 2025 | 2025-06-16 |

### Full body text (verbatim)

> Are you one of those people who is fed up with creating content that nobody seems to look at? Have you had the experience of feeling like you've almost crafted the world's best-ever post but then it struggles to get more than a handful of reactions or comments, with just a few hundred Views? Yet you see others on the platform getting huge amounts of views and interactions on their content. It's a very common frustration and something that comes up time and time again when I'm training and coaching our clients. And almost every time I look at the client's content, I find that they're making the same common errors. LinkedIn is my favorite platform, so I will use this platform for this example. On LinkedIn alone. In the last 12 months, the amount of people who are posting content is grown by 30%. That's a million more people. So, I want to make sure that my content stands out, I want to make sure that the structure of the post is working for me so people see my content, find me, and engage with me… or else, why bother posting content. There is a best practice to the way you structure your social media content. Think: When you look at a post, what is it that catches the eye? Remember, your post is going to sit in somebody's feed; there's a poster above you and a post below you. You're competing for the viewer's attention. There are some key things you need to think about that will catch the eye first? First, it’s the Picture It's the media asset that you use. Whether that is a PDF, a video clip, a static image, or whatever it may be. What is going to capture the eye’s attention? Question: When you look at your feed what catches your eye first? Which posts stand out to you? Learn from what you see other people doing. There are some no-no’s when it comes to the media assets you use. Images with black or dark backgrounds tend to underperform. The same goes for small text on an image. Think about using bright colors such as oranges, greens, yellows, etc as these will help your post stand off the page and catch the attention of a viewer. TIP: Make your images are square to take up the maximum area in the post feed. Now think about the colors that you're going to use, the branding that you're going to use, the imagery that you're going to use, will it capture the eye’s attention. If you are using a PDF slide deck, make sure the first front page that sits immediately visible on your post draws in the viewer. Another common mistake is image text being too small. Often the imagery is created on a large screen desktop where the text is easy to see and read. Remember it's going to be seen on a mobile device. So, optimize your content for viewing on mobile devices. Another common mistake is making the imagery text-heavy. Nobody wants to be reading War & Peace on your social media posts. Stick to the headline statements and use the body of the post to fill out the detail. So the first three things that people engage with on a post are most commonly… The image The image title The opening line of the post The opening line of your post can be the deal-breaker when it comes to getting engagement. I see this all the time on LinkedIn, where that first two or three lines are just solid text, like the start of a new paragraph. On social media, this will put people off engaging with your content. Why? Simply attention spans on social media are short and people make micro-second judgments as to whether they will or will not engage. Large paragraphs of text require the reader to focus and track the lines of text to read the narrative and this results in most readers seeing it and mentally deciding ‘I do not have the time to read all of that.’ TIP: Create single line headlines that draw attention. Then leave one or two line spaces before the next line of text. A few years ago, a colleague of mine wrote a post on this subject and started his post with the headline "Why I killed my mother-in-law". Did he get attention? Absolutely!. Why? Because he played on human curiosity… we all want to know the story behind the headline. So, people click in, and now they're reading his content. The rest of the constant talks about why it's important to have a headline statement, something that creates curiosity for people to click to see more, go into and read the rest of your post. The headline could be a statement that leaves the reader wanting to know more such as "Five ways of winning new business". What are those five ways? The reader has to click on the post and read the rest to find out. It could be a question. If they want to know the answer, they have to read the rest of the post. TIP: Make sure your start a mental conversation Another common mistake is the content does not start a conversation. What you want to do is draw the reader into the content with a mental conversation. You ask questions such as ‘When was the last time you had this experience?’ or ‘How does the problem affect your business?’. If you are writing a bunch of statements, telling everyone how fantastic your company is and how wonderful your products are… then you will be ignored because you have no value to the individual. So let's start the conversation. Let's talk about the common issues that your clients might deal with on a daily, weekly or monthly basis. The sort of things that you know, you can solve. When you start to talk about those issues you start to create a conversation. Add in some questions to promote the mental conversation… Do you have this issue? … (reader thinks) Yes, I do. Is this issue causing you problems X, Y, and Z? … (reader thinks) Oh, yes, absolutely. Does the result of this issue affect not only your business life but your family life too? … (reader thinks) Yes..., this person understands my issue! Now, you've got them engaged in the conversation. The reader is responding yes, yes, yes that's me which promotes a favorable response towards any CTAs. And what they're mentally doing is making an assessment that actually this person understands my situation and the inference of that is that if you're talking about what the problem is, you must already have an answer. So they stay engaged with the post. And now you present to them what the solution could look like and what life could be like with that problem removed with your solution put in place. Your imagery and your text started a conversation around a topic that interests them and engages them enough to invest in the post content. Then as we get to the bottom, here's the real kicker. TIP: Give people a way to interact beyond the post content. What are your calls to action (CTA)? What are you actually asking people to do? A lot of social media content that I see is just a statement telling me how good something is or telling me a bunch of statistics that are supposed to convince me to buy. This type of content is easily ignored and quickly forgotten. So, what are you asking readers to do? What's the engagement you want them? On social media, you will learn that you have to give clear instructions for what you want the reader to do. Examples… "Click here to access the free download" or "Send me a DM for more information" or "Click here to arrange a phone call" Some people will be thinking that's me, I need that solution. It's worth the conversation and they'll want to get in touch. Do not make it a suggestion, give clear direct instruction. Nearly three years ago I learned a valuable lesson. I would quite often in my very English manner say, ‘Hey, if you are interested, click here to find more information. Well, by actually putting it like that I put a negative spin on it… if you are interested. I created a question with the word ‘if’. In the world of social media that invariably promotes the response ‘No, I am not interested.’ So I started writing ‘Click here for more information.’ and, guess what happened. The click rate doubled because I gave clear instructions, and people complied. So, put it all together: Use imagery that attracts attention Optimize content for mobile viewing Write headlines that create curiosity Start a mental conversation Give clear instructions for CTAs Do this consistently and you will find that those views on your content will start to increase and you can say goodbye to underperforming content. Schedule a Discovery Call with me to discuss how to maximize your content strategy. 📅 https://lnkd.in/gp4JWdKK #sales #salesenablement #marketing


## 2. Structured data

### JSON-LD (schema.org)

```json
{
  "@context": "http://schema.org",
  "@type": "Article",
  "headline": "Are you one of those people who is fed up with creating content that nobody seems to look at? Have you had the experience of feeling like you've almost crafted the world's best-ever post but then it struggles to get more than a handful of reactions or comments, with just a few hundred Views? Yet you",
  "url": "https://www.linkedin.com/pulse/how-structure-your-linkedin-content-more-views-graham-riley",
  "publisher": null,
  "name": "How to Structure your LinkedIn Content for more Views",
  "commentCount": 0,
  "interactionStatistic": [
    {
      "@type": "InteractionCounter",
      "interactionType": "http://schema.org/LikeAction",
      "userInteractionCount": 62
    },
    {
      "@type": "InteractionCounter",
      "interactionType": "http://schema.org/CommentAction",
      "userInteractionCount": 0
    }
  ],
  "datePublished": "2022-04-20T22:14:06.000+00:00",
  "mainEntityOfPage": "https://www.linkedin.com/pulse/how-structure-your-linkedin-content-more-views-graham-riley",
  "isAccessibleForFree": true,
  "image": {
    "@type": "ImageObject",
    "url": "https://media.licdn.com/dms/image/v2/C5612AQHS1flUGdsipA/article-cover_image-shrink_720_1280/article-cover_image-shrink_720_1280/0/1650491835717?e=2147483647&v=beta&t=yZEnOmgmJmplxtWg_Cy656d7sJjQalfOldcZTs-yh5o"
  },
  "dateModified": "2026-04-10T16:53:39.000+00:00",
  "author": {
    "@type": "Person",
    "image": "https://media.licdn.com/dms/image/v2/D5603AQEx9gIpnH-iDQ/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1674949661120?e=2147483647&v=beta&t=zFp2UMwFh6xj-v5e30E3jIMJQ-4vg-3NOM5r8K7Lu6E",
    "interactionStatistic": {
      "@type": "InteractionCounter",
      "interactionType": "https://schema.org/FollowAction",
      "name": "Followers",
      "userInteractionCount": 34996
    },
    "name": "Graham Riley",
    "url": "https://www.linkedin.com/in/grahamkeithriley"
  }
}
```

### Meta tags

| property/name | content |
|---|---|
| pageKey | d_flagship2_pulse_read |
| robots | max-image-preview:large, noarchive |
| bingbot | max-image-preview:large, archive |
| locale | de_DE |
| article-ssr-frontend |  |
| al:android:url | https://www.linkedin.com/pulse/how-structure-your-linkedin-content-more-views-graham-riley |
| al:android:package | com.linkedin.android |
| al:android:app_name | LinkedIn |
| al:ios:url | https://www.linkedin.com/pulse/how-structure-your-linkedin-content-more-views-graham-riley |
| al:ios:app_store_id | 288429040 |
| al:ios:app_name | LinkedIn |
| description | Are you one of those people who is fed up with creating content that nobody seems to look at? Have you had the experience of feeling like you've almost crafted the world's best-ever post but then it struggles to get more than a handful of reactions or comments, with just a few hundred Views? Yet you |
| og:title | How to Structure your LinkedIn Content for more Views |
| og:description | Are you one of those people who is fed up with creating content that nobody seems to look at? Have you had the experience of feeling like you've almost crafted the world's best-ever post but then it struggles to get more than a handful of reactions or comments, with just a few hundred Views? Yet you |
| og:image | https://media.licdn.com/dms/image/v2/C5612AQHS1flUGdsipA/article-cover_image-shrink_720_1280/article-cover_image-shrink_720_1280/0/1650491835717?e=2147483647&v=beta&t=yZEnOmgmJmplxtWg_Cy656d7sJjQalfOldcZTs-yh5o |
| og:type | article |
| og:url | https://www.linkedin.com/pulse/how-structure-your-linkedin-content-more-views-graham-riley |
| twitter:card | summary_large_image |
| twitter:site | @LinkedInEditors |
| twitter:title | How to Structure your LinkedIn Content for more Views |
| twitter:description | Are you one of those people who is fed up with creating content that nobody seems to look at? Have you had the experience of feeling like you've almost crafted the world's best-ever post but then it struggles to get more than a handful of reactions or comments, with just a few hundred Views? Yet you |
| twitter:image | https://media.licdn.com/dms/image/v2/C5612AQHS1flUGdsipA/article-cover_image-shrink_720_1280/article-cover_image-shrink_720_1280/0/1650491835717?e=2147483647&v=beta&t=yZEnOmgmJmplxtWg_Cy656d7sJjQalfOldcZTs-yh5o |
| appId |  |
| twitter:label1 | Von |
| twitter:data1 | Graham Riley |
| twitter:label2 | Lesedauer |
| twitter:data2 | Lesedauer: 7 Min. |
| clientSideIngraphs | 1 |

### Embedded `<code>` config blocks

| code id | value |
|---|---|
| articleUrn | urn:li:linkedInArticle:6922664509425807360 |
| legacyArticleUrn | urn:li:article:8483198953102629138 |
| ugcPostUrn | urn:li:ugcPost:6922668744561360896 |
| ugcPostUrl | https://www.linkedin.com/feed/update/urn:li:ugcPost:6922668744561360896 |
| memberUrn (viewer) | urn:li:member:0 |
| isGuest | True |
| signInUrl | https://www.linkedin.com/signup/cold-join?session_redirect=%2Fpulse%2Fhow-structure-your-linkedin-content-more-views-graham-riley |

## 3. Identifiers

| urn | decoded creation (UTC) |
|---|---|
| urn:li:ugcPost:6922668744561360896 | 2022-04-20 22:14:05Z |
| urn:li:linkedInArticle:6922664509425807360 | 2022-04-20 21:57:15Z |
| urn:li:article:8483198953102629138 | (not time-decodable) |

- **Author numeric member id:** `146172655` (from `articleViewEventData.authorId`)
- **Viewer member urn:** `urn:li:member:0` (guest)


## 4. Infrastructure & headers

**CDN path:** Cloudflare edge (a0d85e6b6e5dbb16-ZRH) → LinkedIn fabric prod-ltx1 (PoP cf-prod-ltx1-x)


### HTML document response headers

| header | value |
|---|---|
| date | Thu, 18 Jun 2026 06:52:01 GMT |
| content-type | text/html; charset=utf-8 |
| content-length | 24955 |
| vary | Accept-Encoding |
| server | cloudflare |
| x-fs-uuid | 000654819cf79208ac0183a388d23a77 |
| strict-transport-security | max-age=31536000 |
| x-content-type-options | nosniff |
| x-frame-options | sameorigin |
| content-security-policy | default-src 'none'; connect-src 'self' *.licdn.com *.linkedin.com cdn.linkedin.oribi.io dpm.demdex.net/id lnkd.demdex.net blob: accounts.goo… |
| x-li-fabric | prod-ltx1 |
| pragma | no-cache |
| expires | Thu, 01 Jan 1970 00:00:00 GMT |
| cache-control | no-cache, no-store, no-transform |
| x-li-pop | cf-prod-ltx1-x |
| x-li-proto | http/2 |
| x-li-uuid | AAZUgZz3kgisAYOjiNI6dw== |
| cf-cache-status | DYNAMIC |
| cf-ray | a0d85e6b6e5dbb16-ZRH |
| alt-svc | h3=":443"; ma=86400 |
| content-encoding | gzip |
| x-firefox-spdy | h2 |

### Hosts contacted

| host | requests |
|---|---|
| static.licdn.com | 35 |
| www.linkedin.com | 19 |
| accounts.google.com | 5 |
| collector-pxdojv695v.protechts.net | 4 |
| media.licdn.com | 3 |
| play.google.com | 3 |
| client.protechts.net | 2 |
| li.protechts.net | 1 |
| tzm.protechts.net | 1 |

### Largest responses

| bytes | host | subtype |
|---|---|---|
| 1474688 | media.licdn.com | article-cover_image |
| 737056 | static.licdn.com | js |
| 580208 | static.licdn.com | js |
| 322855 | static.licdn.com | js |
| 264639 | accounts.google.com | google_gsi |

## 5. Tracking & telemetry

| channel | meaning |
|---|---|
| li/track | LinkedIn first-party client tracking beacon; no request body captured in this HAR (empty beacon). |
| ingraphs | Server-side SEO/page-view counters (clientSideIngraphs=1 meta). |
| PerimeterX/HUMAN | HUMAN/PerimeterX sensor + token endpoints; payload is encrypted/opaque. |
| Google GSI | 5 req — Google Identity Services One-Tap widget (sign-in offer to guests). |
| Play log | 3 req — Google Play logging tied to the GSI widget. |
| CSP analytics partners | accounts.google.com/gsi/, ad.doubleclick.net, adservice.google.com, cdn.linkedin.oribi.io, dpm.demdex.net/id, google.com, googleads.g.doubleclick.net, lnkd.demdex.net, pagead2.googlesyndication.com, td.doubleclick.net, www.google.com, www.googleadservices.com, www.googletagmanager.com |

## 6. Derived intelligence

| field | value |
|---|---|
| geolocation | German-speaking Switzerland / Zurich — de_DE locale + Europe/Zurich timezone cookie, independently corroborated by Cloudflare edge colo ZRH (Zurich airport code). |
| capture_dating | Exact: Thu, 18 Jun 2026 06:52:01 GMT (UTC). Article last modified 2026-04-10T16:53:39.000+00:00; recommended-article thumbnails (Jan–Apr 2026) are consistent. |
| session_state | Logged-out guest (urn:li:member:0, isGuest=true) — a sign-in/cold-join wall is present. |
| anti_scraping | HUMAN/PerimeterX active (uc='scraping', tenant msft); persistent device id set. |
| browser | Mozilla Firefox (x-firefox-spdy header). |
