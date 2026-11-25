#!/usr/bin/env python3
"""Render the social-preview image of The Spellbook of Old Stillness:
img/social-card-old-stillness.png.

A 1200x630 card in the cover's style (deep teal night water, the moon over it and its
reflection, faint level lines on the water, the title in the book's own font), written
as a self-contained HTML file (fonts inlined), screenshotted by headless Chrome and saved
as a palette PNG. The title and the subtitle (the first sentence of the book's opening
paragraph) come from the Markdown, so re-run this after changing them; the book's pages
point og:image/twitter:image here.

Usage:
    py scripts/make_old_stillness_card.py [--chrome PATH]

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
import build_old_stillness as book  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: Pillow is required (pip install pillow)\n")
    sys.exit(1)

OUT = os.path.join(book.SITE_ROOT, "img", "social-card-old-stillness.png")
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
  padding: 0 110px 18px;
  background-color: #0c2120;
  background-image:
    radial-gradient(ellipse 46% 52% at 50% 26%, rgba(241,229,196,.12), transparent 70%),
    linear-gradient(180deg, #13302e 0%, #0c2120 58%, #071312 100%);
  color: #f4eedd; text-align: center;
  font-family: "Old East Text", Cambria, serif;
}}
body::after {{
  content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 34%;
  background: repeating-linear-gradient(180deg, rgba(241,229,196,.05) 0 1px, transparent 1px 11px);
  -webkit-mask: linear-gradient(transparent, #000 70%); mask: linear-gradient(transparent, #000 70%);
}}
.cover-emblem {{ width: 250px; height: auto; margin-bottom: 14px; overflow: visible; }}
.em-moon {{ fill: #f1e5c4; }}
.em-halo {{ fill: none; stroke: #f1e5c4; opacity: .3; }}
.em-water {{ fill: none; stroke: #f1e5c4; stroke-linecap: round; }}
.em-r1 {{ opacity: .7; }} .em-r2 {{ opacity: .45; }} .em-r3 {{ opacity: .25; }}
h1 {{ position: relative; font-size: 84px; font-weight: 400; line-height: 1.04; letter-spacing: .005em;
      text-wrap: balance; text-shadow: 0 3px 18px rgba(0,0,0,.35); }}
.sub {{ position: relative; max-width: 860px; margin-top: 20px; font-size: 32px; font-style: italic; line-height: 1.35;
        color: #c9d6cf; text-wrap: balance; }}
.by {{ position: relative; margin-top: 24px; font-size: 24px; font-variant-caps: all-small-caps; letter-spacing: .2em;
       color: #dcbc74; }}
</style></head><body>
{emblem}
<h1>{title}</h1>
<p class="sub">{subtitle}</p>
<p class="by">{author} · free to read online</p>
</body></html>
"""


def b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome", default=next((p for p in CHROME_PATHS if os.path.isfile(p)), None))
    ap.add_argument("--raw", help="also keep Chrome's full-colour screenshot here (to compare palettes)")
    args = ap.parse_args()
    if not args.chrome or not os.path.isfile(args.chrome):
        sys.stderr.write("ERROR: Chrome/Edge not found; pass --chrome PATH\n")
        return 1
    with open(book.DEFAULT_SRC, encoding="utf-8") as fh:
        title, _date, intro, _sections = book.parse_book(fh.read())
    # the card's subtitle is the opening paragraph's first sentence, as on the cover
    subtitle = book.md_inline(" ".join(intro)).partition(". ")[0] + "."

    html = PAGE.format(
        w=WIDTH, h=HEIGHT,
        regular=b64(os.path.join(book.FONT_DIR, "old-east-text-regular.woff")),
        italic=b64(os.path.join(book.FONT_DIR, "old-east-text-italic.woff")),
        emblem=book.emblem("cover-emblem", "cover"),
        title=book.attr(title), subtitle=subtitle, author=book.AUTHOR)

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
        # 256 colours with dithering, as for the other books' cards: the glow stays smooth.
        # Only link previews fetch this image, never a reader loading the page.
        img.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(
            OUT, optimize=True)
    print(f"wrote {os.path.relpath(OUT, book.SITE_ROOT)} ({os.path.getsize(OUT) / 1024:.1f} KB, {WIDTH}x{HEIGHT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
