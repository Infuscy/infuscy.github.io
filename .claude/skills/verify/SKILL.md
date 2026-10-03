# Verify skill for infuscy.github.io

This repo is a Jekyll + GitHub Pages site. GitHub Pages builds it with the
`github-pages` gem (Jekyll 3.x / Liquid 4.0.3). CI mirrors that build in
`.github/workflows/site-build.yml` (`actions/jekyll-build-pages`) and checks
links; `.github/workflows/verify-data.yml` runs the BAC data guard.

## Build locally

Ruby 4.0 is installed via RubyInstaller at `C:/Ruby40-x64`. `bundle` is broken
under git-bash (MSYS path mangling + Gemfile pins vs Ruby 4.0's gems), so skip
bundler:

```bash
JEKYLL_NO_BUNDLER_REQUIRE=1 ruby C:/Ruby40-x64/bin/jekyll build -d "$SCRATCH/site"
```

Build into the session scratchpad (or `_site/`, gitignored). Ignore the benign
`Logger not initialized` / `Jekyll::Stevenson` warnings.

## How to verify a change

The user-facing surface is the rendered HTML. After building (`B` = build dir):

- **Links:** `py scripts/check_links.py "$B"` → `links: OK` (fails on any broken
  internal href/src, e.g. a relative `img/...` path on a nested page).
- **Data guard** (when `bac*/data`, `_verify/` or `_posts/` change):
  `py scripts/verify_digests.py` → `VERIFY: OK`.
- **Portfolio grid:** `grep -c 'col-sm-4 portfolio-item' "$B/index.html"` →
  number of `_posts`.
- **Modals:** `grep -oE 'id="portfolioModal-[0-9]+"' "$B/index.html"` → one per
  post, sequential; post HTML renders as real markup (a window around
  "Deschide raportul" shows `<a class="btn btn-primary" href="/bacYYYY/" ...>`).
- **Post URLs redirect:** `"$B/2025/06/01/bac2025-iunie/index.html"` is the
  `report-redirect` stub (noindex + canonical/refresh to `/bac2025/`).
- **Excluded files stay out:** no `CLAUDE.md`, `AUDIT.md`, `scripts/` or
  `translated/*.md` in the build.

For browser checks, serve the build dir and open it in the Browser pane:

```bash
cd "$B" && py -m http.server 8124 --bind 127.0.0.1   # run in background
```

Check `/`, `/bac2025/`, `/bac2026/`, `/bac2526/` and a chapter page
(`/translated/chapter001.html`) for console errors — every page has a strict
meta CSP (`script-src 'self'`), so an inline script or WASM would show up there.
