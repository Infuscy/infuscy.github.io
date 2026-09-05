#!/usr/bin/env python3
"""Build the per-chapter web edition of FIRE TO FUTURE for infuscy.github.io.

Reads the markdown book in C:\\GIT\\Apocalypse\\book (front matter, 51 chapters in
6 parts, appendices A-G), converts each section into a standalone reader page
under fire-to-future/, writes the ToC data file _data/fire_to_future_chapters.json,
and copies the print PDF (Fire-To-Future.pdf) next to the pages.

The conversion mirrors book/tools/build_html.py (same markdown extensions, the
same id namespacing, meta blockquote and callout handling) so the web pages and
the print edition stay content-identical; the only differences are
per-section pages instead of one long document, cross-file .md links rewritten
to page URLs, and tables wrapped for horizontal scrolling.

Usage:
    python scripts/build_fire_to_future.py [--src C:\\GIT\\Apocalypse]

Requires Python 3 + the `markdown` package (pip install markdown).

The script deletes only the generated page files inside fire-to-future/
(front-matter.html, chNN.html, appendix-X.html) and never touches index.html,
chapters.js, or anything outside that directory.
"""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import date

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
    ("Part V", "Planetary Dominance",
     "1950 \u2192 present",
     ["part5/ch38_polymers_materials.md", "part5/ch39_rocketry.md", "part5/ch40_satellites.md",
      "part5/ch41_fiber_optics.md", "part5/ch42_internet.md", "part5/ch43_energy_mastery.md",
      "part5/ch44_biotech.md", "part5/ch45_robotics.md", "part5/ch46_machine_intelligence.md",
      "part5/ch47_institutions.md"]),
    ("Part VI", "The Martial Thread",
     "War as a Technology Driver",
     ["part6/ch48_fortification.md", "part6/ch49_gunpowder_weapons.md",
      "part6/ch50_naval_power.md", "part6/ch51_industrial_war.md"]),
]

APPENDICES = [
    "appendix_A_critical_path.md", "appendix_B_dead_ends.md", "appendix_C_jumps.md",
    "appendix_D_minimum_viable_stack.md", "appendix_E_timeline.md",
    "appendix_F_glossary.md", "appendix_G_key_numbers.md",
]

FRONT_MATTER = "00_front_matter.md"

# book-relative posix path -> key (filename stem)
KEYS = {}
for _part in PARTS:
    for _f in _part[3]:
        KEYS[os.path.splitext(os.path.basename(_f))[0]] = _f
for _f in APPENDICES + [FRONT_MATTER]:
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
    num = int(re.match(r"ch(\d+)", key).group(1))
    return f"ch{num:02d}.html"


def word_count(rel, book_dir):
    txt = read(os.path.join(book_dir, rel))
    return len(re.findall(r"\S+", txt))


class Converter:
    """Mirrors book/tools/build_html.py convert() but links across pages."""

    def __init__(self, book_dir):
        self.book_dir = book_dir
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
        body = re.sub(r'(\bid=")', rf"\1{key}-", body)

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
            inner = re.sub(r"(<strong>(?:Requires|Unlocks):</strong>)", r"<br>\1", m.group(1))
            return f'<blockquote class="meta">{inner}</blockquote>'

        body = re.sub(
            r'<blockquote class="meta">(.*?)</blockquote>',
            meta_breaks,
            body,
            flags=re.S,
        )
        # callout paragraphs (mirrors book/tools/build_html.py Gate 4 mapping)
        labels = {
            "key threshold": "key", "dead end avoided": "dead", "dead end": "dead", "jump": "jump",
            "safety warning": "warn", "operational hazard": "hazard", "scope note": "scope",
            "safety doctrine": "warn", "safety doctrine (binding)": "warn", "scope note (binding)": "scope",
        }

        def callout(m):
            label = m.group(1)
            cls = labels[label.lower()]
            return f'<p class="co co-{cls}"><strong>{label}:</strong>'

        body = re.sub(
            r"<p><strong>(Key threshold|Dead end avoided|Dead end|Jump|Safety warning|Operational hazard|Scope note|Safety doctrine(?: \(binding\))?|Scope note \(binding\))[:.]?</strong>",
            callout,
            body,
        )
        # horizontal-scroll wrapper for wide tables
        body = body.replace("<table>", '<div class="table-wrap"><table>')
        body = body.replace("</table>", "</table></div>")
        return body


# ----------------------------------------------------------------------- template

CSS = """
:root {
  --reader-max: 46rem;
  --reader-text: #1e293b;
  --reader-muted: #64748b;
  --reader-accent: #2563eb;
  --reader-border: #e2e8f0;
  --reader-font-scale: 1;
}
* { box-sizing: border-box; }
body {
  background: #f8fafc;
  font-family: Inter, system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
  color: var(--reader-text);
  margin: 0;
  padding: 0;
}
.reader-top-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(255,255,255,.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--reader-border);
  padding: .75rem 1.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: .9rem;
}
.reader-top-bar a { color: var(--reader-accent); text-decoration: none; font-weight: 600; }
.reader-top-bar a:hover { text-decoration: underline; }
.reader-progress { color: var(--reader-muted); font-size: .85rem; }
.reader-font-controls { display: flex; gap: .25rem; align-items: center; }
.font-btn {
  background: none;
  border: 1px solid var(--reader-border);
  border-radius: .375rem;
  color: var(--reader-muted);
  cursor: pointer;
  font-family: inherit;
  font-size: .85rem;
  font-weight: 600;
  padding: .25rem .5rem;
  line-height: 1;
  transition: background .15s, border-color .15s, color .15s;
}
.font-btn:hover { background: #eff6ff; border-color: var(--reader-accent); color: var(--reader-accent); }

.reader-content {
  max-width: var(--reader-max);
  margin: 0 auto;
  padding: 2.5rem 1.25rem 3rem;
}
.reader-content h1 {
  font-size: calc(1.6rem * var(--reader-font-scale));
  font-weight: 800;
  letter-spacing: -.02em;
  line-height: 1.25;
  color: #0f172a;
  margin: 0 0 1.75rem;
  text-align: center;
}
.reader-content h2 {
  font-size: calc(1.2rem * var(--reader-font-scale));
  font-weight: 700;
  margin: 2.25rem 0 .75rem;
  color: #0f172a;
}
.reader-content h3 {
  font-size: calc(1.05rem * var(--reader-font-scale));
  font-weight: 600;
  margin: 1.75rem 0 .5rem;
  color: #0f172a;
}
.reader-content h4, .reader-content h5, .reader-content h6 {
  font-size: 1rem;
  font-weight: 600;
  margin: 1.5rem 0 .5rem;
  color: #0f172a;
}
.reader-content p {
  font-size: calc(1.05rem * var(--reader-font-scale));
  line-height: 1.8;
  margin: 0 0 1.15rem;
  color: var(--reader-text);
  text-align: justify;
  hyphens: auto;
}
.reader-content a { color: var(--reader-accent); text-decoration: none; }
.reader-content a:hover { text-decoration: underline; }
.reader-content ul, .reader-content ol {
  margin: 0 0 1.25rem;
  padding-left: 1.5rem;
  font-size: calc(1.05rem * var(--reader-font-scale));
  line-height: 1.8;
}
.reader-content li { margin: 0 0 .4rem; }
.reader-content em { font-style: italic; }
.reader-content hr { border: 0; text-align: center; margin: 2rem auto; max-width: 6rem; }
.reader-content hr::before { content: '\\00b7 \\00b7 \\00b7'; color: var(--reader-muted); font-size: 1.2rem; letter-spacing: .3em; }

/* chapter metadata blockquote (Era span / Requires / Unlocks) */
.reader-content blockquote {
  margin: 1.25rem 0;
  padding: .9rem 1.1rem;
  background: #f6f8fb;
  border-left: 3px solid #cbd5e1;
  border-radius: 0 .5rem .5rem 0;
  font-size: calc(.95rem * var(--reader-font-scale));
  line-height: 1.7;
  color: #334155;
}
.reader-content blockquote.meta {
  background: #eef2f7;
  border-left-color: var(--reader-accent);
}
.reader-content blockquote p { margin: 0 0 .5rem; text-align: left; hyphens: none; }
.reader-content blockquote p:last-child { margin-bottom: 0; }

/* callouts: Key threshold / Dead end avoided / Jump */
.reader-content .co {
  padding: .85rem 1rem;
  margin: 1.25rem 0;
  border-left: 3px solid;
  border-radius: 0 .5rem .5rem 0;
  font-size: calc(.98rem * var(--reader-font-scale));
  line-height: 1.7;
  text-align: left;
  hyphens: none;
}
.co-key { background: #eef5ec; border-color: #3f6c3f; }
.co-dead { background: #f9eeec; border-color: #8f3b2d; }
.co-jump { background: #edf2f9; border-color: #2f5286; }
.co-warn { background: #fdf0ec; border-color: #b3271e; border-width: 3px; }
.co-hazard { background: #fff7e6; border-color: #8a6d1f; }
.co-scope { background: #eef1f5; border-color: #46617a; }

/* figures (inline SVG, web analogue of the print figure CSS) */
.reader-content figure.fig {
  margin: 1.25rem 0;
  padding: .8rem .9rem;
  background: #fbf9f3;
  border: 1px solid #b3a67f;
  border-radius: .5rem;
  text-align: center;
}
.reader-content figure.fig svg { max-width: 100%; height: auto; display: block; margin: 0 auto; }
.reader-content figure.fig svg.wide { width: 100%; }
.reader-content figure.fig figcaption {
  font-size: calc(.85rem * var(--reader-font-scale));
  font-style: italic;
  color: #4a4436;
  margin-top: .5rem;
  text-align: center;
  line-height: 1.45;
}

/* tables */
.table-wrap { overflow-x: auto; margin: 1.25rem 0; }
.reader-content table { border-collapse: collapse; width: 100%; font-size: calc(.9rem * var(--reader-font-scale)); line-height: 1.55; }
.reader-content th { background: #f1f5f9; font-weight: 700; text-align: left; }
.reader-content th, .reader-content td { border: 1px solid var(--reader-border); padding: .5rem .65rem; vertical-align: top; }
.reader-content tr:nth-child(even) td { background: #f8fafc; }

/* code */
.reader-content code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Courier New", monospace;
  font-size: .875em;
  background: #f1f5f9;
  padding: .15em .35em;
  border-radius: .3rem;
}
.reader-content pre {
  background: #f1f5f9;
  border: 1px solid var(--reader-border);
  border-radius: .5rem;
  padding: 1rem;
  overflow-x: auto;
  margin: 1.25rem 0;
  white-space: pre;
}
.reader-content pre code { background: none; padding: 0; font-size: .85rem; }

.reader-bottom-nav {
  max-width: var(--reader-max);
  margin: 0 auto 3rem;
  padding: 0 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.reader-nav-link {
  display: inline-block;
  padding: .5rem 1rem;
  border: 1px solid var(--reader-border);
  border-radius: .5rem;
  color: var(--reader-accent);
  text-decoration: none;
  font-weight: 600;
  font-size: .95rem;
  transition: background .15s, border-color .15s;
}
.reader-nav-link:hover { background: #eff6ff; border-color: var(--reader-accent); }
.reader-nav-link.disabled { color: var(--reader-muted); border-color: transparent; pointer-events: none; }
.reader-toc-link { color: var(--reader-muted); text-decoration: none; font-size: .9rem; }
.reader-toc-link:hover { color: var(--reader-accent); }

@media (max-width: 600px) {
  .reader-content { padding: 1.5rem 1rem 2rem; }
  .reader-content h1 { font-size: calc(1.3rem * var(--reader-font-scale)); }
  .reader-content p { font-size: calc(1rem * var(--reader-font-scale)); line-height: 1.75; }
  .reader-content p { text-align: left; }
}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'; connect-src 'self'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>@TITLE@</title>
<style>
@CSS@
</style>
</head>
<body>
<div class="reader-top-bar">
  <a href="/fire-to-future/">\u2190 Table of Contents</a>
  <span class="reader-font-controls"><button class="font-btn" id="fontDown" title="Smaller text" aria-label="Decrease font size">A\u2212</button><button class="font-btn" id="fontUp" title="Larger text" aria-label="Increase font size">A+</button></span>
  <span class="reader-progress">@PROGRESS@</span>
</div>
<main class="reader-content">
@BODY@
</main>
<nav class="reader-bottom-nav">
  @PREV@
  <a href="/fire-to-future/" class="reader-toc-link">Contents</a>
  @NEXT@
</nav>
<p style="text-align:center;font-size:.8rem;color:#64748b;margin:1rem auto 2.5rem;max-width:46rem;padding:0 1.25rem;line-height:1.5;">FIRE TO FUTURE \u2014 The Complete Technology Ladder \u00b7 <a href="/fire-to-future/Fire-To-Future.pdf" style="color:#2563eb;">Download PDF</a></p>
<script>
(function(){
  var scale = 1;
  function apply(){ document.documentElement.style.setProperty("--reader-font-scale", scale); }
  apply();
  document.getElementById("fontDown").addEventListener("click", function(){ scale = Math.max(0.6, scale - 0.1); apply(); });
  document.getElementById("fontUp").addEventListener("click", function(){ scale = Math.min(2.0, scale + 0.1); apply(); });
})();
</script>
</body>
</html>
"""


def render_page(title, progress, prev, next_, body):
    return (TEMPLATE
            .replace("@TITLE@", title)
            .replace("@PROGRESS@", progress)
            .replace("@PREV@", prev)
            .replace("@NEXT@", next_)
            .replace("@BODY@", body)
            .replace("@CSS@", CSS))


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

    n_chapters = sum(1 for s in seq if s[3] == "chapter")
    n_appendices = sum(1 for s in seq if s[3] == "appendix")

    gen = Converter(book_dir)
    pages = []  # (filename, {..}) in sequence order
    data_entries = []
    total_words = 0

    for idx, (key, rel, part_label, kind, num_label) in enumerate(seq):
        src_text = read(os.path.join(book_dir, rel))
        body = gen.convert(rel)
        raw_title = first_h1(src_text)
        title, label = split_h1(src_text)

        if kind == "front":
            display_title = "Introduction \u2014 What This Guide Is"
            progress = "Front matter"
            label = "Front matter"
            data_num = ""
        elif kind == "chapter":
            display_title = title
            progress = f"Chapter {num_label} of {n_chapters}"
            data_num = int(num_label)
        else:
            display_title = re.sub(r"^Appendix\s+\w+\s*[—–-]\s*", "", title)
            progress = f"Appendix {num_label} of {n_appendices}"

        # prev/next across the whole book sequence
        prev_link, next_link = '<span class="reader-nav-link disabled">\u2190 Start</span>', \
            '<span class="reader-nav-link disabled">End \u2192</span>'
        if idx > 0:
            prev_key, prev_rel, _p, prev_kind, prev_num = seq[idx - 1]
            prev_label = "Chapter " + prev_num if prev_kind == "chapter" else \
                ("Appendix " + prev_num if prev_kind == "appendix" else "Front matter")
            prev_link = f'<a href="{page_file(prev_key)}" class="reader-nav-link">\u2190 {prev_label}</a>'
        if idx < len(seq) - 1:
            next_key, _next_rel, _p, next_kind, next_num = seq[idx + 1]
            next_label = "Chapter " + next_num if next_kind == "chapter" else \
                ("Appendix " + next_num if next_kind == "appendix" else "Front matter")
            next_link = f'<a href="{page_file(next_key)}" class="reader-nav-link">{next_label} \u2192</a>'

        page_raw = raw_title if kind != "front" else "FIRE TO FUTURE \u2014 What This Guide Is"
        page_title = f"{page_raw} \u2014 Fire to Future"
        html = render_page(page_title, progress, prev_link, next_link, body)
        out_path = os.path.join(OUT_PAGES_DIR, page_file(key))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(html)
        pages.append((page_file(key), key))

        data_entries.append({
            "type": kind,
            "num": data_num,
            "title": display_title,
            "part": PART_FULL.get(part_label, part_label) if part_label else "Front matter",
            "file": page_file(key),
            "label": label,
        })
        total_words += word_count(rel, book_dir)

    # ---- ToC data for the Jekyll-rendered chapters.js ----
    os.makedirs(os.path.dirname(OUT_DATA_JSON), exist_ok=True)
    with open(OUT_DATA_JSON, "w", encoding="utf-8", newline="") as fh:
        json.dump(data_entries, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # ---- PDF ----
    out_pdf = os.path.join(OUT_PAGES_DIR, "Fire-To-Future.pdf")
    shutil.copy2(src_pdf, out_pdf)

    # ---- stale page cleanup: remove old generated pages not in the manifest ----
    kept = {f for f, _k in pages} | {"index.html", "chapters.js"}
    for name in os.listdir(OUT_PAGES_DIR):
        if name.endswith(".html") and re.match(r"^(front-matter|ch\d{2}|appendix-[a-g])\.html$", name):
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
