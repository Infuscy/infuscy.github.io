# Verify skill for infuscy.github.io

This repo is a Jekyll + GitHub Pages site. It builds with the `github-pages`
gem, which pins Jekyll 3.9.0 / Liquid 4.0.3 — a stack that predates Ruby 3.2.

## The gotcha

RubyInstaller's current release is Ruby 4.0.x. Jekyll 3.9 / Liquid 4.0.3 call
`String#tainted?` (and `Integer#tainted?`, etc.), which was **removed in Ruby
3.2**. A plain `bundle exec jekyll build` dies with:

```
Liquid Exception: undefined method 'tainted?' for an instance of String
```

Ruby 4.0 also dropped `csv`, `bigdecimal`, `base64`, `drb`, `mutex_m` from
stdlib, which the same old stack requires.

## Working build recipe

Ruby is installed via RubyInstaller (user-dir, no admin) at `C:/Ruby40-x64`.
The MSYS2 DevKit was initialized with `ridk install` (option 3). Bundler runs
via `cmd //c` because the `.cmd` shims aren't directly executable from Bash.

1. **Gemfile** (committed) vendors the stdlib backports + webrick:

   ```ruby
   source "https://rubygems.org"
   gem "github-pages", group: :jekyll_plugins
   gem "webrick", "~> 1.8"
   # Ruby 3.4+ removed these from stdlib; old github-pages Jekyll (3.9) needs them.
   gem "csv", "~> 3.2"
   gem "bigdecimal", "~> 3.1"
   gem "base64", "~> 0.2"
   gem "drb", "~> 2.2"
   gem "mutex_m", "~> 0.2"
   ```

2. **Taint shim** at `C:/tmp/ruby31_shim.rb` (NOT in the repo) backports
   `tainted?` to String/Integer/Float/NilClass/TrueClass/FalseClass/Array/Hash.
   It must be loaded before Liquid — achieved by a wrapper script, not RUBYOPT
   (Ruby 4 ignores `-R` in RUBYOPT).

3. **Build wrapper** at `C:/tmp/build_site.rb`:

   ```ruby
   require_relative 'ruby31_shim'
   require 'jekyll'
   conf = Jekyll.configuration({
     'source'      => 'C:/GIT/infuscy.github.io',
     'destination' => 'C:/tmp/infuscy-build',
     'quiet'       => false,
   })
   Jekyll::Site.new(conf).process
   ```

4. **Run it** from the repo root:

   ```bash
   cd C:/GIT/infuscy.github.io
   cmd //c "set PATH=C:\Ruby40-x64\bin;%PATH% && bundle exec ruby C:/tmp/build_site.rb"
   ```

   Ignore the benign `warning: Logger not initialized properly` /
   `Jekyll::Stevenson#initialize: does not call super` lines.

5. **Inspect output** in `C:/tmp/infuscy-build/`.

## How to verify a change

The user-facing surface is the rendered HTML. After building:

- **Portfolio grid:** `grep -c 'col-sm-4 portfolio-item' build/index.html` → should equal number of `_posts`.
- **Modals:** `grep -oE 'id="portfolioModal-[0-9]+"' build/index.html` → one per post, sequential.
- **`| raw` fix (HTML in descriptions/credits renders as real markup, not escaped):**
  - escaped (BAD): `grep -c '&lt;a class=&quot;btn' build/index.html` → must be 0
  - real button (GOOD): a window around "Deschide raportul" shows `<a class="btn btn-primary" href="/bacYYYY/" target="_blank" rel="noopener">`.
- **Report links resolve:** each `/bacNNNN/` in the built index returns HTTP 200 when the build dir is served; a nonexistent one 404s.

To serve the build dir for HTTP checks:
```bash
(cd C:/tmp/infuscy-build && python3 -m http.server 8124 &) ; sleep 1.5
# ... curl localhost:8124/ ... ; pkill -f "http.server 8124"
```

## Notes

- `bundle install` only needs re-running when the Gemfile changes.
- The `investigatie de date/YYYY/...` subdirectories in the build output are
  normal Jekyll category-archive pages (from `permalink: pretty` + a `category`
  front-matter field). Harmless, not an error.
