# Security policy & threat model

## Reporting a vulnerability

- Preferred channel: https://infuscy.github.io/.well-known/security.txt
- Email: contact@febuse.com (also used for GDPR/data-subject requests)
- Supervisory authority for data-protection complaints: ANSPDCP — https://www.dataprotection.ro

## Threat model

This is a static GitHub Pages site: no backend, no database, no user input, no
accounts or sessions, no forms, no cookies, and no third-party analytics or
comment services. All content is owner-authored. The residual risks are:

1. supply chain (bundled client-side libraries),
2. client-side injection via authored HTML (`| raw` front matter),
3. clickjacking (GitHub Pages cannot set frame headers),
4. third-party requests made by the report SPAs (now reduced to OSM map tiles).

## Security posture

- HTTPS only (GitHub Pages; `github.io` is on the HSTS preload list).
- Content-Security-Policy via meta tag on the Jekyll layer (`_includes/head.html`)
  and on all three report SPAs (`bac2025/`, `bac2026/`, `bac2526/`). The report
  policy allows `'wasm-unsafe-eval'` (DuckDB-WASM), `worker-src 'self' blob:`,
  and `img-src ... https://tile.openstreetmap.org`. The novel chapter pages
  (`translated/*.html`, standalone HTML outside Jekyll) carry their own meta
  CSP + referrer policy — injected by `scripts/patch_translated_security.py`,
  which must be re-run after regenerating chapters upstream.
- Referrer policy meta tag everywhere (`strict-origin-when-cross-origin`).
- Frame-buster script in `js/freelancer.js` (Pages cannot set
  `X-Frame-Options`/`frame-ancestors`).
- No external fonts, analytics or comment widgets; all JS/CSS/fonts are local.
- No cookies, no localStorage/sessionStorage anywhere (the novel reader's font
  control is in-memory only, per-page).
- The novel TOC script lives in `js/novel-toc.js` + `/novel/chapters.js`
  (Jekyll-rendered data) — the Jekyll-layer CSP is `script-src 'self'` with no
  `'unsafe-inline'`.
- `rel="noopener"` on all `target="_blank"` links.
- `_site/` is gitignored — local build and screenshot artifacts are never published.

## Accepted risks (re-evaluate periodically)

- **Bootstrap 3.4.1** — CVE-2024-6484 / CVE-2024-6485 (carousel / tooltip-popover
  XSS). Bootstrap 3.x is EOL with no upstream fix. The vulnerable components are
  bundled but not used with untrusted data. Migration to Bootstrap 5 is backlog.
- **`| raw` HTML sinks** — `_posts/*.markdown` `description` and `site.credits`
  are rendered unescaped. That is a stored-XSS vector *if* third-party HTML is
  ever committed. Rule: post descriptions may only contain hand-written HTML.
- **jQuery 3.7.1** — no known CVEs; upgrade to 4.x is backlog only.
- **Font Awesome 4.1.0 / Bootswatch CSS 3.2.0** — old, but CSS/fonts only; no
  known vulnerabilities.
- **The novel** (`/novel/`, `translated/`) — a 1,862-chapter fanfiction
  translation. Copyright exposure (original author's text + Blizzard IP) was
  reviewed and explicitly accepted by the site owner on 2026-08-13. Chapters
  are generated upstream: after regenerating, re-run
  `scripts/patch_translated_security.py` (idempotent) or the CSP metas and the
  localStorage-free reader script regress.
- **Local Ruby build stack** — the `github-pages` gem pins legacy versions:
  liquid 4.0.3 (CVE-2025-47904), rouge 3.26.0 (CVE-2021-44172), commonmarker
  0.17.13 (bundled cmark-gfm CVEs), kramdown 2.3.1 (fixed). GitHub Pages builds
  with its own locked set and all templates are trusted, so exposure is limited
  to local `jekyll serve` builds. `Gemfile.lock` is intentionally gitignored;
  periodically run `bundle update`.
- **GitHub Pages header limits** — no custom HTTP headers, so no
  `X-Frame-Options`, `frame-ancestors` or HSTS overrides; meta CSP + the
  frame-buster are the available mitigations.

## EU legislation posture

- GDPR privacy notice: `/privacy/` (GitHub Pages processor disclosure, OSM tile
  transfer, no cookies/analytics/localStorage).
- Legitimate Interests Assessment for the BAC candidate-level data: `/lia/`
  (`lia.html`; no direct identifiers, min-n aggregate thresholds, client-side
  only). The privacy notice no longer calls the data "anonymous" — it states
  the absence of direct identifiers and links the LIA.
- OSM Tile Usage Policy: maps attribute "© OpenStreetMap contributors".
- DSA (2022/2065) and the European Accessibility Act (2019/882): assessed as
  not applicable to this personal, non-commercial static site.

## Report apps: upstream maintenance

The three report SPAs are built in their upstream repos (`BAC2025IUNIE`,
`BAC2026`, `BAC2526`) and copied into this repo as `web/dist/`. On 2026-08-13
the security fixes below were applied **both** to the committed dist in this
repo (stopgap, so the live site is correct now) **and** to the upstream repos,
so future rebuilds keep them:

1. `web/index.html` (all three repos): Google Fonts `preconnect` + stylesheet
   links removed; CSP meta + referrer meta added (strict policy with
   `'wasm-unsafe-eval'` for DuckDB-WASM, `worker-src 'self' blob:`,
   `img-src ... https://tile.openstreetmap.org`).
2. `web/src/components/CountyMap.tsx` (BAC2025IUNIE, BAC2026): attribution
   `&copy; OpenStreetMap contributors`, tile URL without the deprecated
   `{s}.` subdomain prefix.

> When updating a report: run `npm run build` in the repo's `web/` **before**
> copying `web/dist/` into this repo — copying an un-rebuilt dist would
> re-introduce the old font links and attribution.
