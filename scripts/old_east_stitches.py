#!/usr/bin/env python3
"""The cross-stitch ornaments of The Old Book of the East.

Each motif is drawn on the counted-thread grid of East European embroidery: a
string of cells, '.' empty and a letter for a stitch in that colour. They are
original drawings of traditional geometric motifs (no pattern is copied):

  band     a chain of diamonds, each with a ring and a heart, between running
           stitches: the embroidered end of a ritual towel (ștergar, rushnyk)
  divider  a great diamond between two small ones
  emblem   the "sown field": a rhombus quartered, a seed in each quarter, forked
           hooks at the corners, an old fertility motif of Romanian and
           Ukrainian embroidery
  mini     a small diamond with a seed, for the top bar

They render as square stitches (crisp at small sizes) or as X stitches (the
cover). scripts/build_old_east.py and scripts/make_old_east_card.py import this
module for the inline emblem; old-east/book.css and the home card in
_includes/css/main.css carry the data URIs this script prints:

    py scripts/old_east_stitches.py        # CSS custom properties to paste

Re-run it and paste its output when a motif or a thread colour changes.
"""
import sys
import urllib.parse

MOTIFS = {
    "band": """
r.r.r.r.
........
....r...
...r.r..
..r.k.r.
.r.k.k.r
r.k.r.k.
.r.k.k.r
..r.k.r.
...r.r..
....r...
........
r.r.r.r.
""",
    "divider": """
............r............
...........r.r...........
.....r....r.k.r....r.....
....r.r..r.k.k.r..r.r....
.k.r.k.rr.k.r.k.rr.k.r.k.
....r.r..r.k.k.r..r.r....
.....r....r.k.r....r.....
...........r.r...........
............r............
""",
    "emblem": """
........k...k........
.........k.k.........
..........r..........
.........r.r.........
........r...r........
.......r.....r.......
......r...k...r......
.....r.r.....r.r.....
k...r...r...r...r...k
.k.r.....r.r.....r.k.
..r...k...r...k...r..
.k.r.....r.r.....r.k.
k...r...r...r...r...k
.....r.r.....r.r.....
......r...k...r......
.......r.....r.......
........r...r........
.........r.r.........
..........r..........
.........k.k.........
........k...k........
""",
    "mini": """
....r....
...r.r...
..r...r..
.r..k..r.
r..k.k..r
.r..k..r.
..r...r..
...r.r...
....r....
""",
}

# thread colours: r = the main thread, k = the second
LIGHT = {"r": "#a3241b", "k": "#2a1f1c"}   # madder red and soot on linen
DARK = {"r": "#e0715e", "k": "#e6dccd"}    # red and bleached linen on black wool
COVER = {"r": "#f4e9d6", "k": "#e2b25c"}   # linen and gold on the madder cover


def grid(name):
    rows = MOTIFS[name].strip("\n").split("\n")
    w = max(len(r) for r in rows)
    return [r.ljust(w, ".") for r in rows], w, len(rows)


def paths(name, mode="square"):
    """{colour letter: path data} for a motif, in cell units."""
    rows, w, h = grid(name)
    out = {}
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            if mode == "square":
                d = f"M{x} {y}h1v1h-1z"
            else:  # one cross stitch: two strokes corner to corner
                d = f"M{x}.2 {y}.2l.6.6m0-.6l-.6.6"
            out.setdefault(ch, []).append(d)
    return {k: "".join(v) for k, v in out.items()}, w, h


def svg(name, colours, mode="square", attrs=""):
    """A standalone SVG; colours maps each letter to a colour (or to None to skip it)."""
    p, w, h = paths(name, mode)
    head = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}'"
            + (" shape-rendering='crispEdges'" if mode == "square" else "") + attrs + ">")
    body = []
    for ch, d in p.items():
        c = colours.get(ch)
        if not c:
            continue
        if mode == "square":
            body.append(f"<path fill='{c}' d='{d}'/>")
        else:
            body.append(f"<path fill='none' stroke='{c}' stroke-width='.3' stroke-linecap='round' d='{d}'/>")
    return head + "".join(body) + "</svg>"


def inline_svg(name, cls, mode="square"):
    """An inline <svg> for a page, coloured by CSS: <path class="st-r">, <path class="st-k">."""
    p, w, h = paths(name, mode)
    extra = ' shape-rendering="crispEdges"' if mode == "square" else ""
    body = "".join(f'<path class="st-{ch}" d="{d}"/>' for ch, d in p.items())
    return f'<svg class="{cls}" viewBox="0 0 {w} {h}" aria-hidden="true"{extra}>{body}</svg>'


def data_uri(s):
    return 'url("data:image/svg+xml,' + urllib.parse.quote(s, safe=" /:=',.-()") + '")'


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("/* old-east/book.css, :root (light) */")
    print(f"  --band: {data_uri(svg('band', LIGHT))};")
    print(f"  --divider: {data_uri(svg('divider', LIGHT))};")
    print("/* old-east/book.css, dark */")
    print(f"    --band: {data_uri(svg('band', DARK))};")
    print(f"    --divider: {data_uri(svg('divider', DARK))};")
    print("/* old-east/book.css: the cover band, X stitch */")
    print(f"  --cover-band: {data_uri(svg('band', COVER, mode='x'))};")
    print("/* _includes/css/main.css, .book-cover-old-east: the cover band, square stitch (small) */")
    print(f"  {data_uri(svg('band', COVER))}")
    print("/* _includes/fiction.html: the card's emblem (square stitch) */")
    print(inline_svg("emblem", "book-cover-emblem"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
