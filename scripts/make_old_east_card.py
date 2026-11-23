#!/usr/bin/env python3
"""Render the social-preview image of The Old Book of the East: img/social-card-old-east.png.

A 1200x630 card in the cover's style (madder-red wool, two bands of linen and gold
cross-stitch, the "sown field" emblem, the title in the book's own font), written as a
self-contained HTML file (fonts and stitches inlined), screenshotted by headless Chrome
and saved as a palette PNG. The title and subtitle come from the book's Markdown, so
re-run this after changing them; the book's pages point og:image/twitter:image here.

Usage:
    py scripts/make_old_east_card.py [--chrome PATH]

Needs Chrome (or Edge) and Pillow (pip install pillow).
"""
import argparse
import base64
import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True  # importing the build script must not leave __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_old_east as book  # noqa: E402
import old_east_stitches as stitches  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: Pillow is required (pip install pillow)\n")
    sys.exit(1)

OUT = os.path.join(book.SITE_ROOT, "img", "social-card-old-east.png")
FONTS = os.path.join(book.BOOK_DIR, "fonts")
WIDTH, HEIGHT = 1200, 630
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><style>
@font-face {{ font-family: "Old East Text"; src: url(data:font/woff;base64,{regular}) format("woff"); font-weight: 400; font-style: normal; }}
@font-face {{ font-family: "Old East Text"; src: url(data:font/woff;base64,{italic}) format("woff"); font-weight: 400; font-style: italic; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ width: {w}px; height: {h}px; overflow: hidden; }}
body {{
  position: relative;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 40px 90px 0;
  background-color: #6b1712;
  background-image:
    radial-gradient(ellipse 65% 70% at 50% 44%, rgba(255,220,190,.12), transparent 70%),
    repeating-linear-gradient(45deg, rgba(0,0,0,.07) 0 1px, transparent 1px 5px),
    linear-gradient(180deg, #6b1712 0%, #3f0d0a 100%);
  color: #f4e9d6; text-align: center;
  font-family: "Old East Text", Cambria, serif;
}}
body::before, body::after {{
  content: ""; position: absolute; left: 0; right: 0; height: 52px;
  background: url("data:image/svg+xml;base64,{band}") left center / 32px 52px repeat-x;
}}
body::before {{ top: 22px; }}
body::after {{ bottom: 22px; }}
.emblem {{ width: 112px; height: 112px; margin-bottom: 22px; }}
.emblem .st-r {{ stroke: #f4e9d6; fill: none; stroke-width: .3; stroke-linecap: round; }}
.emblem .st-k {{ stroke: #e2b25c; fill: none; stroke-width: .3; stroke-linecap: round; }}
h1 {{ font-size: 86px; font-weight: 400; line-height: 1.02; letter-spacing: .005em;
      text-shadow: 0 3px 18px rgba(0,0,0,.35); }}
.sub {{ max-width: 880px; margin-top: 20px; font-size: 32px; font-style: italic; line-height: 1.35;
        color: #e9d6bd; text-wrap: balance; }}
.by {{ margin-top: 26px; font-size: 24px; font-variant-caps: all-small-caps; letter-spacing: .2em; color: #e2b25c; }}
</style></head><body>
{emblem}
<h1>{title}</h1>
<p class="sub">{subtitle}</p>
<p class="by">{author} · free to read online</p>
</body></html>
"""


def b64(path_or_text, is_text=False):
    data = path_or_text.encode("utf-8") if is_text else open(path_or_text, "rb").read()
    return base64.b64encode(data).decode("ascii")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome", default=next((p for p in CHROME_PATHS if os.path.isfile(p)), None))
    ap.add_argument("--raw", help="also keep Chrome's full-colour screenshot here (to compare palettes)")
    args = ap.parse_args()
    if not args.chrome or not os.path.isfile(args.chrome):
        sys.stderr.write("ERROR: Chrome/Edge not found; pass --chrome PATH\n")
        return 1
    with open(book.DEFAULT_SRC, encoding="utf-8") as fh:
        title, subtitle, _sections = book.parse_book(fh.read())
    # the card keeps the subtitle's first clause; the cover sets the rest under it
    subtitle = subtitle.partition(" — ")[0]

    html = PAGE.format(
        w=WIDTH, h=HEIGHT,
        regular=b64(os.path.join(FONTS, "old-east-text-regular.woff")),
        italic=b64(os.path.join(FONTS, "old-east-text-italic.woff")),
        band=b64(stitches.svg("band", stitches.COVER, mode="x"), True),
        emblem=stitches.inline_svg("emblem", "emblem", mode="x"),
        title=book.attr(title), subtitle=book.attr(subtitle), author=book.AUTHOR)

    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "card.html")
        shot = os.path.join(tmp, "card.png")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(html)
        subprocess.run([args.chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", f"--window-size={WIDTH},{HEIGHT}",
                        "--virtual-time-budget=4000", f"--user-data-dir={os.path.join(tmp, 'profile')}",
                        "--blink-settings=preferredColorScheme=1",
                        f"--screenshot={shot}", "file:///" + page.replace("\\", "/")],
                       check=True, capture_output=True, timeout=120)
        img = Image.open(shot).convert("RGB")
        if args.raw:
            img.save(args.raw)
        if img.size != (WIDTH, HEIGHT):
            raise SystemExit(f"ERROR: screenshot is {img.size}, expected {(WIDTH, HEIGHT)}")
        # 256 colours with dithering, as for Old Magic's card: smooth glow, ~150 KB. Only
        # link previews fetch this image, never a reader loading the page.
        img.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(
            OUT, optimize=True)
    print(f"wrote {os.path.relpath(OUT, book.SITE_ROOT)} ({os.path.getsize(OUT) / 1024:.1f} KB, {WIDTH}x{HEIGHT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
