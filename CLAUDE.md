# infuscy.github.io

Jekyll + GitHub Pages frontend for static Bacalaureat data reports. Reports are pre-built Vite apps committed into subdirs; the Jekyll layer is the grid + modals that link to them.

## Commands

| Command | Description |
|---------|-------------|
| `bundle exec jekyll serve` | Local preview at http://localhost:4000 |
| `JEKYLL_NO_BUNDLER_REQUIRE=1 ruby C:/Ruby40-x64/bin/jekyll build` | Local build on this machine: `bundle` is broken under git-bash (MSYS path mangling + Gemfile pins conflict with Ruby 4.0's installed gems). This skips bundler and works. Output in `_site/` (gitignored). |
| `npm run build` (in a report's own repo) | Build a report -> `web/dist/` to copy here |

## Architecture

```
_posts/           # one markdown post per report -> grid card + modal
_includes/        # Jekyll partials (nav, about, footer, modals, portfolio_grid)
bac2025/ bac2026/ bac2526/   # pre-built Vite static apps (committed, not Jekyll-built)
img/portfolio/    # card thumbnails, referenced by posts
_config.yml       # site metadata, social, credits
Gemfile           # github-pages Jekyll + Ruby 3.4 stdlib backports
```

## Gotchas

- **Posts carry HTML in `description`** — `{{ post.description | raw }}` in `_includes/modals.html`. Dropping `| raw` silently escapes the link/button markup.
- **`modal-id` must be unique and incremental** — ties the post to `portfolioModal-{N}` in `modals.html`.
- **Reports are not built by Jekyll** — to edit one, build it in its upstream repo and copy `web/dist/` into this repo.
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
- **Other rules to sanity-check per feature** — accessibility (required for Art. 50(5) info too), consumer/marketing rules (Law 363/2007 — only if ads/sales are ever added), and any new EU/RO law that imposes a notice, disclaimer, or consent.
- **Verify from primary sources** — EUR-Lex for the regulation text, Commission guidelines for interpretation; note dates carefully (entry into force ≠ date obligations apply). When uncertain about whether a duty applies, add the voluntary notice anyway (cheap, honest, and it satisfies the strictest reading).

## Workflow: adding a report

1. `npm run build` in the report's repo -> `web/dist/`.
2. Copy `web/dist/` into this repo as a new subdir (e.g. `bac2027/`).
3. Add `_posts/YYYY-MM-DD-slug.markdown` with a new unique `modal-id` and an HTML link in `description` to `/<dir>/`.
4. Add thumbnail to `img/portfolio/`.
5. Push.
