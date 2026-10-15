# Phase 22 — Public Cybersecurity News

Public page: `/news` (no login). API: `GET /api/v1/news`, `/news/categories`, `/news/sources`.

## How it works
1. **Request path** reads only the MongoDB cache (`news_articles`). It never waits on an external site.
2. If any source's cooldown has passed, the request schedules a **background refresh** (stale-while-revalidate).
   A MongoDB lease (`news_source_state/__refresh__`, 150 s) prevents concurrent refreshes across workers; failing
   sources back off 60 s, 120 s, … up to the refresh interval. Traffic alone cannot drive outbound requests.
3. A one-off warm-up refresh also runs at startup (non-blocking).
4. Each source is fetched, parsed, normalised and upserted independently; one failure never affects the others.
5. Articles expire via a MongoDB TTL index on `expires_at` (retention `NEWS_RETENTION_DAYS`).

The page says "checked about every N minutes" — it does **not** claim real-time. If refreshes fail, cached articles
are served with an explicit warning and the last successful refresh time.

## Sources (fixed list)
| id | Source | Method | Verification at build time |
|---|---|---|---|
| cisa | CISA Alerts & Advisories | RSS `cisa.gov/cybersecurity-advisories/all.xml` | URL confirmed via public docs; live fetch was bot-blocked from my tooling |
| nvd | NIST NVD | JSON API 2.0, critical CVEs from last 7 days (v3 and v4 filters = 2 requests) | Endpoint and params confirmed on NVD's developer page; not called live |
| ncsc-uk | UK NCSC | RSS | URL listed in feed directories; not fetched live |
| krebs | Krebs on Security | RSS | **Fetched live; format confirmed** |
| bleepingcomputer | BleepingComputer | RSS | listed in feed directories; not fetched live |
| securityweek | SecurityWeek | RSS | listed in feed directories; not fetched live |
| schneier | Schneier on Security | Atom | listed in feed directories; not fetched live |
| project-zero | Google Project Zero | Atom | listed in feed directories; not fetched live |

Run `python -m app.services.news.check_sources` on a machine with internet to test all of them live.

## What is and isn't stored/shown
Only: title, the source's own short excerpt (plain text, ≤320 chars), link, source, publication time, category,
CVE ids found literally in the source's text, and NVD's own CVSS severity. Full article bodies (`content:encoded`,
Atom `<content>`) are ignored. Images are supported by the pipeline but **disabled for every source**
(`allow_images=False`) until a source's image terms are reviewed. Categories are assigned by a rule-based classifier
(no AI), and the page says so. No summaries are generated.

## Security controls
* Fetcher takes a configured source, never a URL; https only; host must be in the source's allow-list.
* Redirects handled manually (max 3), every hop re-validated; no downgrade to http; no cross-host hops.
* Hostname is resolved before connecting and refused if any answer is private/loopback/link-local/reserved.
* Timeouts, streamed download with a byte cap (+ overall deadline vs slow-drip), content-type check.
* Feeds containing `<!DOCTYPE`/`<!ENTITY` are rejected (no XXE / entity expansion); stdlib XML only.
* Article links must be on the source's own domains; no credentials, IPs, or non-http(s) schemes.
* All feed text is stripped to plain text and rendered by React as text; links use `rel="noopener noreferrer"`.
* Search text is regex-escaped; page size ≤ 50; unknown filter values → 422.
* Public routes have no auth dependency and expose no account data. The frontend does not send the bearer token.

## Known limitations
* DNS is checked just before connecting, not pinned to the connection, so a DNS-rebinding race is theoretically
  possible. Mitigated because URLs are fixed and host-allow-listed, never user-supplied.
* No per-IP rate limiter exists in this app; public endpoints are bounded (page size, query length, indexed reads)
  but a reverse-proxy rate limit is advisable in production.
* Categories can be imperfect; "Careers & skills" will often be empty because few feeds publish careers news.
