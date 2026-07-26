# infuscy.github.io

Jekyll + GitHub Pages frontend for static Bacalaureat data reports. Reports are pre-built Vite apps committed into subdirs; the Jekyll layer is the grid + modals that link to them.

## Commands

| Command | Description |
|---------|-------------|
| `bundle exec jekyll serve` | Local preview at http://localhost:4000 |
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

## Workflow: adding a report

1. `npm run build` in the report's repo -> `web/dist/`.
2. Copy `web/dist/` into this repo as a new subdir (e.g. `bac2027/`).
3. Add `_posts/YYYY-MM-DD-slug.markdown` with a new unique `modal-id` and an HTML link in `description` to `/<dir>/`.
4. Add thumbnail to `img/portfolio/`.
5. Push.
