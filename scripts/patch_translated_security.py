"""One-shot security patch for translated/*.html (novel reader pages).

1. Injects CSP + referrer meta tags after <meta charset="UTF-8"> (idempotent).
2. Replaces the inline reader-font-scale script (both the old localStorage
   version and the in-memory one) with /js/reader-font.js, so the CSP needs
   no 'unsafe-inline' for scripts; collapses accidental duplicates
   (chapter100.html had two).

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
    "script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; base-uri 'self'; form-action 'none'; "
    'object-src \'none\'; connect-src \'self\'">\n'
    '<meta name="referrer" content="strict-origin-when-cross-origin">'
)

CHARSET = '<meta charset="UTF-8">'


def main() -> int:
    files = sorted(glob.glob("translated/*.html"))
    patched_meta = 0
    patched_script = 0
    errors = []

    for path in files:
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()
        original = text

        # Older pages carry the previous CSP that allowed inline scripts.
        text = text.replace(METAS.replace("script-src 'self';", "script-src 'self' 'unsafe-inline';"), METAS)
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

        if text != original:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)

    print(f"files scanned:      {len(files)}")
    print(f"metas injected:     {patched_meta}")
    print(f"scripts replaced:   {patched_script}")
    if errors:
        print("ERRORS:")
        for e in errors:
            print(" ", e)
        return 1

    leftovers = [
        p
        for p in files
        if "localStorage" in open(p, encoding="utf-8").read()
        or "<script>" in open(p, encoding="utf-8").read()
        or METAS not in open(p, encoding="utf-8").read()
    ]
    if leftovers:
        print("LEFTOVERS:", leftovers)
        return 1
    print("verification: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
