"""Idempotent patch for translated/*.html (novel reader pages): security + shared CSS.

1. Injects CSP + referrer meta tags after <meta charset="UTF-8">.
2. Replaces the inline reader-font-scale script (both the old localStorage
   version and the in-memory one) with /js/reader-font.js, so the CSP needs
   no 'unsafe-inline' for scripts; collapses accidental duplicates
   (chapter100.html had two).
3. Replaces the site stylesheet link + the per-page <style> block with the one
   shared /css/reader.css, and the two inline-styled notes with classes from
   it. With no inline style left, the CSP drops 'unsafe-inline' for styles too.

Run again after regenerating chapters upstream.
"""
import glob
import re
import sys

OLD_SCRIPT = """<script>
(function(){
  var scale = parseFloat(localStorage.getItem("reader-font-scale")) || 1;
  function apply(){ document.documentElement.style.setProperty("--reader-font-scale", scale); }
  apply();
  document.getElementById("fontDown").addEventListener("click", function(){ scale = Math.max(0.6, scale - 0.1); localStorage.setItem("reader-font-scale", scale); apply(); });
  document.getElementById("fontUp").addEventListener("click", function(){ scale = Math.min(2.0, scale + 0.1); localStorage.setItem("reader-font-scale", scale); apply(); });
})();
</script>"""

INLINE_SCRIPT = """<script>
(function(){
  var scale = 1;
  function apply(){ document.documentElement.style.setProperty("--reader-font-scale", scale); }
  apply();
  document.getElementById("fontDown").addEventListener("click", function(){ scale = Math.max(0.6, scale - 0.1); apply(); });
  document.getElementById("fontUp").addEventListener("click", function(){ scale = Math.min(2.0, scale + 0.1); apply(); });
})();
</script>"""

NEW_SCRIPT = '<script src="/js/reader-font.js"></script>'

METAS = (
    '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; '
    "script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; font-src 'self'; base-uri 'self'; form-action 'none'; "
    'object-src \'none\'; connect-src \'self\'">\n'
    '<meta name="referrer" content="strict-origin-when-cross-origin">'
)
# Earlier versions of the same metas: inline styles allowed, and before that inline scripts too.
METAS_INLINE_STYLE = METAS.replace("style-src 'self';", "style-src 'self' 'unsafe-inline';")
METAS_INLINE_SCRIPT = METAS_INLINE_STYLE.replace("script-src 'self';", "script-src 'self' 'unsafe-inline';")

CHARSET = '<meta charset="UTF-8">'

READER_CSS = '<link rel="stylesheet" href="/css/reader.css">'
RX_SITE_CSS = re.compile(r'<link rel="stylesheet" href="/style\.css">\n<style>.*?</style>', re.S)
RX_DISCLAIMER = re.compile(r'<div style="max-width:42rem;[^"]*">(?=<strong>Non-commercial fan translation)')
RX_FOOTNOTE = re.compile(r'<p style="text-align:center;font-size:\.8rem;[^"]*">(?=Unofficial non-commercial fan work)')


def main() -> int:
    files = sorted(glob.glob("translated/*.html"))
    patched_meta = 0
    patched_script = 0
    patched_css = 0
    errors = []

    for path in files:
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()
        original = text

        text = text.replace(METAS_INLINE_SCRIPT, METAS).replace(METAS_INLINE_STYLE, METAS)
        if METAS not in text:
            if CHARSET not in text:
                errors.append(f"{path}: no charset meta")
                continue
            text = text.replace(CHARSET, CHARSET + "\n" + METAS, 1)
            patched_meta += 1

        if OLD_SCRIPT in text or INLINE_SCRIPT in text:
            text = text.replace(OLD_SCRIPT, NEW_SCRIPT).replace(INLINE_SCRIPT, NEW_SCRIPT)
            patched_script += 1

        while NEW_SCRIPT + "\n" + NEW_SCRIPT in text:
            text = text.replace(NEW_SCRIPT + "\n" + NEW_SCRIPT, NEW_SCRIPT)

        text = RX_SITE_CSS.sub(READER_CSS, text, 1)
        text = RX_DISCLAIMER.sub('<div class="reader-disclaimer">', text, 1)
        text = RX_FOOTNOTE.sub('<p class="reader-footnote">', text, 1)
        if READER_CSS in text and READER_CSS not in original:
            patched_css += 1

        if text != original:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)

    print(f"files scanned:      {len(files)}")
    print(f"metas injected:     {patched_meta}")
    print(f"scripts replaced:   {patched_script}")
    print(f"stylesheets moved:  {patched_css}")
    if errors:
        print("ERRORS:")
        for e in errors:
            print(" ", e)
        return 1

    leftovers = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            page = fh.read()
        if ("localStorage" in page or "<script>" in page or METAS not in page
                or READER_CSS not in page or "<style" in page or ' style="' in page):
            leftovers.append(path)
    if leftovers:
        print("LEFTOVERS:", leftovers[:20], f"({len(leftovers)} files)")
        return 1
    print("verification: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
