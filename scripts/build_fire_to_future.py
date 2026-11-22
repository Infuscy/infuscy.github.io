#!/usr/bin/env python3
"""Build the per-chapter web edition of FIRE TO FUTURE for infuscy.github.io.

Reads the markdown book in C:\\GIT\\Apocalypse\\book (front matter, 51 chapters in
6 parts, appendices A-G, the source policy), converts each section into a standalone reader page
under fire-to-future/, writes the contents data file _data/fire_to_future_chapters.json
(fire-to-future/index.html lists it, sitemap.xml maps it), and copies the print PDF
(Fire-To-Future.pdf) next to the pages.

The conversion mirrors book/tools/build_html.py (same markdown extensions, the
same id namespacing, meta blockquote and callout handling) so the web pages and
the print edition stay content-identical; the only differences are
per-section pages instead of one long document, cross-file .md links rewritten
to page URLs, tables wrapped for horizontal scrolling, and reading markup that
never changes the text: the part and chapter kickers over each title, a chapter's
metadata set as a spec plate (definition list, difficulty gauge, chapter chips),
section numbers in their own span, and a pager naming the neighbouring pages.

Usage:
    python scripts/build_fire_to_future.py [--src C:\\GIT\\Apocalypse]

Requires Python 3 + the `markdown` package (pip install markdown).

The script rewrites reader.css (the theme of the pages and of the hand-written
index.html, from the CSS constant below) and deletes only the generated page files
inside fire-to-future/ (front-matter.html, chNN.html, appendix-X.html,
source-policy.html); it never touches index.html or anything outside that directory.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
from datetime import date
from urllib.parse import quote

try:
    import markdown
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: the `markdown` package is required (pip install markdown)\n")
    sys.exit(1)

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Apocalypse"))

OUT_PAGES_DIR = os.path.join(SITE_ROOT, "fire-to-future")
OUT_DATA_JSON = os.path.join(SITE_ROOT, "_data", "fire_to_future_chapters.json")

# ----------------------------------------------------------------------- manifest

PARTS = [
    ("Part I", "Ignition",
     "Survival and Settled Life \u2014 fire \u2192 villages",
     ["part1/ch01_fire.md", "part1/ch02_toolkit.md", "part1/ch03_textiles.md",
      "part1/ch04_food.md", "part1/ch05_pottery.md", "part1/ch06_shelter.md",
      "part1/ch07_agriculture.md", "part1/ch08_animals.md"]),
    ("Part II", "The Ancient Engine",
     "Cities, Metals, Records \u2014 villages \u2192 classical industry",
     ["part2/ch09_trade_money.md", "part2/ch10_copper_bronze.md", "part2/ch11_writing.md",
      "part2/ch12_mathematics.md", "part2/ch13_mining.md", "part2/ch14_iron.md",
      "part2/ch15_mechanisms.md", "part2/ch16_water_wind.md", "part2/ch17_chemistry_ancient.md"]),
    ("Part III", "The Acceleration",
     "Printing, Science, and Fossil Power",
     ["part3/ch18_printing.md", "part3/ch19_optics.md", "part3/ch20_instruments.md",
      "part3/ch21_blackpowder_acids.md", "part3/ch22_coke_iron.md", "part3/ch23_steam.md",
      "part3/ch24_transport.md", "part3/ch25_electricity_1.md", "part3/ch26_electricity_2.md"]),
    ("Part IV", "The Modern Stack",
     "1870 \u2192 1960",
     ["part4/ch27_steel_concrete.md", "part4/ch28_petroleum.md", "part4/ch29_combustion.md",
      "part4/ch30_sanitation.md", "part4/ch31_medicine.md", "part4/ch32_green_revolution.md",
      "part4/ch33_flight.md", "part4/ch34_vacuum_tubes.md", "part4/ch35_semiconductors.md",
      "part4/ch36_computers.md", "part4/ch37_nuclear.md"]),
    ("Part V", "Planetary Systems",
     "1950 \u2192 present",
     ["part5/ch38_polymers_materials.md", "part5/ch39_rocketry.md", "part5/ch40_satellites.md",
      "part5/ch41_fiber_optics.md", "part5/ch42_internet.md", "part5/ch43_energy_mastery.md",
      "part5/ch44_biotech.md", "part5/ch45_robotics.md", "part5/ch46_machine_intelligence.md",
      "part5/ch47_institutions.md"]),
    ("Optional Defense Annex", "Defense and Wartime Spillovers",
     "Optional context — outside the core build sequence",
     ["part6/ch48_fortification.md", "part6/ch49_gunpowder_weapons.md",
      "part6/ch50_naval_power.md", "part6/ch51_industrial_war.md"]),
]

APPENDICES = [
    "appendix_A_critical_path.md", "appendix_B_dead_ends.md", "appendix_C_jumps.md",
    "appendix_D_minimum_viable_stack.md", "appendix_E_timeline.md",
    "appendix_F_glossary.md", "appendix_G_key_numbers.md",
]

# printed after the appendices (book/tools/build_html.py REFERENCE_NOTES)
REFERENCE_NOTES = ["SOURCE_POLICY.md"]

FRONT_MATTER = "00_front_matter.md"

# book-relative posix path -> key (filename stem)
KEYS = {}
for _part in PARTS:
    for _f in _part[3]:
        KEYS[os.path.splitext(os.path.basename(_f))[0]] = _f
for _f in APPENDICES + REFERENCE_NOTES + [FRONT_MATTER]:
    KEYS[os.path.splitext(os.path.basename(_f))[0]] = _f


# full divider label per part (label + name, e.g. "Part I — Ignition")
PART_FULL = {pl: f"{pl} \u2014 {pn}" for pl, pn, _pd, _fs in PARTS}

# ----------------------------------------------------------------------- helpers

def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def first_h1(text):
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else "(untitled)"


def split_h1(text):
    """Return (title_without_prefix, 'Chapter N' style label or None)."""
    t = first_h1(text)
    m = re.match(r"^Chapter\s+(\d+)\s*:\s*(.*)$", t)
    if m:
        return m.group(2).strip(), f"Chapter {int(m.group(1))}"
    return t, None


def page_file(key):
    """key (filename stem) -> output page filename."""
    if key == "00_front_matter":
        return "front-matter.html"
    if key.startswith("appendix_"):
        return f"appendix-{key.split('_')[1].lower()}.html"
    if key == "SOURCE_POLICY":
        return "source-policy.html"
    num = int(re.match(r"ch(\d+)", key).group(1))
    return f"ch{num:02d}.html"


def nav_label(kind, num):
    """Prev/next button text for a sequence entry."""
    return {"chapter": f"Chapter {num}", "appendix": f"Appendix {num}",
            "reference": "Source policy"}.get(kind, "Front matter")


def load_callouts(book_dir):
    """Callout label -> CSS class suffix, read from the book's own
    book/tools/callouts.py (the vocabulary its print build styles and its
    linter enforces), so new labels never drift out of sync."""
    spec = importlib.util.spec_from_file_location(
        "ftf_callouts", os.path.join(book_dir, "tools", "callouts.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CALLOUTS


def word_count(rel, book_dir):
    txt = read(os.path.join(book_dir, rel))
    return len(re.findall(r"\S+", txt))


class Converter:
    """Mirrors book/tools/build_html.py convert() but links across pages."""

    def __init__(self, book_dir):
        self.book_dir = book_dir
        self.callouts = load_callouts(book_dir)
        self.callout_re = re.compile(
            r"<p><strong>("
            + "|".join(re.escape(k) for k in sorted(self.callouts, key=len, reverse=True))
            + r")[:.]?</strong>"
        )
        self.md = markdown.Markdown(
            extensions=["tables", "fenced_code", "sane_lists", "toc"],
            extension_configs={"toc": {"anchorlink": False}},
        )

    def _rewrite_links(self, src, cur_rel):
        """Rewrite [text](rel.md[#frag]) to per-page URLs; fix bare 'chNN' stems."""
        cur_dir = os.path.dirname(os.path.join(self.book_dir, cur_rel))

        def repl(m):
            target, frag = m.group(1), m.group(2)
            norm = os.path.normpath(os.path.join(cur_dir, target))
            rel = os.path.relpath(norm, self.book_dir).replace("\\", "/")
            key = None
            for k, v in KEYS.items():
                if v == rel:
                    key = k
                    break
            if key is None:
                return m.group(0)  # leave unknown .md targets untouched
            page = page_file(key)
            if frag:
                return f"]({page}#{key}-{frag.lstrip('#')})"
            return f"]({page})"

        src = re.sub(r"\]\(([^)#\s]+\.md)(#[^)\s]*)?\)", repl, src)
        # upstream typo fix: [Ch 30](ch30) -> ch30.html (same key-less stem pattern)
        src = re.sub(
            r"\]\((ch\d{1,2}|appendix_[A-G][a-z_]+)\)",
            lambda m: f"]({page_file(m.group(1))})",
            src,
        )
        return src

    def convert(self, rel):
        src = read(os.path.join(self.book_dir, rel))
        src = self._rewrite_links(src, rel)
        key = os.path.splitext(os.path.basename(rel))[0]
        self.md.reset()
        body = self.md.convert(src)
        # namespace heading ids to keep them unique (same scheme as print build)
        # NOTE: \g<1> is required — a bare \1 before a digit-leading key
        # (00_front_matter) would parse as the octal escape \100 and mangle ids.
        body = re.sub(r'(\bid=")', rf"\g<1>{key}-", body)

        def fix_href(m):
            frag = m.group(1)
            if frag.startswith("sec-"):
                return m.group(0)
            owner = frag.split("-", 1)[0]
            if owner in KEYS:  # already a fully-qualified cross-file anchor
                return m.group(0)
            return f'href="#{key}-{frag}"'

        body = re.sub(r'href="#([^"]+)"', fix_href, body)
        # metadata blockquote directly after the chapter H1
        body = re.sub(r"(</h1>\s*)<blockquote>", r'\1<blockquote class="meta">', body, count=1)

        def meta_breaks(m):
            inner = re.sub(
                r"\s*(?:·\s*)?(<strong>(?:Requires|Unlocks|Annex status|Data snapshot):</strong>)",
                r"<br>\1", m.group(1))
            return f'<blockquote class="meta">{inner}</blockquote>'

        body = re.sub(
            r'<blockquote class="meta">(.*?)</blockquote>',
            meta_breaks,
            body,
            flags=re.S,
        )
        # callout paragraphs (mirrors book/tools/build_html.py; labels from callouts.py)
        def callout(m):
            label = m.group(1)
            return f'<p class="co co-{self.callouts[label]}"><strong>{label}:</strong>'

        body = self.callout_re.sub(callout, body)
        # horizontal-scroll wrapper for wide tables
        body = body.replace("<table>", '<div class="table-wrap"><table>')
        body = body.replace("</table>", "</table></div>")
        return body


# ----------------------------------------------------------------------- template

# Part -> theme key (body data-part): fire to future, one accent per part
PART_KEYS = {
    "Part I": "p1", "Part II": "p2", "Part III": "p3", "Part IV": "p4", "Part V": "p5",
    "Optional Defense Annex": "annex", "Appendices": "appx", "Reference note": "ref",
}
PART_DESC = {pl: pd for pl, _pn, pd, _fs in PARTS}

# Difficulty word -> segments lit on the heat gauge of the chapter's spec plate
DIFFICULTY = {"low": 1, "low–mid": 2, "mid": 3, "mid–high": 4, "high": 5, "extreme": 6}

WORDS_PER_MINUTE = 230  # same reading speed as The Book of Old Magic

# The emblem: a cog around a flame (fill-rule evenodd: the cog, its bore, the flame
# inside it). Original drawing; fire-to-future/index.html repeats the path inline.
EMBLEM_PATH = (
    "M10.09 3L10.61 0.68L13.39 0.68L13.91 3L17.01 4.28L19.02 3.02L20.98 4.98L19.72 6.99"
    "L21 10.09L23.32 10.61L23.32 13.39L21 13.91L19.72 17.01L20.98 19.02L19.02 20.98"
    "L17.01 19.72L13.91 21L13.39 23.32L10.61 23.32L10.09 21L6.99 19.72L4.98 20.98"
    "L3.02 19.02L4.28 17.01L3 13.91L0.68 13.39L0.68 10.61L3 10.09L4.28 6.99L3.02 4.98"
    "L4.98 3.02L6.99 4.28Z"
    "M19 12A7 7 0 1 0 5 12A7 7 0 1 0 19 12Z"
    "M12 6.2C13.6 8.5 16 10.3 16 13.8A4 4 0 0 1 8 13.8C8 12 8.9 10.8 10 9.9"
    "C10 11.2 10.6 12.1 11.5 12.5C11 10.5 11.2 8.2 12 6.2Z"
)

_SIGN = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='#000' "
         "stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>")
# Original SVG masks (the colour comes from CSS): the emblem and one sign per callout kind.
ICONS = {
    "emblem": f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>"
              f"<path fill-rule='evenodd' d='{EMBLEM_PATH}'/></svg>",
    # Key threshold / Capability gate: a gauge at its mark
    "gauge": _SIGN + "<path d='M3.5 17.5a8.5 8.5 0 0 1 17 0'/><path d='M12 17.5l4.6-5.6'/>"
                     "<path d='M6.2 12.6l1.1.9M12 9v1.4M17.8 12.6l-1.1.9' stroke-width='1.6'/>"
                     "<circle cx='12' cy='17.5' r='1.7' fill='#000' stroke='none'/></svg>",
    # Dead end: the no-through-road sign
    "deadend": _SIGN + "<rect x='3.5' y='3.5' width='17' height='17' rx='3'/><path d='M12 19V10.5'/>"
                       "<path d='M7.5 8h9' stroke-width='3'/></svg>",
    # Jump: an arrow leaping a gap
    "jump": _SIGN + "<path d='M3 19.5h5M16 19.5h5'/><path d='M4.5 16C6 8.5 15 7 18.6 13.6'/>"
                    "<path d='M19.4 9.4l-.8 4.2-4.1-1.4'/></svg>",
    # Safety warning / doctrine: the warning triangle
    "warn": _SIGN + "<path d='M12 3.6L21.6 20H2.4Z'/><path d='M12 9.6v4.6'/>"
                    "<circle cx='12' cy='17.1' r='1.25' fill='#000' stroke='none'/></svg>",
    # Competence gate: a padlock
    "gate": _SIGN + "<rect x='4.5' y='10.5' width='15' height='10' rx='2'/>"
                    "<path d='M8 10.5V7.6a4 4 0 0 1 8 0v2.9'/><path d='M12 14.3v2.6'/></svg>",
    # Operational hazard: the hazard diamond
    "hazard": _SIGN + "<path d='M12 2.6L21.4 12L12 21.4L2.6 12Z'/><path d='M12 7.8v5.2'/>"
                      "<circle cx='12' cy='16.1' r='1.25' fill='#000' stroke='none'/></svg>",
    # Scope note / Planning marker: framing corners
    "scope": _SIGN + "<path d='M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5'/>"
                     "<circle cx='12' cy='12' r='1.9' fill='#000' stroke='none'/></svg>",
}


def svg_uri(svg):
    """SVG -> data: URI for a CSS url("..."): the markup uses single quotes, so the
    double-quoted url() needs only <, >, # and % escaped (quote() also takes spaces)."""
    return "data:image/svg+xml," + quote(svg, safe="=:/;,'.-()")


CSS = r"""/* Fire to Future: reader theme of the chapter pages (fire-to-future/*.html) and of the
   contents page (fire-to-future/index.html). Written by scripts/build_fire_to_future.py:
   edit the CSS constant there, never this file.

   "A field manual on the workshop bench." The page is the drafting paper and carbon
   ink of the book's own figures, set like its print edition: a Cambria-family serif,
   ochre spaced capitals, a steel rule under each chapter title. Each part carries an
   accent from the journey the title names, fire to future: ember (I Ignition), copper
   (II The Ancient Engine), brass (III The Acceleration), steel (IV The Modern Stack),
   blueprint blue (V Planetary Systems), gunmetal (the optional defense annex).
   Chapters open with a spec plate (era, difficulty on a heat gauge, what the chapter
   requires and unlocks); callouts keep the print edition's meaning and hue and gain a
   sign each. Dark mode is the workshop at night: the figures stay paper, pinned to the
   board, because their drawings are dark ink. The emblem (a cog around a flame) and
   the signs are original SVG masks. Every text colour passes WCAG AA (4.5:1) on its
   background in both schemes. */

:root {
  color-scheme: light dark;
  --reader-font-scale: 1;
  --measure: 40rem;
  --serif: Cambria, Charter, "Bitstream Charter", "Sitka Text", Georgia, "Noto Serif", serif;
  --mono: ui-monospace, "Cascadia Mono", Consolas, Menlo, "DejaVu Sans Mono", monospace;

  --page: #f4f0e6;
  --page-deep: #ebe4d5;
  --plate: #f9f6ee;
  --sheet: #fbf9f3;
  --sheet-edge: #b3a67f;
  --pre: #efe9dc;
  --rule: #d6cab2;
  --rule-strong: #a09479;
  --ink: #231e17;
  --ink-strong: #15120d;
  --muted: #675c4b;
  --ochre: #7a5c12;
  --link: #24497f;
  --bar: rgba(244, 240, 230, .92);
  --shadow: rgba(60, 44, 20, .16);
  --grid: rgba(122, 92, 18, .1);
  --heat-1: #b08a2e;
  --heat-2: #c96a2e;
  --heat-3: #9b3720;

  /* the parts, fire to future */
  --p1: #9b3720;
  --p2: #8f4f17;
  --p3: #7a5c12;
  --p4: #3e5870;
  --p5: #1f4f96;
  --annex: #52585e;
  --part: var(--ochre);
  --part-next: var(--ochre);

  /* callouts: the print edition's meaning and hue */
  --key: #2f5e33;     --key-bg: #e8f0e4;
  --dead: #8c3424;    --dead-bg: #f6e8e3;
  --jump: #284f86;    --jump-bg: #e7edf6;
  --warn: #a3241b;    --warn-bg: #fae9e4;
  --gate: #6e1f1a;    --gate-bg: #f3e3e0;
  --hazard: #76570e;  --hazard-bg: #f8eed6;
  --scope: #3e5870;   --scope-bg: #e8ecf1;

  /* the cover: a forge glowing under a blueprint sky, the same in both schemes */
  --cover-night: #0b1526;
  --cover-sky: #13223b;
  --cover-ember: #5a2414;
  --cover-ink: #f4ecdc;
  --cover-soft: #d9cdb6;
  --cover-brass: #e2be6c;
  --cover-brass-hover: #ecce88;
  --cover-on-brass: #1a140c;
  --cover-grid: rgba(150, 180, 230, .09);
  --spectrum: linear-gradient(90deg, #c4532f 0 16.67%, #c97a35 0 33.33%, #cfa244 0 50%,
              #7c98b3 0 66.67%, #4f86d6 0 83.33%, #8b9096 0);

  --emblem: url("@ICON:emblem@");
  --ico-key: url("@ICON:gauge@");
  --ico-dead: url("@ICON:deadend@");
  --ico-jump: url("@ICON:jump@");
  --ico-warn: url("@ICON:warn@");
  --ico-gate: url("@ICON:gate@");
  --ico-hazard: url("@ICON:hazard@");
  --ico-scope: url("@ICON:scope@");
}
@media (prefers-color-scheme: dark) {
  :root {
    --page: #15130f;
    --page-deep: #1f1b15;
    --plate: #1b1813;
    --sheet-edge: #6b604f;
    --pre: #1c1914;
    --rule: #3a332a;
    --rule-strong: #6b604f;
    --ink: #e4dccd;
    --ink-strong: #f3ecdf;
    --muted: #aa9e8a;
    --ochre: #d4b05a;
    --link: #93b7ee;
    --bar: rgba(21, 19, 15, .9);
    --shadow: rgba(0, 0, 0, .55);
    --grid: rgba(212, 176, 90, .08);
    --heat-1: #b38b33;
    --heat-2: #d9783a;
    --heat-3: #e0573a;
    --p1: #f08b6c;
    --p2: #e8a062;
    --p3: #d8b45e;
    --p4: #a3bcd3;
    --p5: #8fb5f2;
    --annex: #bab7b0;
    --key: #95cb8f;     --key-bg: #16231a;
    --dead: #f0957d;    --dead-bg: #2a1814;
    --jump: #94b8f0;    --jump-bg: #142034;
    --warn: #ff9182;    --warn-bg: #2e1512;
    --gate: #ffa196;    --gate-bg: #311414;
    --hazard: #e4c066;  --hazard-bg: #29210f;
    --scope: #aac1d7;   --scope-bg: #18212c;
  }
}
[data-part="p1"] { --part: var(--p1); --part-next: var(--p2); }
[data-part="p2"] { --part: var(--p2); --part-next: var(--p3); }
[data-part="p3"] { --part: var(--p3); --part-next: var(--p4); }
[data-part="p4"] { --part: var(--p4); --part-next: var(--p5); }
[data-part="p5"] { --part: var(--p5); --part-next: var(--p5); }
[data-part="annex"] { --part: var(--annex); --part-next: var(--annex); }

/* ---------- base ---------- */
*, *::before, *::after { box-sizing: border-box; }
[hidden] { display: none !important; }
html { font-size: 100%; -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
@media (prefers-reduced-motion: no-preference) {
  html { scroll-behavior: smooth; }
  /* cross-fade between chapters (and to the contents) */
  @view-transition { navigation: auto; }
}
body {
  margin: 0;
  background: var(--page);
  color: var(--ink);
  font-family: var(--serif);
  font-size: 1rem;
  line-height: 1.5;
  font-kerning: normal;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
a {
  color: var(--link);
  text-decoration-line: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: .18em;
  text-decoration-color: color-mix(in srgb, var(--link) 40%, transparent);
}
a:hover { text-decoration-color: currentColor; }
a:focus-visible, button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--link) 65%, transparent);
  outline-offset: 3px;
  border-radius: 3px;
}
button { margin: 0; font: inherit; }
strong, b { font-weight: 700; }
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}
.skip-link {
  position: absolute;
  left: 1rem;
  top: -4rem;
  z-index: 40;
  padding: .55rem 1rem;
  border-radius: .4rem;
  background: var(--ink-strong);
  color: var(--page);
  text-decoration: none;
}
.skip-link:focus { top: .5rem; }

/* ---------- top bar ---------- */
.reader-top-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .75rem;
  min-height: 3rem;
  padding: .35rem 1.25rem;
  background: var(--bar);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--rule);
}
.reader-book, .reader-back {
  display: inline-flex;
  align-items: center;
  gap: .55rem;
  min-height: 2.25rem;
  color: var(--ink-strong);
  font-size: .78rem;
  letter-spacing: .16em;
  text-transform: uppercase;
  text-decoration: none;
  white-space: nowrap;
}
.reader-book::before {
  content: "";
  flex: none;
  width: 1.3rem;
  height: 1.3rem;
  background: var(--part);
  -webkit-mask: var(--emblem) center / contain no-repeat;
  mask: var(--emblem) center / contain no-repeat;
}
.reader-book:hover, .reader-back:hover { text-decoration: underline; text-underline-offset: .25em; }
.reader-progress {
  color: var(--muted);
  font-size: .82rem;
  letter-spacing: .04em;
  font-variant-numeric: lining-nums tabular-nums;
  white-space: nowrap;
}
.reader-font-controls { display: flex; gap: .35rem; }
.font-btn {
  min-width: 2.75rem;
  min-height: 2.25rem;
  padding: .25rem .5rem;
  border: 1px solid var(--rule);
  border-radius: .35rem;
  background: transparent;
  color: var(--ink);
  font-family: var(--serif);
  font-size: .9rem;
  line-height: 1;
  cursor: pointer;
  transition: background-color .15s, border-color .15s;
}
.font-btn:hover { border-color: var(--part); background: var(--page-deep); color: var(--ink-strong); }
/* reading progress: a thread from this part's colour toward the next one (scroll-driven, no script) */
@supports (animation-timeline: scroll()) {
  .reader-top-bar::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: -1px;
    height: 3px;
    background: linear-gradient(90deg, var(--part), var(--part-next));
    transform-origin: 0 50%;
    transform: scaleX(0);
    animation: ftf-progress linear both;
    animation-timeline: scroll(root block);
  }
  @keyframes ftf-progress { to { transform: scaleX(1); } }
  .cover-top::after { display: none; }
}

/* ---------- the chapter ---------- */
.reader-content {
  max-width: calc(var(--measure) + 2.5rem);
  margin: 0 auto;
  padding: 2.75rem 1.25rem 2.5rem;
  font-size: calc(1.125rem * var(--reader-font-scale));
  line-height: 1.68;
}
.reader-content p { margin: 0 0 .95em; text-wrap: pretty; -webkit-hyphens: auto; hyphens: auto; }

/* part, chapter number, title, and the steel rule under them */
.reader-content .part-kicker {
  display: flex;
  align-items: center;
  gap: .75rem;
  margin: 0 0 1.4rem;
  font-size: .72em;
  letter-spacing: .26em;
  line-height: 1.4;
  text-transform: uppercase;
  color: var(--part);
  font-variant-numeric: lining-nums;
}
.part-kicker::before {
  content: "";
  flex: none;
  width: 2.4rem;
  height: .3rem;
  border-radius: 1px;
  background: linear-gradient(90deg, var(--part), var(--part-next));
}
.reader-content h1 {
  margin: 0 0 1.75rem;
  padding-bottom: 1.35rem;
  font-size: 2.05em;
  font-weight: 700;
  line-height: 1.16;
  letter-spacing: -.005em;
  color: var(--ink-strong);
  text-wrap: balance;
  -webkit-hyphens: manual;
  hyphens: manual;
  background:
    linear-gradient(var(--ink-strong), var(--ink-strong)) left bottom 8px / 100% 2px no-repeat,
    repeating-linear-gradient(90deg, var(--ink-strong) 0 1px, transparent 1px 10px) left bottom 3px / 100% 5px no-repeat,
    repeating-linear-gradient(90deg, var(--ink-strong) 0 1.5px, transparent 1.5px 50px) left bottom / 100% 8px no-repeat;
}
.chapter-kicker {
  display: block;
  margin-bottom: .55rem;
  font-size: .4em;
  font-weight: 400;
  line-height: 1.3;
  letter-spacing: .24em;
  text-transform: uppercase;
  color: var(--ochre);
  font-variant-numeric: lining-nums;
}

/* the spec plate: era, difficulty, requires, unlocks */
.spec {
  margin: 0 0 2.2rem;
  padding: .85rem 1.35rem .9rem;
  border: 1px solid var(--rule-strong);
  border-radius: .3rem;
  background:
    radial-gradient(circle at .6rem .6rem, var(--rule-strong) 0 2px, transparent 2.6px),
    radial-gradient(circle at calc(100% - .6rem) .6rem, var(--rule-strong) 0 2px, transparent 2.6px),
    radial-gradient(circle at .6rem calc(100% - .6rem), var(--rule-strong) 0 2px, transparent 2.6px),
    radial-gradient(circle at calc(100% - .6rem) calc(100% - .6rem), var(--rule-strong) 0 2px, transparent 2.6px),
    var(--plate);
  box-shadow: inset 0 0 0 4px var(--plate), inset 0 0 0 5px var(--rule);
  font-size: .9em;
  line-height: 1.5;
}
.spec > div {
  display: grid;
  grid-template-columns: 6.8rem minmax(0, 1fr);
  column-gap: 1rem;
  padding: .4rem 0;
}
.spec > div + div { border-top: 1px dashed var(--rule); }
.spec dt {
  padding-top: .22em;
  font-size: .74em;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--ochre);
}
.spec dd { margin: 0; }
.gauge {
  --lvl: 0;
  display: inline-block;
  width: 5.4em;
  height: .62em;
  margin-right: .65em;
  vertical-align: .02em;
  background:
    linear-gradient(90deg, transparent calc(var(--lvl) * 100% / 6), var(--rule) 0),
    linear-gradient(90deg, var(--heat-1), var(--heat-2) 55%, var(--heat-3));
  -webkit-mask: repeating-linear-gradient(90deg, #000 0 calc(100% / 6 - 2px), transparent 0 calc(100% / 6));
  mask: repeating-linear-gradient(90deg, #000 0 calc(100% / 6 - 2px), transparent 0 calc(100% / 6));
}
.gauge[data-level="1"] { --lvl: 1; }
.gauge[data-level="2"] { --lvl: 2; }
.gauge[data-level="3"] { --lvl: 3; }
.gauge[data-level="4"] { --lvl: 4; }
.gauge[data-level="5"] { --lvl: 5; }
.gauge[data-level="6"] { --lvl: 6; }
.reader-content .chips { display: flex; flex-wrap: wrap; gap: .4rem; margin: .1rem 0 0; padding: 0; list-style: none; }
.reader-content .chips li { margin: 0; padding: 0; }
.chips a {
  display: inline-block;
  padding: .02rem .5rem .06rem;
  border: 1px solid color-mix(in srgb, var(--link) 35%, transparent);
  border-radius: .3rem;
  background: var(--page);
  font-variant-numeric: lining-nums tabular-nums;
  text-decoration: none;
  white-space: nowrap;
  transition: border-color .15s, background-color .15s;
}
.chips a:hover { border-color: var(--link); background: var(--page-deep); }

/* sections */
.reader-content h2 {
  margin: 2.3em 0 .75em;
  font-size: 1.3em;
  font-weight: 700;
  line-height: 1.3;
  color: var(--ink-strong);
  text-wrap: balance;
  -webkit-hyphens: manual;
  hyphens: manual;
  scroll-margin-top: 4.5rem;
}
.sec-num {
  margin-right: .3em;
  color: var(--part);
  font-variant-numeric: lining-nums tabular-nums;
}
.reader-content h3 {
  margin: 1.8em 0 .6em;
  font-size: 1.08em;
  font-weight: 700;
  line-height: 1.35;
  color: var(--ink-strong);
  scroll-margin-top: 4.5rem;
}
.reader-content :is(ul, ol) { margin: 0 0 1.1em; padding-left: 1.45em; }
.reader-content li { margin: .3em 0; padding-left: .2em; }
.reader-content ul > li::marker { color: var(--part); }
.reader-content ol > li::marker { color: var(--ochre); font-weight: 700; font-variant-numeric: lining-nums; }
.reader-content :is(li, td, th) > p:last-child { margin-bottom: 0; }

/* callouts: Key threshold, Dead end, Jump, Safety warning, Competence gate, Operational hazard, Scope note */
.reader-content .co {
  --co: var(--ochre);
  --co-bg: var(--page-deep);
  position: relative;
  margin: 1.35em 0;
  padding: .8rem 1.05rem .85rem 3.05rem;
  border-left: 3px solid var(--co);
  border-radius: 0 .4rem .4rem 0;
  background: var(--co-bg);
  font-size: .95em;
  line-height: 1.6;
  -webkit-hyphens: manual;
  hyphens: manual;
}
.reader-content .co::before {
  content: "";
  position: absolute;
  left: .9rem;
  top: .92rem;
  width: 1.35rem;
  height: 1.35rem;
  background: var(--co);
  -webkit-mask: var(--co-icon) center / contain no-repeat;
  mask: var(--co-icon) center / contain no-repeat;
}
.reader-content .co > strong:first-child {
  font-variant-caps: all-small-caps;
  letter-spacing: .07em;
  font-size: 1.08em;
  color: var(--co);
}
.reader-content .co-key { --co: var(--key); --co-bg: var(--key-bg); --co-icon: var(--ico-key); }
.reader-content .co-dead { --co: var(--dead); --co-bg: var(--dead-bg); --co-icon: var(--ico-dead); }
.reader-content .co-jump { --co: var(--jump); --co-bg: var(--jump-bg); --co-icon: var(--ico-jump); }
.reader-content .co-warn { --co: var(--warn); --co-bg: var(--warn-bg); --co-icon: var(--ico-warn); border-left-width: 5px; }
.reader-content .co-gate {
  --co: var(--gate);
  --co-bg: var(--gate-bg);
  --co-icon: var(--ico-gate);
  border-left-width: 6px;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--gate) 35%, transparent);
}
.reader-content .co-hazard { --co: var(--hazard); --co-bg: var(--hazard-bg); --co-icon: var(--ico-hazard); border-left-width: 5px; }
.reader-content .co-scope { --co: var(--scope); --co-bg: var(--scope-bg); --co-icon: var(--ico-scope); }

/* figures: drawing sheets on the bench (their SVG is dark ink on its own paper) */
.reader-content figure.fig {
  margin: 1.6em 0;
  padding: .85rem .95rem .75rem;
  border: 1px solid var(--sheet-edge);
  border-radius: 2px;
  background: var(--sheet);
  box-shadow: 0 1px 2px var(--shadow), 0 12px 26px -18px var(--shadow);
  color: #16130e;
  text-align: center;
}
.reader-content figure.fig svg { display: block; max-width: 100%; height: auto; margin: 0 auto; }
.reader-content figure.fig svg.wide { width: 100%; }
/* the print edition's figure type; haloed labels paint their stroke under the fill */
.reader-content figure.fig svg text { font-family: Cambria, Georgia, serif; paint-order: stroke; }
.reader-content figure.fig figcaption {
  margin-top: .55rem;
  font-size: .82em;
  font-style: italic;
  line-height: 1.45;
  color: #4a4436;
  -webkit-hyphens: manual;
  hyphens: manual;
}
.reader-content figure.fig figcaption strong { font-style: normal; }
@media (prefers-color-scheme: dark) {
  /* paper under a work lamp, not a light box */
  .reader-content figure.fig { filter: brightness(.88); }
}

/* tables: data sheets */
.table-wrap { margin: 1.4em 0 1.7em; overflow-x: auto; }
.reader-content table {
  width: 100%;
  border-collapse: collapse;
  font-size: .84em;
  line-height: 1.5;
  font-variant-numeric: lining-nums tabular-nums;
}
.reader-content th {
  padding: .5rem .65rem;
  border-bottom: 2px solid var(--ink-strong);
  background: var(--page-deep);
  font-weight: 700;
  text-align: left;
  vertical-align: bottom;
  color: var(--ink-strong);
}
.reader-content td { padding: .5rem .65rem; border-bottom: 1px solid var(--rule); vertical-align: top; }
.reader-content tbody tr:nth-child(even) td { background: color-mix(in srgb, var(--page-deep) 45%, transparent); }

/* code and diagrams, on graph paper */
.reader-content code {
  padding: .1em .32em;
  border-radius: .25rem;
  background: var(--page-deep);
  font-family: var(--mono);
  font-size: .84em;
}
.reader-content pre {
  margin: 1.4em 0;
  padding: 1rem 1.15rem;
  overflow-x: auto;
  border: 1px solid var(--rule);
  border-radius: .3rem;
  background-color: var(--pre);
  background-image:
    linear-gradient(var(--grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid) 1px, transparent 1px);
  background-size: 1.25rem 1.25rem;
  line-height: 1.45;
}
.reader-content pre code { padding: 0; background: none; font-size: .8em; }

/* quotations, and the summary that opens each appendix */
.reader-content blockquote {
  margin: 1.4em 0;
  padding: .9rem 1.15rem;
  border-left: 3px solid var(--ochre);
  border-radius: 0 .4rem .4rem 0;
  background: color-mix(in srgb, var(--page-deep) 70%, transparent);
  font-size: .95em;
  line-height: 1.6;
}
.reader-content blockquote p { margin: 0 0 .55em; }
.reader-content blockquote p:last-child { margin-bottom: 0; }
.reader-content blockquote.meta {
  margin: 0 0 2.2rem;
  border: 1px solid var(--rule-strong);
  border-left: 4px solid var(--part);
  background: var(--plate);
  font-size: 1em;
}
.reader-content hr {
  width: 8rem;
  height: 8px;
  margin: 2.2em auto;
  border: 0;
  background:
    linear-gradient(var(--rule-strong), var(--rule-strong)) top / 100% 2px no-repeat,
    repeating-linear-gradient(90deg, var(--rule-strong) 0 1px, transparent 1px 8px) bottom / 100% 6px no-repeat;
}
/* end of the chapter: the emblem */
.reader-content::after {
  content: "";
  display: block;
  width: 1.6rem;
  height: 1.6rem;
  margin: 2.4em auto 0;
  background: var(--part);
  -webkit-mask: var(--emblem) center / contain no-repeat;
  mask: var(--emblem) center / contain no-repeat;
}

/* the front matter opens like the print title page */
[data-part="front"] .part-kicker { justify-content: center; }
[data-part="front"] .part-kicker::before { display: none; }
[data-part="front"] .reader-content h1 {
  margin-bottom: .6rem;
  padding: 0 0 0 .14em;
  font-size: 2.5em;
  letter-spacing: .14em;
  text-align: center;
  background: none;
}
[data-part="front"] .reader-content h1 + h3 {
  max-width: 30rem;
  margin: 0 auto 1.6rem;
  font-size: 1.12em;
  font-style: italic;
  font-weight: 400;
  line-height: 1.5;
  text-align: center;
  color: var(--muted);
}

/* ---------- previous / next ---------- */
.reader-pager {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: stretch;
  gap: 1rem 1.25rem;
  max-width: calc(var(--measure) + 2.5rem);
  margin: 0 auto;
  padding: 1.75rem 1.25rem 1.5rem;
  border-top: 1px solid var(--rule);
}
.reader-pager a { text-decoration: none; }
.pager-prev, .pager-next {
  display: block;
  padding: .7rem .95rem;
  border: 1px solid var(--rule);
  border-radius: .45rem;
  transition: border-color .15s, background-color .15s;
}
.pager-prev:hover, .pager-next:hover { border-color: var(--part); background: color-mix(in srgb, var(--page-deep) 65%, transparent); }
.pager-next { text-align: right; }
.pager-dir {
  display: block;
  font-size: .7rem;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--ochre);
  font-variant-numeric: lining-nums;
}
.pager-title { display: block; margin-top: .25rem; font-size: 1rem; line-height: 1.3; color: var(--link); }
.pager-toc {
  align-self: center;
  font-size: .76rem;
  letter-spacing: .18em;
  text-transform: uppercase;
  color: var(--muted);
}
.pager-toc:hover { color: var(--link); }
.pager-empty { visibility: hidden; }

.reader-footnote {
  max-width: calc(var(--measure) + 2.5rem);
  margin: 0 auto;
  padding: .5rem 1.25rem 2.75rem;
  text-align: center;
  font-size: .78rem;
  line-height: 1.6;
  letter-spacing: .03em;
  color: var(--muted);
}
.reader-footnote a { color: var(--muted); }
.reader-footnote a:hover { color: var(--link); }

/* ---------- contents page (fire-to-future/index.html) ---------- */
.cover-top {
  position: relative;
  border-bottom: 0;
  background: var(--cover-night);
  -webkit-backdrop-filter: none;
  backdrop-filter: none;
}
.cover-top .reader-back { color: var(--cover-ink); }
.cover {
  position: relative;
  isolation: isolate;
  padding: 3.25rem 1.25rem 4.1rem;
  overflow: hidden;
  background:
    radial-gradient(ellipse 55% 42% at 50% 108%, rgba(214, 104, 44, .5), transparent 72%),
    radial-gradient(ellipse 95% 70% at 50% 112%, var(--cover-ember), transparent 75%),
    linear-gradient(180deg, var(--cover-night) 0%, var(--cover-sky) 58%, #1f1922 100%);
  color: var(--cover-ink);
  text-align: center;
}
/* the blueprint grid of the future, fading into the fire */
.cover::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    linear-gradient(var(--cover-grid) 1px, transparent 1px) center top / 1.5rem 1.5rem,
    linear-gradient(90deg, var(--cover-grid) 1px, transparent 1px) center top / 1.5rem 1.5rem;
  -webkit-mask: linear-gradient(#000 20%, transparent 85%);
  mask: linear-gradient(#000 20%, transparent 85%);
}
/* the six parts as one spectrum, fire to future */
.cover::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 6px;
  background: var(--spectrum);
}
.cover-inner { position: relative; max-width: 40rem; margin: 0 auto; }
.cover-emblem { display: block; width: 4.6rem; height: 4.6rem; margin: 0 auto 1.35rem; fill: var(--cover-brass); }
.cover-kicker {
  margin: 0 0 1.15rem;
  font-size: .76rem;
  letter-spacing: .4em;
  line-height: 1.6;
  text-transform: uppercase;
  color: var(--cover-brass);
}
.cover h1 {
  margin: 0;
  padding-left: .14em;
  font-size: clamp(2.25rem, 8.5vw, 4.1rem);
  font-weight: 700;
  line-height: 1.06;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--cover-ink);
  text-wrap: balance;
  text-shadow: 0 2px 18px rgba(0, 0, 0, .35);
}
.cover h1::after {
  content: "";
  display: block;
  width: 10rem;
  height: 9px;
  margin: 1.35rem auto 1.25rem;
  background:
    linear-gradient(var(--cover-brass), var(--cover-brass)) top / 100% 2px no-repeat,
    repeating-linear-gradient(90deg, var(--cover-brass) 0 1px, transparent 1px 10px) left bottom 1px / 100% 5px no-repeat,
    repeating-linear-gradient(90deg, var(--cover-brass) 0 1.5px, transparent 1.5px 40px) left bottom / 100% 7px no-repeat;
}
.cover-sub {
  max-width: 30rem;
  margin: 0 auto;
  font-size: 1.15rem;
  font-style: italic;
  line-height: 1.5;
  color: var(--cover-soft);
  text-wrap: balance;
}
.cover-facts {
  margin: 1.35rem 0 0;
  font-size: .74rem;
  letter-spacing: .2em;
  line-height: 1.7;
  text-transform: uppercase;
  color: var(--cover-soft);
  font-variant-numeric: lining-nums;
}
.cover-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: .75rem; margin: 1.85rem 0 0; }
.btn-begin, .btn-pdf {
  display: inline-block;
  padding: .72rem 1.45rem;
  border-radius: 999px;
  font-size: .84rem;
  letter-spacing: .14em;
  text-decoration: none;
  text-transform: uppercase;
  transition: background-color .15s, border-color .15s;
}
.btn-begin { background: var(--cover-brass); color: var(--cover-on-brass); }
.btn-begin:hover { background: var(--cover-brass-hover); }
.btn-pdf { border: 1px solid color-mix(in srgb, var(--cover-ink) 55%, transparent); background: rgba(11, 21, 38, .55); color: var(--cover-ink); }
.btn-pdf:hover { border-color: var(--cover-ink); background: rgba(11, 21, 38, .8); }
.cover :focus-visible { outline-color: var(--cover-ink); }

.contents {
  max-width: calc(var(--measure) + 2.5rem);
  margin: 0 auto;
  padding: 2.4rem 1.25rem 1.5rem;
}
.cover-about {
  padding: 1rem 1.25rem;
  border: 1px solid var(--rule);
  border-radius: .45rem;
  background: var(--plate);
  font-size: .95rem;
  line-height: 1.6;
}
.cover-about p { margin: 0; }
.cover-about p + p { margin-top: .55rem; }
.cover-about strong { color: var(--ink-strong); }
.contents-title {
  margin: 2.7rem 0 1.15rem;
  font-size: .85rem;
  font-weight: 400;
  letter-spacing: .3em;
  text-transform: uppercase;
  text-align: center;
  color: var(--ochre);
}
.contents-title::after {
  content: "";
  display: block;
  width: 8rem;
  height: 8px;
  margin: .7rem auto 0;
  background:
    linear-gradient(var(--rule-strong), var(--rule-strong)) top / 100% 2px no-repeat,
    repeating-linear-gradient(90deg, var(--rule-strong) 0 1px, transparent 1px 8px) bottom / 100% 6px no-repeat;
}
.toc-search {
  display: block;
  width: 100%;
  margin: 0 0 .5rem;
  padding: .75rem 1rem;
  border: 1px solid color-mix(in srgb, var(--muted) 75%, var(--page));
  border-radius: .45rem;
  background: var(--plate);
  color: var(--ink);
  font: inherit;
  font-size: 1rem;
  transition: border-color .15s, box-shadow .15s;
}
.toc-search::placeholder { color: var(--muted); opacity: 1; }
.toc-search:focus { outline: none; border-color: var(--link); box-shadow: 0 0 0 3px color-mix(in srgb, var(--link) 25%, transparent); }
.toc-group { margin-top: 2rem; }
.toc-group-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  column-gap: .75rem;
  margin: 0;
  padding-bottom: .45rem;
  border-bottom: 3px solid var(--part);
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1.3;
  color: var(--ink-strong);
}
.toc-group-label {
  font-size: .56em;
  font-weight: 400;
  letter-spacing: .24em;
  text-transform: uppercase;
  color: var(--part);
}
.toc-group-desc { margin: .45rem 0 .2rem; font-size: .9rem; font-style: italic; line-height: 1.5; color: var(--muted); }
.toc-rows { margin: 0; padding: 0; list-style: none; }
.toc-row {
  display: grid;
  grid-template-columns: 2.3rem minmax(0, 1fr) auto;
  align-items: baseline;
  column-gap: .85rem;
  padding: .55rem .5rem;
  border-bottom: 1px solid color-mix(in srgb, var(--rule) 75%, transparent);
  color: var(--ink);
  text-decoration: none;
}
.toc-row:hover { background: var(--page-deep); }
.toc-row:hover .toc-title { color: var(--link); text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: .18em; }
.toc-num {
  text-align: right;
  font-size: .9rem;
  color: var(--part);
  font-variant-numeric: lining-nums tabular-nums;
}
.toc-title { font-size: 1.02rem; line-height: 1.35; }
.toc-time { font-size: .76rem; color: var(--muted); white-space: nowrap; font-variant-numeric: lining-nums tabular-nums; }
.toc-empty { margin: 0; padding: 2.5rem 0; text-align: center; font-style: italic; color: var(--muted); }
.toc-foot { padding: 1.25rem 1.25rem 2.75rem; text-align: center; font-size: .82rem; color: var(--muted); }
.toc-foot a { color: var(--muted); }
.toc-foot a:hover { color: var(--link); }

/* ---------- phones ---------- */
@media (max-width: 36rem) {
  .reader-top-bar { gap: .5rem; padding: .3rem .75rem; }
  .reader-book { gap: .4rem; font-size: .7rem; letter-spacing: .12em; }
  .reader-book::before { width: 1.15rem; height: 1.15rem; }
  .reader-progress { font-size: .74rem; letter-spacing: 0; }
  .font-btn { min-width: 2.5rem; }
  .reader-content {
    padding: 2rem 1rem;
    font-size: calc(1.0625rem * var(--reader-font-scale));
    line-height: 1.65;
  }
  .reader-content h1 { font-size: 1.75em; }
  [data-part="front"] .reader-content h1 { font-size: 1.9em; letter-spacing: .1em; }
  .spec { padding: .75rem 1rem .8rem; }
  .spec > div { display: block; }
  .spec dt { padding-top: 0; }
  .reader-content .co { padding: .75rem .9rem .8rem 2.65rem; }
  .reader-content .co::before { left: .75rem; top: .85rem; width: 1.2rem; height: 1.2rem; }
  .reader-content figure.fig { margin-inline: -.35rem; padding: .6rem .5rem .55rem; }
  .reader-pager { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: .75rem; padding-inline: 1rem; }
  .pager-toc { grid-column: 1 / -1; grid-row: 2; justify-self: center; }
  .cover { padding: 2.6rem 1rem 3.3rem; }
  .cover-kicker { letter-spacing: .28em; }
  .contents { padding-inline: 1rem; }
  .toc-row { grid-template-columns: 1.9rem minmax(0, 1fr) auto; column-gap: .6rem; padding-inline: .25rem; }
}
@media (max-width: 22rem) {
  .reader-progress { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
}

@media print {
  .reader-top-bar, .reader-pager, .skip-link, .toc-search, .cover-actions { display: none !important; }
  body { background: #fff; color: #000; }
  .reader-content { max-width: none; padding: 0; font-size: 11pt; }
  .reader-content figure.fig { filter: none; box-shadow: none; }
  .reader-content :is(.co, .spec, figure.fig, pre) { break-inside: avoid; }
  a { color: inherit; }
}
"""


def css_text():
    """The stylesheet with its SVG masks filled in."""
    return re.sub(r"@ICON:([a-z]+)@", lambda m: svg_uri(ICONS[m.group(1)]), CSS.lstrip("\n"))


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'; connect-src 'self'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f4f0e6" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#15130f" media="(prefers-color-scheme: dark)">
<title>@TITLE@</title>
<meta name="description" content="@DESC@">
<link rel="canonical" href="https://infuscy.github.io/fire-to-future/@FILE@">
<link rel="icon" href="/img/profile.png">
<link rel="stylesheet" href="/fire-to-future/reader.css">
@REL@</head>
<body data-part="@PART@">
<a class="skip-link" href="#text">Skip to the text</a>
<header class="reader-top-bar">
  <a class="reader-book" href="/fire-to-future/">Fire to Future</a>
  <span class="reader-progress">@PROGRESS@</span>
  <span class="reader-font-controls"><button class="font-btn" id="fontDown" type="button" title="Smaller text" aria-label="Decrease font size">A−</button><button class="font-btn" id="fontUp" type="button" title="Larger text" aria-label="Increase font size">A+</button></span>
</header>
<main id="text" class="reader-content">
@BODY@
</main>
<nav class="reader-pager" aria-label="Chapters">
@PREV@
  <a class="pager-toc" href="/fire-to-future/">Contents</a>
@NEXT@
</nav>
<p class="reader-footnote">FIRE TO FUTURE — A Field Manual for Rebuilding Technology · <a href="/fire-to-future/Fire-To-Future.pdf">Download the PDF</a> (@PDFSIZE@)</p>
<script src="/js/reader-font.js"></script>
</body>
</html>
"""


def esc_attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def head_markup(body, kicker):
    """Set the page's first heading as the print edition does: the part above it, the
    chapter (or appendix) number as a kicker inside it, the title on its own line. A
    visually hidden ':' or ' —' keeps the heading's accessible name as written."""
    def repl(m):
        hid, text = m.group(1), m.group(2)
        mm = re.match(r"(Chapter \d+|Appendix [A-G])\s*(:|—)\s*(.+)$", text, re.S)
        if mm:
            sep = ":" if mm.group(2) == ":" else " —"
            text = (f'<span class="chapter-kicker">{mm.group(1)}<span class="visually-hidden">{sep}</span>'
                    f'</span> {mm.group(3)}')
        return f'<p class="part-kicker">{kicker}</p>\n<h1 id="{hid}">{text}</h1>'
    return re.sub(r'<h1 id="([^"]+)">(.*?)</h1>', repl, body, count=1, flags=re.S)


def spec_plate(body, titles):
    """A chapter's metadata blockquote (Era span · Difficulty / Requires / Unlocks /
    Data snapshot / Annex status) -> a definition list set as a spec plate: the
    difficulty gets a heat gauge, link-only Requires/Unlocks become chips titled with
    the chapter names. The text is unchanged. Appendices' summaries (no labels) and any
    block of an unexpected shape are left as they are."""
    m = re.search(r'<blockquote class="meta">\s*<p>(.*?)</p>\s*</blockquote>', body, re.S)
    if not m or not m.group(1).lstrip().startswith("<strong>"):
        return body
    rows = []
    for part in re.split(r"<br\s*/?>|\s+·\s+(?=<strong>)", m.group(1)):
        lm = re.match(r"\s*<strong>([^<]+?):</strong>\s*(.*)$", part, re.S)
        if not lm:
            return body
        label, value = lm.group(1), lm.group(2).strip()
        if label == "Difficulty" and value in DIFFICULTY:
            value = f'<span class="gauge" data-level="{DIFFICULTY[value]}" aria-hidden="true"></span>{value}'
        elif label in ("Requires", "Unlocks"):
            links = re.findall(r'<a href="([^"#]+)">([^<]+)</a>', value)
            rest = re.sub(r'<a href="[^"]+">[^<]+</a>', "L", value)
            if links and re.fullmatch(r"L(, L)*", rest):
                value = '<ul class="chips">' + "".join(
                    f'<li><a href="{href}"'
                    + (f' title="{esc_attr(titles[href])}"' if href in titles else "")
                    + f'>{text}</a></li>' for href, text in links) + "</ul>"
        cls = re.sub(r"[^a-z]+", "-", label.lower()).strip("-")
        rows.append(f'<div class="spec-{cls}"><dt>{label}</dt><dd>{value}</dd></div>')
    return body[:m.start()] + '<dl class="spec">\n' + "\n".join(rows) + "\n</dl>" + body[m.end():]


def number_sections(body):
    """'1.1 Ignition by Friction', 'A.2 …', '6. …': the section number in its own span."""
    return re.sub(r'(<h2 id="[^"]+">)(\d+\.\d+[a-z]?|[A-G]\.\d+|\d+\.)\s+',
                  r'\1<span class="sec-num">\2</span> ', body)


def reading_minutes(body):
    """Reading time of a page: its text without the figures' SVG markup."""
    text = re.sub(r"<svg\b.*?</svg>", " ", body, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return max(1, round(len(re.findall(r"\S+", text)) / WORDS_PER_MINUTE))


def pager_link(cls, rel, href, direction, title):
    return (f'  <a class="{cls}" href="{href}" rel="{rel}"><span class="pager-dir">{direction}</span>'
            f'<span class="pager-title">{title}</span></a>')


def page_description(body, limit=160):
    """Plain-text summary for <meta name="description">: the first prose
    paragraph of the page (not the era/requires metadata, figures or callouts),
    cut at a word boundary."""
    for m in re.finditer(r"<p>(.*?)</p>", body, re.S):
        before = body[:m.start()]
        # skip paragraphs inside blockquotes, figures and callout boxes
        if before.count("<blockquote") > before.count("</blockquote>"):
            continue
        if before.count("<figure") > before.count("</figure>"):
            continue
        if re.search(r'<div class="co[^"]*">[^<]*$', before):
            continue
        text = re.sub(r"<[^>]+>", "", m.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'"))
        if len(text) < 60:
            continue
        if len(text) > limit:
            text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"
        return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    return "FIRE TO FUTURE — A Field Manual for Rebuilding Technology."


def render_page(title, desc, progress, part, rel_links, prev, next_, body, file_name, pdf_size):
    # the body goes in last, so nothing in the book's text is taken for a placeholder
    return (TEMPLATE
            .replace("@TITLE@", title)
            .replace("@DESC@", desc)
            .replace("@FILE@", file_name)
            .replace("@PROGRESS@", progress)
            .replace("@PART@", part)
            .replace("@REL@", rel_links)
            .replace("@PDFSIZE@", pdf_size)
            .replace("@PREV@", prev)
            .replace("@NEXT@", next_)
            .replace("@BODY@", body))


def esc_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------------- build

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC, help="path of the Apocalypse repo")
    args = ap.parse_args()

    book_dir = os.path.join(args.src, "book")
    src_pdf = os.path.join(args.src, "Fire-To-Future.pdf")
    for p in (book_dir, src_pdf):
        if not os.path.exists(p):
            sys.stderr.write(f"ERROR: missing {p}\n")
            return 1

    # ---- sequence: (key, rel, part_label_or_None, type, num_label) ----
    seq = []
    seq.append(("00_front_matter", FRONT_MATTER, None, "front", ""))
    for part_label, _part_name, _part_desc, files in PARTS:
        for rel in files:
            key = os.path.splitext(os.path.basename(rel))[0]
            num = int(re.match(r"ch(\d+)", key).group(1))
            seq.append((key, rel, part_label, "chapter", str(num)))
    for rel in APPENDICES:
        key = os.path.splitext(os.path.basename(rel))[0]
        letter = key.split("_")[1]
        seq.append((key, rel, "Appendices", "appendix", letter))
    for rel in REFERENCE_NOTES:
        key = os.path.splitext(os.path.basename(rel))[0]
        seq.append((key, rel, "Reference note", "reference", ""))

    n_chapters = sum(1 for s in seq if s[3] == "chapter")
    n_appendices = sum(1 for s in seq if s[3] == "appendix")

    gen = Converter(book_dir)
    pages = []  # (filename, {..}) in sequence order
    data_entries = []
    total_words = 0
    pdf_size = f"{os.path.getsize(src_pdf) / 1e6:.1f} MB"
    part_names = {pl: pn for pl, pn, _pd, _fs in PARTS}

    # ---- first pass: titles and labels of every page (the pager and the chips name them) ----
    entries = []
    for key, rel, part_label, kind, num_label in seq:
        src_text = read(os.path.join(book_dir, rel))
        title, label = split_h1(src_text)

        if kind == "front":
            display_title = "Introduction — What This Guide Is"
            progress = "Front matter"
            label = "Front matter"
            data_num = ""
            kicker = "Front matter"
        elif kind == "chapter":
            display_title = title
            progress = f"Chapter {num_label} of {n_chapters}"
            data_num = int(num_label)
            kicker = (f"{part_label} · {part_names[part_label]}" if part_label.startswith("Part ")
                      else part_label)
        elif kind == "appendix":
            display_title = re.sub(r"^Appendix\s+\w+\s*[—–-]\s*", "", title)
            progress = f"Appendix {num_label} of {n_appendices}"
            data_num = num_label
            kicker = "Appendices"
        else:
            display_title = title
            progress = "Reference note"
            data_num = ""
            kicker = "Reference note"
        entries.append({
            "key": key, "rel": rel, "part_label": part_label, "kind": kind, "num_label": num_label,
            "raw_title": first_h1(src_text), "title": display_title, "label": label,
            "progress": progress, "data_num": data_num, "kicker": kicker, "file": page_file(key),
        })
    titles = {e["file"]: e["title"] for e in entries}

    # ---- second pass: the pages ----
    for idx, e in enumerate(entries):
        key, rel, part_label, kind = e["key"], e["rel"], e["part_label"], e["kind"]
        body = gen.convert(rel)
        desc = page_description(body)
        minutes = reading_minutes(body)
        body = head_markup(body, e["kicker"])
        if kind == "chapter":
            body = spec_plate(body, titles)
        body = number_sections(body)

        # prev/next across the whole book sequence, each named
        rel_links = ""
        prev_link = '  <span class="pager-prev pager-empty" aria-hidden="true"></span>'
        next_link = '  <span class="pager-next pager-empty" aria-hidden="true"></span>'
        if idx > 0:
            p = entries[idx - 1]
            prev_link = pager_link("pager-prev", "prev", p["file"],
                                   f'← {nav_label(p["kind"], p["num_label"])}', esc_text(p["title"]))
            rel_links += f'<link rel="prev" href="{p["file"]}">\n'
        if idx < len(entries) - 1:
            n = entries[idx + 1]
            next_link = pager_link("pager-next", "next", n["file"],
                                   f'{nav_label(n["kind"], n["num_label"])} →', esc_text(n["title"]))
            rel_links += f'<link rel="next" href="{n["file"]}">\n'

        page_raw = e["raw_title"] if kind != "front" else "FIRE TO FUTURE — What This Guide Is"
        page_title = f"{page_raw} — Fire to Future"
        part_key = PART_KEYS.get(part_label, "front")
        html = render_page(page_title, desc, e["progress"], part_key, rel_links,
                           prev_link, next_link, body, e["file"], pdf_size)
        out_path = os.path.join(OUT_PAGES_DIR, e["file"])
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(html)
        pages.append((e["file"], key))

        data_entries.append({
            "type": kind,
            "num": e["data_num"],
            "title": e["title"],
            "part": PART_FULL.get(part_label, part_label) if part_label else "Front matter",
            "file": e["file"],
            "label": e["label"],
            "part_key": part_key,
            "part_desc": PART_DESC.get(part_label, ""),
            "minutes": minutes,
        })
        total_words += word_count(rel, book_dir)

    # ---- contents data: fire-to-future/index.html lists it, sitemap.xml maps it ----
    os.makedirs(os.path.dirname(OUT_DATA_JSON), exist_ok=True)
    with open(OUT_DATA_JSON, "w", encoding="utf-8", newline="") as fh:
        json.dump(data_entries, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # ---- shared stylesheet of the reader pages ----
    with open(os.path.join(OUT_PAGES_DIR, "reader.css"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(css_text())

    # ---- PDF ----
    out_pdf = os.path.join(OUT_PAGES_DIR, "Fire-To-Future.pdf")
    shutil.copy2(src_pdf, out_pdf)

    # ---- stale page cleanup: remove old generated pages not in the manifest ----
    kept = {f for f, _k in pages} | {"index.html"}
    for name in os.listdir(OUT_PAGES_DIR):
        if name.endswith(".html") and re.match(r"^(front-matter|ch\d{2}|appendix-[a-g]|source-policy)\.html$", name):
            if name not in kept:
                os.remove(os.path.join(OUT_PAGES_DIR, name))

    # ---- link audit: every href in every generated page must resolve ----
    unresolved = []
    for fname, key in pages:
        with open(os.path.join(OUT_PAGES_DIR, fname), encoding="utf-8") as fh:
            text = fh.read()
        ids = set(re.findall(r"\bid=\"([^\"]+)\"", text))
        for href in re.findall(r"href=\"([^\"]*)\"", text):
            if href.startswith(("http://", "https://", "mailto:", "data:")) or href == "":
                continue
            target, _, frag = href.partition("#")

            def resolve(path):
                if path.startswith("/"):
                    full = os.path.join(SITE_ROOT, path.lstrip("/"))
                else:
                    full = os.path.join(OUT_PAGES_DIR, path.split("/")[-1])
                if os.path.isdir(full):
                    full = os.path.join(full, "index.html")
                return full

            if target == "":
                if frag and frag not in ids:
                    unresolved.append(f"{fname}: missing anchor #{frag}")
                continue
            tpath = resolve(target)
            if not os.path.isfile(tpath):
                unresolved.append(f"{fname}: missing page {target}")
                continue
            if frag:
                ttext = open(tpath, encoding="utf-8").read()
                if f'id="{frag}"' not in ttext:
                    unresolved.append(f"{fname}: missing anchor {target}#{frag}")

    pdf_size = os.path.getsize(out_pdf)
    print(f"pages written:        {len(pages)}")
    print(f"chapters:             {n_chapters} | appendices: {n_appendices}")
    print(f"words:                {total_words:,}")
    print(f"toc data:             {OUT_DATA_JSON}")
    print(f"pdf copied:           {out_pdf} ({pdf_size:,} bytes)")
    if unresolved:
        print("LINK AUDIT FAILED:")
        for u in unresolved[:30]:
            print("  ", u)
        return 1
    print("link audit:           clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
