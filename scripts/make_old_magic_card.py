#!/usr/bin/env python3
"""Render the social-preview image of The Book of Old Magic: img/social-card-old-magic.png.

A 1200x630 card in the cover's style (lapis glazed brick, the rosette frieze of the
Ishtar Gate, Ištar's eight-pointed star, the title in the book's own font), written as
a self-contained HTML file (fonts and patterns inlined), screenshotted by headless
Chrome and saved as a palette PNG. The title and subtitle come from the book's Markdown,
so re-run this after changing them; the book's pages point og:image/twitter:image here.

Usage:
    py scripts/make_old_magic_card.py [--chrome PATH]

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
import build_old_magic as book  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: Pillow is required (pip install pillow)\n")
    sys.exit(1)

OUT = os.path.join(book.SITE_ROOT, "img", "social-card-old-magic.png")
FONTS = os.path.join(book.BOOK_DIR, "fonts")
WIDTH, HEIGHT = 1200, 630
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

# the cover's ornaments (see old-magic/book.css)
ROSETTES = ("<svg xmlns='http://www.w3.org/2000/svg' width='34' height='22' viewBox='0 0 34 22'>"
            "<path d='M0 1.5h34M0 20.5h34' stroke='#e3bd62' stroke-opacity='.75'/>"
            "<g fill='#f4ead2'>"
            + "".join(f"<ellipse cx='17' cy='6.3' rx='1.75' ry='3.3' transform='rotate({k * 45} 17 11)'/>"
                      for k in range(8))
            + "</g><circle cx='17' cy='11' r='2.1' fill='#e3bd62'/></svg>")
BRICKS = ("<svg xmlns='http://www.w3.org/2000/svg' width='48' height='24' viewBox='0 0 48 24'>"
          "<path d='M0 .5h48M0 12.5h48M.5 0v12M24.5 12v12' stroke='#fff' stroke-opacity='.07' fill='none'/></svg>")
EMBLEM = ('<svg class="emblem" viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="46"/>'
          '<circle cx="50" cy="50" r="41"/><path d="M50 12L54.97 37.99L76.87 23.13L62.01 45.03L88 50'
          'L62.01 54.97L76.87 76.87L54.97 62.01L50 88L45.03 62.01L23.13 76.87L37.99 54.97L12 50L37.99 45.03'
          'L23.13 23.13L45.03 37.99Z"/></svg>')

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><style>
@font-face {{ font-family: "Old Magic Text"; src: url(data:font/woff;base64,{regular}) format("woff"); font-weight: 400; font-style: normal; }}
@font-face {{ font-family: "Old Magic Text"; src: url(data:font/woff;base64,{italic}) format("woff"); font-weight: 400; font-style: italic; }}
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ width: {w}px; height: {h}px; overflow: hidden; }}
body {{
  position: relative;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 0 90px;
  background-color: #1b3a6b;
  background-image: url("data:image/svg+xml;base64,{bricks}"),
    radial-gradient(ellipse 65% 70% at 50% 42%, rgba(255,255,255,.11), transparent 70%),
    linear-gradient(180deg, #1b3a6b 0%, #122a50 100%);
  color: #f4ead2; text-align: center;
  font-family: "Old Magic Text", Cambria, serif;
}}
body::before, body::after {{
  content: ""; position: absolute; left: 0; right: 0; height: 36px;
  background: url("data:image/svg+xml;base64,{rosettes}") left center / 55.6px 36px repeat-x;
}}
body::before {{ top: 18px; }}
body::after {{ bottom: 18px; }}
.emblem {{ width: 104px; height: 104px; margin-bottom: 26px; }}
.emblem circle {{ fill: none; stroke: #e3bd62; stroke-width: 1.4; }}
.emblem circle + circle {{ stroke-width: .7; opacity: .75; }}
.emblem path {{ fill: #e3bd62; }}
h1 {{ font-size: 94px; font-weight: 400; line-height: 1.02; letter-spacing: .005em;
      text-shadow: 0 3px 18px rgba(0,0,0,.35); }}
.sub {{ max-width: 860px; margin-top: 22px; font-size: 33px; font-style: italic; line-height: 1.35;
        color: #e6d8b8; text-wrap: balance; }}
.by {{ margin-top: 30px; font-size: 19px; letter-spacing: .22em; text-transform: uppercase; color: #e3bd62; }}
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

    html = PAGE.format(
        w=WIDTH, h=HEIGHT,
        regular=b64(os.path.join(FONTS, "old-magic-text-regular.woff")),
        italic=b64(os.path.join(FONTS, "old-magic-text-italic.woff")),
        bricks=b64(BRICKS, True), rosettes=b64(ROSETTES, True), emblem=EMBLEM,
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
        # 256 colours with dithering: ~150 KB, smooth. Fast-octree without dithering is a
        # third of that but rings the glow behind the title; full colour is ~340 KB. Only
        # link previews fetch this image, never a reader loading the page.
        img.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(
            OUT, optimize=True)
    print(f"wrote {os.path.relpath(OUT, book.SITE_ROOT)} ({os.path.getsize(OUT) / 1024:.1f} KB, {WIDTH}x{HEIGHT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
