# infuscy.github.io

Jekyll + GitHub Pages frontend for static Bacalaureat data reports. Reports are pre-built Vite apps committed into subdirs; the Jekyll layer is the card grid that links to them.

## Commands

| Command | Description |
|---------|-------------|
| `bundle exec jekyll serve` | Local preview at http://localhost:4000 |
| `JEKYLL_NO_BUNDLER_REQUIRE=1 ruby C:/Ruby40-x64/bin/jekyll build` | Local build on this machine: `bundle` is broken under git-bash (MSYS path mangling + Gemfile pins conflict with Ruby 4.0's installed gems). This skips bundler and works. Output in `_site/` (gitignored). |
| `npm run build` (in a report's own repo) | Build a report -> `web/dist/` to copy here |
| `py scripts/verify_digests.py` | Data guard: recomputes canary stats from `_verify/*_slim.parquet` vs the shipped JSON (also CI: `verify-data.yml`) |
| `py scripts/check_links.py _site` | Fail on broken internal links in a build (also CI: `site-build.yml`) |

## Architecture

```
_posts/           # one markdown post per report -> grid card (post URLs only redirect to the report)
_includes/        # Jekyll partials (nav, about, footer, portfolio_grid)
bac2025/ bac2026/ bac2526/   # pre-built Vite static apps (committed, not Jekyll-built)
_verify/          # slim candidate-level parquets for the data guard (unpublished: `_` dir)
translated/       # novel chapters: *.md sources (excluded from the site) -> *.html
img/portfolio/    # card thumbnails, referenced by posts
_config.yml       # site metadata, social, credits
Gemfile           # github-pages Jekyll + Ruby 3.4 stdlib backports
```

## Gotchas

- **Post `description` is plain text** — one or two sentences, shown on the card (clamped to 3 lines) and in `feed.xml`. Jekyll never escapes Liquid output, so keep HTML out of it.
- **Posts are data, not pages** — `_config.yml` defaults give them `layout: report-redirect`, so `/YYYY/MM/DD/slug/` is a noindex redirect to `/<report>/`. Each post needs a `report:` field (the report dir); sitemap and RSS link to `/<report>/`.
- **Cards are fully clickable** — the title link (`.card-link`) stretches over the card via `::after`; the "Deschide…" button is a decorative `<span aria-hidden="true">`. Any extra link inside a card needs `class="card-details"` (raised above the overlay) or it won't be clickable.
- **Theme `rem` = 16px** — `main.css` resets Bootstrap 3's `html { font-size: 10px }` to `100%`. Write sizes in `rem` assuming 16px; don't remove the reset (chapter and ToC pages depend on it too).
- **Card thumbnails are report screenshots** — 960×540 PNG in `img/portfolio/`, from headless Chrome at 1120×630, 2× DPR, of the served report (`chrome --headless=new --force-device-scale-factor=2 --window-size=1120,630 --screenshot=… http://localhost:4000/<dir>/`), then resized.
- **Reports are not built by Jekyll** — to edit one, change it in its upstream repo (`C:/GIT/BAC2025IUNIE`, `BAC2026`, `BAC2526`), rebuild, and copy `web/dist/` here. Never patch the shipped `bac*/` files in place: the next upstream rebuild silently reverts it.
- **Keep the reports lean** — no in-browser SQL/DuckDB-WASM (removed 2026-10-03: ~146 MB of WASM per two reports). The report CSP is `script-src 'self'`; don't add `'wasm-unsafe-eval'`/workers back.
- **`exclude:` in `_config.yml` replaces Jekyll's defaults** — internal docs (`*.md` here), `scripts/` and `translated/*.md` are kept out of the site; keep the Gemfile entries when editing the list.
- **No inline scripts on chapter pages** — `translated/*.html` and `fire-to-future/*.html` use `/js/reader-font.js` with a `script-src 'self'` CSP. After regenerating chapters, re-run `scripts/patch_translated_security.py` (novel) / `scripts/build_fire_to_future.py` (already emits it).
- **Gemfile pins `csv`, `bigdecimal`, `base64`, `drb`, `mutex_m`** — Ruby 3.4+ removed these from stdlib; old `github-pages` Jekyll needs them. Don't delete them.
- **Push to publish** — GitHub Pages builds automatically on push to `master`.
- **Contact is a plain `mailto:` link** (GDPR decision) — no forms, no Formspree, no Disqus, no third-party processors. If a contact form is ever added again, it needs consent handling + a documented processor in `privacy.html`.
- **Content pages are HTML, not markdown** (`privacy.html`, `novel/index.html`). Kramdown's `parse_block_html` is off, so markdown inside a `<div>` renders as raw text — the old `privacy.md` was broken exactly this way. Keep content pages as `.html` files.
- **Frontend JS stack**: jQuery 3.7.1 (`js/jquery-3.7.1.min.js`) + Bootstrap 3.4.1 (`js/bootstrap.min.js`). The themed Bootswatch CSS is 3.2.0 — it's customized with the report design tokens, so upgrade it only by re-applying the custom colors. `js/freelancer.js` must stay jQuery-3 compatible (no `.bind()`/`.delegate()`).

## Compliance (check before publishing anything user-facing)

Before adding content or changing site behavior, check the relevant EU/Romanian legal obligations and resolve them up front — the same way the article and the novel got their disclaimers.

- **AI-generated content (EU AI Act, Reg. (EU) 2024/1689, Art. 50)** — transparency obligations apply **from 2 Aug 2026**. Any text published to inform the public **on matters of public interest** that was generated/manipulated by an AI system must be **visibly disclosed** as such (Art. 50(4)), unless **both** apply: (a) the content underwent substantive **human review / editorial control** (fact-checking — not spell-checking), and (b) a natural/legal person holds **editorial responsibility** (their identity + contact must be findable — see [Commission Guidelines](https://ec.europa.eu/newsroom/dae/redirection/document/131215)). Disclosure must be clear, distinguishable and at first exposure (Art. 50(5)); machine-readable marking (Art. 50(2)) is the AI *provider's* duty, not ours. **Default policy: add a voluntary visible transparency note** (AI assistance + human verification + responsible person/contact) — pattern in use: `art47-hcl419.html` (Transparență note by the byline + footer mention).
- **Personal data (GDPR + Romanian Law 190/2018)** — current decision: no forms, no third-party processors, no analytics/fonts/external embeds (see Gotchas). Verify anything new that touches personal data or makes third-party requests.
- **Copyright** — only original/own or clearly licensed content (text, images, data, code); keep the non-commercial fan-work disclaimers on derivative works (`fire-to-future/`).
  - **The novel (`/novel/`, `translated/`) is a known, accepted exception — not an issue to raise in reviews.** It's an unofficial translation of an old Chinese web-novel fanfic; getting a licence is practically impossible, and the owner accepted the risk (see `SECURITY.md`). Keep its disclaimer + takedown-on-request note.
- **Other rules to sanity-check per feature** — accessibility (required for Art. 50(5) info too), consumer/marketing rules (Law 363/2007 — only if ads/sales are ever added), and any new EU/RO law that imposes a notice, disclaimer, or consent.
- **Verify from primary sources** — EUR-Lex for the regulation text, Commission guidelines for interpretation; note dates carefully (entry into force ≠ date obligations apply). When uncertain about whether a duty applies, add the voluntary notice anyway (cheap, honest, and it satisfies the strictest reading).

## Workflow: adding a report

1. In the report's repo: run the pipeline (`py preprocess/build_data.py`, `py analyze/stats.py`, `py preprocess/export_findings.py`), then `npm run build` in `web/` -> `web/dist/`.
2. Copy `web/dist/` into this repo as a new subdir (e.g. `bac2027/`), and the repo's `data/bac_slim.parquet` to `_verify/bac2027_slim.parquet` if the data guard should cover it.
3. Add `_posts/YYYY-MM-DD-slug.markdown` with `report: <dir>`, `img`, `category`, `project-date`, `stats` and a plain-text `description` (no `layout:` — the default handles it).
4. Add a screenshot thumbnail to `img/portfolio/` (see Gotchas).
5. Build, `py scripts/check_links.py _site`, `py scripts/verify_digests.py`, then push.
