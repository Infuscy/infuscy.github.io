#!/usr/bin/env python3
"""Make the web fonts of The Book of Old Magic (old-magic/fonts/).

They are subsets of Gentium Book Plus 6.101 by SIL International (SIL Open Font
License 1.1), downloaded from https://github.com/google/fonts/tree/main/ofl/gentiumbookplus
(the four GentiumBookPlus-*.ttf files and OFL.txt). Gentium was chosen because it
carries every letter of the book's transliterations (ḫ ṣ ṭ, subscript digits),
which Palatino, Georgia and Sitka lack.

The OFL reserves the names "Gentium" and "SIL", and a subset in another format is
a Modified Version, so the fonts are renamed "Old Magic Text". SIL's copyright and
licence stay in the name table, the designers stay credited, and OFL.txt is copied
next to the fonts unchanged.

The kept ranges are wider than the book needs today (Latin with the scholarly
transliteration letters, punctuation, sub/superscripts), so small text edits do not
need a new subset; scripts/build_old_magic.py checks that every character of the
pages is in the fonts and says so when one is missing.

Usage:
    py scripts/subset_old_magic_fonts.py --src DIR [--out old-magic/fonts]

Needs fontTools (pip install fonttools). Writes WOFF (zlib): WOFF2 would need the
brotli module, and every browser the site supports reads WOFF.
"""
import argparse
import os
import shutil
import sys

try:
    from fontTools import subset
    from fontTools.ttLib import TTFont
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: fontTools is required (pip install fonttools)\n")
    sys.exit(1)

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_OUT = os.path.join(SITE_ROOT, "old-magic", "fonts")

FAMILY = "Old Magic Text"
STYLES = {  # source file -> (style name, output file)
    "GentiumBookPlus-Regular.ttf": ("Regular", "old-magic-text-regular.woff"),
    "GentiumBookPlus-Italic.ttf": ("Italic", "old-magic-text-italic.woff"),
    "GentiumBookPlus-Bold.ttf": ("Bold", "old-magic-text-bold.woff"),
    "GentiumBookPlus-BoldItalic.ttf": ("Bold Italic", "old-magic-text-bold-italic.woff"),
}

RANGES = [
    (0x0020, 0x007E),  # Basic Latin
    (0x00A0, 0x00FF),  # Latin-1 Supplement
    (0x0100, 0x017F),  # Latin Extended-A (š ā ē ī ū ğ …)
    (0x0218, 0x021B),  # Ș ș Ț ț (Romanian comma below)
    (0x02BC, 0x02BF),  # ʼ ʽ ʾ ʿ (aleph and ayin in transliteration)
    (0x02C6, 0x02C7),  # spacing circumflex, caron
    (0x02D8, 0x02DD),  # spacing breve, dot, ring, ogonek, tilde, double acute
    (0x0300, 0x0331),  # combining accents, incl. dot, breve and macron below
    (0x1E00, 0x1E9F),  # Latin Extended Additional without Vietnamese (ḫ ṣ ṭ ḥ ḍ …)
    (0x2000, 0x206F),  # General Punctuation (dashes, quotes, …, ′, spaces)
    (0x2070, 0x209F),  # superscripts and subscripts (TU₆, ku₄)
    (0x20AC, 0x20AC),  # €
    (0x2116, 0x2116),  # №
    (0x2122, 0x2122),  # ™
    (0x2190, 0x2193),  # ← ↑ → ↓ (the top bar's "← Febuse")
    (0x2212, 0x2212),  # − (the A− button)
    (0x25CC, 0x25CC),  # dotted circle, for stray combining marks
    (0xFB00, 0xFB04),  # ff fi fl ffi ffl
]

# ccmp/locl/mark/mkmk keep accents right; liga and kern are the text features.
# The character variants, stylistic sets and small caps are not used by the CSS.
FEATURES = ["ccmp", "locl", "liga", "kern", "mark", "mkmk"]

DESCRIPTION = ("Subset of Gentium Book Plus 6.101 by SIL International, made for "
               "infuscy.github.io/old-magic/. Renamed because the SIL Open Font License "
               "reserves the names \"Gentium\" and \"SIL\" for unmodified fonts.")


def unicodes():
    out = []
    for lo, hi in RANGES:
        out.extend(range(lo, hi + 1))
    return out


def rename(font, style):
    name = font["name"]
    version = (name.getDebugName(5) or "").strip()
    ps_name = "OldMagicText-" + style.replace(" ", "")
    # drop every record the new name replaces (all platforms), and the
    # manufacturer: SIL did not make this subset
    name.names = [r for r in name.names if r.nameID not in (1, 2, 3, 4, 6, 8, 10, 16, 17)
                  and r.platformID == 3]
    for name_id, text in ((1, FAMILY), (2, style),
                          (3, f"{FAMILY} {style}; {version}"),
                          (4, f"{FAMILY} {style}"), (6, ps_name), (10, DESCRIPTION)):
        name.setName(text, name_id, 3, 1, 0x409)
    font["OS/2"].achVendID = "NONE"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="folder with the GentiumBookPlus-*.ttf files and OFL.txt")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    missing = [n for n in list(STYLES) + ["OFL.txt"] if not os.path.isfile(os.path.join(args.src, n))]
    if missing:
        sys.stderr.write("ERROR: missing in --src: " + ", ".join(missing) + "\n")
        return 1
    os.makedirs(args.out, exist_ok=True)

    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = FEATURES
    opts.name_IDs = [0, 1, 2, 3, 4, 5, 6, 9, 13, 14]
    opts.name_languages = [0x409]
    opts.name_legacy = False
    opts.notdef_outline = True
    opts.glyph_names = False
    # No TrueType hints: 23% smaller, and Chrome on Windows (DirectWrite, subpixel
    # positioning) rendered the hinted and unhinted subsets equally crisp, while the
    # hints changed advance widths there; unhinted lays out the same on every system.
    opts.hinting = False

    total = 0
    for src_name, (style, out_name) in STYLES.items():
        font = TTFont(os.path.join(args.src, src_name))
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=unicodes())
        sub.subset(font)
        rename(font, style)
        out_path = os.path.join(args.out, out_name)
        font.flavor = "woff"
        font.save(out_path)
        size = os.path.getsize(out_path)
        total += size
        print(f"{out_name:34s} {len(font.getGlyphOrder()):4d} glyphs  {size / 1024:6.1f} KB")
    shutil.copyfile(os.path.join(args.src, "OFL.txt"), os.path.join(args.out, "OFL.txt"))
    print(f"total {total / 1024:.1f} KB; OFL.txt copied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
