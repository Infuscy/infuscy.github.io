#!/usr/bin/env python3
"""Build the web edition of THE SPELLBOOK OF OLD STILLNESS for infuscy.github.io.

Source: old-stillness/the-spellbook-of-old-stillness.md, the book's Markdown export
(kept in the repo, excluded from the site by _config.yml). Each `##` section becomes
one reader page in old-stillness/:

    how-to-read.html        "How to read this book" (with the "At a glance" timeline)
    before-you-cast.html    "Before you cast"
    foundation.html         "The Foundation: the seat"
    china.html …            "Chapter I — China" … "Chapter VII — The Sufi Path"
    counterfeits.html       "Appendix A — Counterfeits"
    grimoire-shelf.html     "Appendix B — The Grimoire Shelf"

plus old-stillness/index.html (cover and contents, with Jekyll front matter so the
book is in feed.xml and the sitemap) and _data/old_stillness_pages.json (the page
list the sitemap reads).

The text is never rewritten, only marked up for reading:
  * "### 9. Name (term)"          -> the spell head: its number as a moon on the
    horizon, the name, the term (CJK tagged zh-Hant in China, ja in Japan)
  * "**Source:** … · **Seal:** …" -> the provenance label; every Gold, Silver or Bronze
    in a seal gets its gauge (three discs: Gold 3 filled, Silver 2, Bronze 1)
  * "**Casting**" + its list      -> the casting head and the numbered steps
  * "**Promised effect:**"        -> the tradition's claim, set apart
  * "**Caution:**", and "Plain rules for casting" with its list -> warning callouts
  * "**Note:**"                   -> a note
  * a bold paragraph on its own in the front and back matter -> a section head
  * "[embedded content: …]"       -> the "At a glance" timeline, drawn from GLANCE: the
    data of the chart in the book's original document (the export keeps only its
    caption); each chapter opens with its own lane of it
  * "Spell 9", "Spells 9 and 10", "Chapter III", "Appendix A", "Foundation",
    "Before you cast", "the Locked Spells", Appendix B's spell numbers and the
    "Name (15)" cells of Appendix A -> links
  * tables                        -> data-label cells that stack on phones

The pages share old-stillness/book.css (hand-written: this script never touches it),
the fonts of The Old Book of the East (/old-east/fonts/: its Gentium subset already
has every letter this book uses, which the build checks) and /js/reader-font.js (the
A-/A+ buttons). CSP is script-src 'self' and style-src 'self': the pages carry no
inline scripts or styles.

Usage:
    py scripts/build_old_stillness.py [--src path/to/book.md]

Requires Python 3 + the `markdown` package (pip install markdown).
"""
import argparse
import datetime
import html as htmlmod
import json
import os
import re
import sys
import unicodedata

try:
    import markdown
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: the `markdown` package is required (pip install markdown)\n")
    sys.exit(1)

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOOK_DIR = os.path.join(SITE_ROOT, "old-stillness")
DEFAULT_SRC = os.path.join(BOOK_DIR, "the-spellbook-of-old-stillness.md")
DATA_JSON = os.path.join(SITE_ROOT, "_data", "old_stillness_pages.json")
# The type is The Old Book of the East's (scripts/subset_old_east_fonts.py): its Gentium
# subset already covers this book's transliterations (ā ṇ ṭ ḥ ẓ ʿ ʾ …) and has the small
# capitals. check_font_coverage() confirms it on every build. The CJK of the spell names
# is left to the system's CJK fonts (book.css names them per language).
FONT_DIR = os.path.join(SITE_ROOT, "old-east", "fonts")
FONT_URL = "/old-east/fonts/"

SITE_URL = "https://infuscy.github.io"
BASE = "/old-stillness/"
SHORT = "The Spellbook of Old Stillness"
AUTHOR = "Buse Florin-Emilian"
WORDS_PER_MINUTE = 230

FRONT = {
    "How to read this book": "how-to-read",
    "Before you cast": "before-you-cast",
    "The Foundation: the seat": "foundation",
}
# The language of the CJK in a chapter's spell names.
CJK_LANG = {"China": "zh-Hant", "Japan": "ja"}
CJK_RUN = re.compile(r"[぀-ヿ㐀-䶿一-鿿豈-﫿]+")
METALS = {"Gold": 3, "Silver": 2, "Bronze": 1}
METAL_RE = re.compile(r"\b(Gold|Silver|Bronze)\b")

# Voluntary AI transparency note (EU AI Act art. 50; see CLAUDE.md, Compliance):
# in every page's footer, and on the cover with the article reference.
TRANSPARENCY = (
    "<strong>Transparency:</strong> this book was compiled with the help of an AI system "
    "(Claude), working from the texts, translations and studies linked in each spell and "
    "listed in <a href=\"grimoire-shelf.html\">Appendix B</a>; the author reviewed the text "
    "against those sources before publication. Editorial responsibility: "
    f"{AUTHOR} (<a href=\"/#contact\">contact</a>)."
)
TRANSPARENCY_COVER = (TRANSPARENCY + " A transparency statement under Article 50 of "
                      "Regulation (EU) 2024/1689 (the AI Act).")

# The cover's epigraph: Dōgen's instruction, from Spell 8 (its words as the book gives them).
EPIGRAPH = ('<figure class="epigraph"><blockquote><p>“Think of not-thinking. How? Non-thinking.”</p>'
            '</blockquote><figcaption>Dōgen, quoting Yaoshan, in the <em>Universal Recommendation '
            'for Zazen</em> (1227) · <a href="japan.html#spell-8">Spell 8</a></figcaption></figure>')

# The share image (img/social-card-old-stillness.png) is made by scripts/make_old_stillness_card.py.
IMAGE_ALT = ("The Spellbook of Old Stillness: the title in moonlight on deep teal night water, "
             "under a full moon and its reflection")

CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "font-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'; connect-src 'self'")

ICON_WARN = ('<svg class="caution-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
             'stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round">'
             '<path d="M12 3.5L21.5 20h-19z"/><path d="M12 10v4.5"/><path d="M12 17.3v.2"/></svg>')
ICON_LOCK = ('<svg class="lock-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
             'stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round">'
             '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8.5 10.5V7.6a3.5 3.5 0 0 1 7 0v2.9"/>'
             '<path d="M12 14.6v2"/></svg>')

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}

# ----------------------------------------------------------------- the timeline
# "At a glance" in the book's original document is a chart that the Markdown export
# replaces with its caption. Its data, as drawn there: one lane per tradition, from its
# oldest source in the book to its newest (from/to are the lane's labels), a dot per
# source, the 1800 cut-off and the strip of Appendix A's modern methods. Years < 0 are BCE.
GLANCE_LANES = [
    # key, label, chapter, start, end, from, to, sources
    ("china", "China", "I", -350, 1163, "c. 350 BCE", "1163", [-350, -300, 500, 575, 700, 1157, 1163]),
    ("greece", "Greece and Rome", "V", -51, 265, "51 BCE", "c. 265", [-51, 45, 108, 175, 265]),
    ("india", "India", "IV", -50, 1450, "1st c. BCE", "15th c.", [-50, 100, 375, 430, 800, 1450]),
    ("christian", "Christian", "VI", 425, 1548, "c. 425", "1548", [425, 1165, 1250, 1330, 1375, 1548]),
    ("tibet", "Tibet", "III", 793, 1580, "c. 793", "late 1500s", [793, 1150, 1580]),
    ("sufi", "Sufi", "VII", 857, 1389, "c. 857", "1389", [857, 1100, 1179, 1389]),
    ("japan", "Japan", "II", 1130, 1757, "c. 1130", "1757", [1130, 1227, 1757]),
]
GLANCE_CUT = 1800
GLANCE_BAND = (1900, 2026)
GLANCE_TITLE = "Every source here predates 1800; the counterfeits came after 1900"
GLANCE_SUB = ("Each bar runs from a tradition’s oldest source in this book to its newest; "
              "each dot is one source")
GLANCE_LO, GLANCE_HI = -500, 2050
GLANCE_TICKS = [-500, 1, 500, 1000, 1500, 2000]


def roman_to_int(s):
    total = 0
    for i, ch in enumerate(s):
        v = ROMAN[ch]
        total += -v if i + 1 < len(s) and ROMAN[s[i + 1]] > v else v
    return total


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def plain(s):
    """Tag-free, entity-free text."""
    return htmlmod.unescape(strip_tags(s))


def attr(s):
    return htmlmod.escape(s, quote=True)


def slugify(s):
    s = plain(s).replace("’", "").replace("'", "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def word_count(s):
    return len(re.findall(r"\S+", plain(s)))


def minutes(words):
    return max(1, round(words / WORDS_PER_MINUTE))


def year(y):
    return f"{-y} BCE" if y < 0 else ("1 CE" if y == 1 else str(y))


def num(x):
    """SVG coordinates: one decimal, no trailing zero."""
    return f"{x:.1f}".rstrip("0").rstrip(".")


# ----------------------------------------------------------------- source

BYLINE = re.compile(r"^([A-Z][a-z]{2}) (\d{1,2}), (\d{4}) · @\S+$")
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def parse_book(text):
    """-> title, date of the byline, the intro paragraphs (Markdown), [{heading, md}]."""
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    m = re.match(r"# (.+)", lines[0])
    if not m:
        raise SystemExit("ERROR: the source must start with '# <title>'")
    title = m.group(1).strip()
    first_h2 = next(i for i, ln in enumerate(lines) if ln.startswith("## "))
    date, intro = None, []
    for ln in (ln.strip() for ln in lines[1:first_h2]):
        bm = BYLINE.match(ln)
        if bm and date is None:
            date = datetime.date(int(bm.group(3)), MONTHS[bm.group(1)], int(bm.group(2)))
        elif ln:
            intro.append(ln)
    if date is None:
        raise SystemExit("ERROR: no 'Mon D, YYYY · @name' byline under the title")
    sections, cur = [], None
    for ln in lines[first_h2:]:
        if ln.startswith("## "):
            cur = {"heading": ln[3:].strip(), "md": []}
            sections.append(cur)
        else:
            cur["md"].append(ln)
    for s in sections:
        s["md"] = "\n".join(s["md"]).strip() + "\n"
    return title, date, intro, sections


SMARTY_ENTITIES = {"&ldquo;": "“", "&rdquo;": "”", "&lsquo;": "‘",
                   "&rsquo;": "’", "&hellip;": "…", "&ndash;": "–",
                   "&mdash;": "—", "&laquo;": "«", "&raquo;": "»"}


def md_to_html(src):
    # The export indents sub-items by three spaces; Python-Markdown nests them at four.
    src = re.sub(r"^ {3}(?=[-*] |\d+\. )", "    ", src, flags=re.M)
    md = markdown.Markdown(extensions=["tables", "sane_lists", "smarty"])
    out = md.convert(src)
    for ent, ch in SMARTY_ENTITIES.items():
        out = out.replace(ent, ch)
    if re.search(r"<li>\s*<p>", out):
        raise SystemExit("ERROR: a loose list (blank lines between items) slipped in; "
                         "the block splitter expects tight lists")
    return out


def md_inline(s):
    """A heading's Markdown -> inline HTML (curly quotes, italics)."""
    out = md_to_html(s).strip()
    return re.sub(r"^<p>(.*)</p>$", r"\1", out, flags=re.S)


def tag_cjk(html, lang, where):
    if not CJK_RUN.search(html):
        return html
    if not lang:
        print(f"  CJK without a language in {where}: add the chapter to CJK_LANG")
        return html
    return CJK_RUN.sub(lambda m: f'<span lang="{lang}">{m.group(0)}</span>', html)


def split_title(s):
    """'Name — gloss' or 'Name: gloss' -> (name, separator, gloss)."""
    m = re.match(r"^(.*?)( — |: )(.+)$", s)
    return (m.group(1), m.group(2), m.group(3)) if m else (s, "", "")


def split_term(h):
    """'Inward Training (<em>Neiye</em> 內業)' -> ('Inward Training', '<em>Neiye</em> 內業')."""
    h = h.strip()
    if not h.endswith(")"):
        return h, ""
    depth = 0
    for i in range(len(h) - 1, -1, -1):
        if h[i] == ")":
            depth += 1
        elif h[i] == "(":
            depth -= 1
            if depth == 0:
                return h[:i].rstrip(), h[i + 1:-1].strip()
    return h, ""


def page_meta(heading):
    m = re.match(r"Chapter ([IVX]+) — (.+)$", heading)
    if m:
        name = m.group(2)
        return {"kind": "chapter", "num": m.group(1), "n": roman_to_int(m.group(1)),
                "name": md_inline(name), "plain_name": name, "kicker": f"Chapter {m.group(1)}",
                "file": slugify(re.sub(r"^The ", "", name)) + ".html"}
    m = re.match(r"Appendix ([A-Z]) — (.+)$", heading)
    if m:
        name = m.group(2)
        return {"kind": "back", "num": m.group(1), "n": m.group(1), "name": md_inline(name),
                "plain_name": name, "kicker": f"Appendix {m.group(1)}",
                "file": slugify(re.sub(r"^The ", "", name)) + ".html"}
    if heading in FRONT:
        return {"kind": "front", "num": "", "n": "", "name": md_inline(heading), "plain_name": heading,
                "kicker": "", "file": FRONT[heading] + ".html"}
    raise SystemExit(f"ERROR: unknown section heading {heading!r} (add it to FRONT)")


# ----------------------------------------------------------------- blocks

def split_blocks(html):
    """Top-level blocks of Python-Markdown output, as [tag, html] pairs."""
    blocks, pos, n = [], 0, len(html)
    while True:
        pos = re.compile(r"\s*").match(html, pos).end()
        if pos >= n:
            return blocks
        m = re.compile(r"<(\w+)").match(html, pos)
        if not m:
            raise SystemExit(f"ERROR: stray text in Markdown output: {html[pos:pos + 80]!r}")
        tag = m.group(1).lower()
        if tag in ("hr", "br", "img"):
            end = html.index(">", pos) + 1
        else:
            depth, end = 0, None
            for t in re.compile(rf"<(/?){tag}\b[^>]*>").finditer(html, pos):
                depth += -1 if t.group(1) else 1
                if depth == 0:
                    end = t.end()
                    break
            if end is None:
                raise SystemExit(f"ERROR: unclosed <{tag}> in Markdown output")
        blocks.append([tag, html[pos:end]])
        pos = end


def p_inner(block):
    return re.match(r"<p>(.*)</p>$", block, re.S).group(1)


LEAD_STRONG = re.compile(r"^<strong>(.*?)</strong>(.*)$", re.S)
BOLD_ONLY = re.compile(r"<strong>((?:(?!</?strong>).)+)</strong>", re.S)
EMBED = re.compile(r"(?:&#91;|\[)embedded content: (.+?)\\?\]", re.S)
SOURCE_SEAL = re.compile(r"^<strong>Source:</strong>\s*(.*?)\s*·\s*<strong>Seal:</strong>\s*(.*)$", re.S)


def lead(block):
    """(label, rest) when a paragraph opens with a bold label, else (None, None)."""
    m = LEAD_STRONG.match(p_inner(block))
    return (m.group(1), m.group(2)) if m else (None, None)


def gauge(metal):
    depth = METALS[metal]
    marks = "".join('<i class="on"></i>' if k < depth else "<i></i>" for k in range(3))
    return f'<span class="gauge" aria-hidden="true">{marks}</span>'


def seal_html(text):
    """Every metal in a seal gets its gauge: 'Silver for … Gold for …' carries two."""
    return METAL_RE.sub(lambda m: f'<span class="metal metal-{m.group(1).lower()}">'
                                  f'{gauge(m.group(1))}{m.group(1)}</span>', text)


def seal_mark(metal):
    """The gauge alone, for the contents lists (the name of the metal is read aloud)."""
    if not metal:
        return ""
    return (f'<span class="toc-seal metal-{metal.lower()}">{gauge(metal)}'
            f'<span class="vh">, seal: {metal}</span></span>')


def render_list(block, ordered_cls=None):
    block = block.replace("<li><strong>", '<li><strong class="rubric">')
    if ordered_cls and block.startswith("<ol>"):
        block = f'<ol class="{ordered_cls}">' + block[len("<ol>"):]
    return block


def render_steps(block):
    block = block.replace("<li><strong>", '<li><strong class="step-lead">')
    return '<ol class="steps">' + block[len("<ol>"):] if block.startswith("<ol>") else block


def short_label(head):
    """'Zhiyi, Concise Śamatha-Vipaśyanā (6th c., China)' -> 'Zhiyi' for the stacked cells."""
    return head.split(",")[0].strip() if len(head) > 28 and "," in head else head


def render_table(block):
    heads = [plain(h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", block, re.S)]
    kind = {"Seal": "seals", "": "manuals", "Practice": "locked", "Sold as": "counterfeits",
            "Spells": "shelf"}.get(heads[0] if heads else None, "")

    def row(m):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), re.S)
        out = []
        for k, c in enumerate(cells):
            label = short_label(heads[k]) if k < len(heads) else ""
            if kind == "seals" and k == 0:
                c = seal_html(c)
            out.append(f'<td role="cell" data-label="{attr(label)}">{c}</td>')
        return '<tr role="row">' + "".join(out) + "</tr>"

    block = re.sub(r"<tr>\s*(<td.*?)</tr>", row, block, flags=re.S)
    block = (block.replace("<table>", f'<table role="table"{f" class={chr(34)}{kind}{chr(34)}" if kind else ""}>')
             .replace("<thead>", '<thead role="rowgroup">')
             .replace("<tbody>", '<tbody role="rowgroup">')
             .replace("<th>", '<th role="columnheader">')
             .replace("<tr>", '<tr role="row">'))
    # the three manuals side by side, and the counterfeits, widen past the text column
    wide = " table-wide" if kind in ("manuals", "counterfeits") else ""
    return f'<div class="table-wrap{wide}">{block}</div>'


# ----------------------------------------------------------------- the timeline, drawn

def glance_x(y, x0, w):
    return x0 + (y - GLANCE_LO) / (GLANCE_HI - GLANCE_LO) * w


def glance_svg(layout, chapter_files):
    """The "At a glance" chart as inline SVG: a wide layout (names in a column on the
    left) and a narrow one for phones (each name over its lane). Colours are book.css's."""
    wide = layout == "wide"
    if wide:  # drawn for the text column (~620px), so its text is near true size there
        W, x0, w, top, lane0, step = 620, 150, 446, 44, 92, 44
        fs_tick, fs_lane, fs_range, fs_note = 12, 14, 11.5, 12
    else:
        W, x0, w, top, lane0, step = 360, 16, 328, 34, 82, 54
        fs_tick, fs_lane, fs_range, fs_note = 11, 13, 11.5, 11.5
    bottom = lane0 + step * (len(GLANCE_LANES) - 1) + 26
    H = bottom + 52

    def X(y):
        return glance_x(y, x0, w)

    out = [f'<svg class="glance-svg glance-{layout}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-labelledby="glance-title glance-sub">']
    b0, b1 = GLANCE_BAND
    out.append(f'<rect class="g-band" x="{num(X(b0))}" y="{top}" width="{num(X(b1) - X(b0))}" '
               f'height="{bottom - top}"/>')
    for k, t in enumerate(GLANCE_TICKS):
        anchor = "start" if (not wide and k == 0) else "middle"
        out.append(f'<line class="g-grid" x1="{num(X(t))}" x2="{num(X(t))}" y1="{top}" y2="{bottom}"/>'
                   f'<text class="g-tick" x="{num(X(t))}" y="{top - 12}" text-anchor="{anchor}" '
                   f'font-size="{fs_tick}">{year(t)}</text>')
    out.append(f'<line class="g-axis" x1="{x0}" x2="{x0 + w}" y1="{top}" y2="{top}"/>')
    cx = num(X(GLANCE_CUT))
    out.append(f'<line class="g-cut" x1="{cx}" x2="{cx}" y1="{top}" y2="{bottom}"/>')
    for i, (key, label, chap, start, end, frm, to, points) in enumerate(GLANCE_LANES):
        y = lane0 + step * i
        href = chapter_files.get(chap, "")
        rng = f"{frm} to {to}"
        if wide:
            out.append(f'<a href="{href}"><text class="g-lane" x="14" y="{y + 5}" font-size="{fs_lane}">'
                       f'{label}</text></a>'
                       f'<text class="g-range" x="{num(X(start))}" y="{y - 12}" font-size="{fs_range}">'
                       f'{rng}</text>')
        else:
            out.append(f'<a href="{href}"><text class="g-lane" x="{x0}" y="{y - 14}" font-size="{fs_lane}">'
                       f'{label}<tspan class="g-range" dx="7" font-size="{fs_range}">{rng}</tspan></text></a>')
        out.append(f'<rect class="g-bar" x="{num(X(start))}" y="{y - 5}" width="{num(X(end) - X(start))}" '
                   f'height="10" rx="5"><title>{label}: {rng}</title></rect>')
        for p in points:
            out.append(f'<circle class="g-dot" cx="{num(X(p))}" cy="{y}" r="4.5"><title>{label} · '
                       f'{year(p)}</title></circle>')
    out.append(f'<text class="g-note" x="{num(X(GLANCE_CUT) - 6)}" y="{bottom + 20}" text-anchor="end" '
               f'font-size="{fs_note}">Cut-off {GLANCE_CUT}</text>')
    out.append(f'<a href="counterfeits.html"><text class="g-note g-band-note" x="{num(X(b1))}" '
               f'y="{bottom + 40}" text-anchor="end" font-size="{fs_note}">Counterfeits in Appendix A: '
               f'{b0}s to today</text></a>')
    out.append("</svg>")
    return "".join(out)


def glance_figure(caption, chapter_files):
    rows = "".join(
        f'<tr role="row"><td role="cell" data-label="Tradition"><a href="{chapter_files.get(chap, "")}">'
        f'{label}</a></td><td role="cell" data-label="Oldest source">{frm}</td>'
        f'<td role="cell" data-label="Newest source">{to}</td>'
        f'<td role="cell" data-label="Sources in this book">{len(points)}</td></tr>'
        for _k, label, chap, _s, _e, frm, to, points in GLANCE_LANES)
    table = ('<div class="table-wrap"><table role="table" class="lanes"><thead role="rowgroup">'
             '<tr role="row"><th role="columnheader">Tradition</th><th role="columnheader">Oldest source</th>'
             '<th role="columnheader">Newest source</th><th role="columnheader">Sources in this book</th>'
             f'</tr></thead><tbody role="rowgroup">{rows}</tbody></table></div>')
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return (f'<figure class="glance"><p class="glance-title" id="glance-title">{GLANCE_TITLE}</p>'
            f'<p class="glance-sub" id="glance-sub">{GLANCE_SUB}</p>'
            f'{glance_svg("wide", chapter_files)}{glance_svg("narrow", chapter_files)}{cap}'
            f'<details class="glance-data"><summary>The seven lanes as a table</summary>{table}</details>'
            f'</figure>')


def lane_strip(chap):
    """A chapter's own lane of the timeline, on the same scale, for its title page."""
    lane = next((ln for ln in GLANCE_LANES if ln[2] == chap), None)
    if not lane:
        return ""
    _k, label, _c, start, end, frm, to, points = lane
    W, H, x0, w, y = 600, 30, 10, 580, 15

    def X(v):
        return glance_x(v, x0, w)

    b0, b1 = GLANCE_BAND
    parts = [f'<svg class="lane-svg" viewBox="0 0 {W} {H}" aria-hidden="true" focusable="false">',
             f'<rect class="g-band" x="{num(X(b0))}" y="2" width="{num(X(b1) - X(b0))}" height="{H - 4}"/>',
             f'<line class="g-axis" x1="{x0}" x2="{x0 + w}" y1="{y}" y2="{y}"/>']
    parts += [f'<line class="g-axis" x1="{num(X(t))}" x2="{num(X(t))}" y1="{y - 4}" y2="{y + 4}"/>'
              for t in GLANCE_TICKS]
    cx = num(X(GLANCE_CUT))
    parts.append(f'<line class="g-cut" x1="{cx}" x2="{cx}" y1="1" y2="{H - 1}"/>')
    parts.append(f'<rect class="g-bar" x="{num(X(start))}" y="{y - 6}" width="{num(X(end) - X(start))}" '
                 f'height="12" rx="6"/>')
    parts += [f'<circle class="g-dot" cx="{num(X(p))}" cy="{y}" r="5.2"/>' for p in points]
    parts.append("</svg>")
    tip = f"{label}, {frm} to {to}: its lane on the timeline of all seven traditions"
    return (f'<a class="lane-strip" href="how-to-read.html#at-a-glance" aria-label="{tip}" '
            f'title="{tip}">{"".join(parts)}</a>')


# ----------------------------------------------------------------- spells

def casting_head(rest):
    note = rest.strip()
    note_html = f'<span class="casting-note"> {note}</span>' if note else ""
    return f'<h3 class="casting-head">Casting{note_html}</h3>'


def provenance(source, seal):
    rows = [f'<p class="prov-row"><span class="prov-cap">Source<span class="vh">:</span></span>'
            f'<span class="prov-text">{source}</span></p>']
    if seal:
        rows.append(f'<p class="prov-row prov-seal"><span class="prov-cap">Seal<span class="vh">:</span>'
                    f'</span><span class="prov-text">{seal_html(seal)}</span></p>')
    return f'<div class="provenance">{"".join(rows)}</div>'


def caution_block(label, rest):
    return (f'<div class="caution" role="note">{ICON_WARN}<p><strong class="caution-cap">{label}</strong>'
            f'{rest}</p></div>')


def transform_spell(blocks, where):
    """A spell's blocks -> (html, the first metal of its seal)."""
    out, metal = [], None
    for tag, b in blocks:
        if tag == "p":
            inner = p_inner(b)
            m = SOURCE_SEAL.match(inner)
            if m:
                out.append(provenance(m.group(1), m.group(2)))
                mm = METAL_RE.search(plain(m.group(2)))
                metal = metal or (mm.group(1) if mm else None)
                continue
            label, rest = lead(b)
            if label is not None:
                key = plain(label).strip().rstrip(":")
                if key == "Casting":
                    out.append(casting_head(rest))
                elif key == "Promised effect":
                    out.append(f'<div class="effect"><p><strong class="effect-cap">{label}</strong>{rest}</p></div>')
                elif key == "Caution":
                    out.append(caution_block(label, rest))
                elif key == "Note":
                    out.append(f'<p class="note"><strong class="note-cap">{label}</strong>{rest}</p>')
                elif key == "Source":
                    print(f"  {where}: a Source without a Seal")
                    out.append(provenance(rest.strip(), None))
                else:
                    print(f"  {where}: unknown label {key!r} (kept as a rubric)")
                    out.append(f'<p><strong class="rubric">{label}</strong>{rest}</p>')
                continue
            out.append(b)
        elif tag == "ol":
            out.append(render_steps(b))
        elif tag == "ul":
            out.append(render_list(b))
        elif tag == "table":
            out.append(render_table(b))
        else:
            out.append(b)
    return "\n".join(out), metal


def spell_heading(h3):
    """'9. The Soft-Butter Method (<em>nanso no hō</em> …)' -> id, number, name, term."""
    m = re.match(r"^(\d+)\.\s+(.+)$", h3, re.S)
    name, term = split_term(m.group(2) if m else h3)
    if m:
        return {"id": f"spell-{m.group(1)}", "num": m.group(1), "name": name, "term": term, "locked": False}
    return {"id": slugify(h3), "num": "", "name": name, "term": term,
            "locked": plain(name).startswith("The Locked")}


def spell_h2(s):
    parts = []
    if s["num"]:
        parts.append(f'<span class="sp-num"><span class="vh">Spell </span><span class="sp-disc">{s["num"]}'
                     f'</span><span class="vh">: </span></span>')
    elif s["locked"]:
        parts.append(f'<span class="sp-num sp-lock">{ICON_LOCK}</span>')
    parts.append(f'<span class="sp-name">{s["name"]}</span>')
    if s["term"]:
        parts.append(f'<span class="vh"> (</span><span class="sp-term">{s["term"]}</span>'
                     f'<span class="vh">)</span>')
    return "".join(parts)


def toc_item(href, s):
    lead_mark = (f'<span class="toc-n">{s["num"]}</span>' if s["num"]
                 else f'<span class="toc-n toc-lock">{ICON_LOCK}</span>')
    term = (f'<span class="vh"> (</span><span class="toc-term">{s["term"]}</span><span class="vh">)</span>'
            if s["term"] else "")
    return (f'<li><a href="{href}">{lead_mark}<span class="toc-name">{s["name"]}</span>{term}'
            f'{seal_mark(s.get("metal"))}</a></li>')


# ----------------------------------------------------------------- front and back matter

def transform_matter(blocks, chapter_files):
    """Bold paragraphs on their own become section heads; the embed becomes the timeline.
    -> (html, [(id, heading html)])"""
    out, heads, i, n = [], [], 0, len(blocks)
    while i < n:
        tag, b = blocks[i]
        if tag == "p":
            inner = p_inner(b)
            bm = BOLD_ONLY.fullmatch(inner.strip())
            if bm:
                text = bm.group(1)
                sid = slugify(text)
                heads.append((sid, text))
                nxt = blocks[i + 1] if i + 1 < n else None
                if plain(text).startswith("Plain rules") and nxt and nxt[0] in ("ul", "ol"):
                    out.append(f'<section class="caution caution-rules" aria-labelledby="{sid}">{ICON_WARN}'
                               f'<div><h2 class="caution-head" id="{sid}">{text}</h2>{render_list(nxt[1])}'
                               f'</div></section>')
                    i += 2
                    continue
                out.append(f'<h2 class="sub-head" id="{sid}">{text}</h2>')
                i += 1
                continue
            em = EMBED.fullmatch(inner.strip())
            if em:
                # the paragraph right after an embed is its caption
                cap = None
                if i + 1 < n and blocks[i + 1][0] == "p" and not lead(blocks[i + 1][1])[0]:
                    cap = p_inner(blocks[i + 1][1])
                    i += 1
                out.append(glance_figure(cap, chapter_files))
                i += 1
                continue
            if plain(inner).startswith("Sources: "):
                out.append(b.replace("<p>", '<p class="sources-line">', 1))
                i += 1
                continue
            out.append(b)
        elif tag in ("ul", "ol"):
            out.append(render_list(b))
        elif tag == "table":
            out.append(render_table(b))
        else:
            out.append(b)
        i += 1
    return "\n".join(out), heads


def build_body(html, meta, chapter_files):
    """Section HTML -> (lede text, body html, toc entries, section heads)."""
    blocks = split_blocks(html)
    intro, sections, cur = [], [], None
    for tag, b in blocks:
        if tag == "h3":
            cur = {"title": re.match(r"<h3>(.*)</h3>$", b, re.S).group(1), "blocks": []}
            sections.append(cur)
        elif cur is None:
            intro.append([tag, b])
        else:
            cur["blocks"].append([tag, b])

    parts, lede_text, heads = [], "", []
    if intro and intro[0][0] == "p" and not lead(intro[0][1])[0]:
        lede_text = plain(p_inner(intro[0][1]))
        parts.append(intro[0][1].replace("<p>", '<p class="lede">', 1))
        intro = intro[1:]
    if intro:
        body, heads = transform_matter(intro, chapter_files)
        if len(heads) > 1:
            items = "".join(f'<li><a href="#{sid}">{text}</a></li>' for sid, text in heads)
            parts.append(f'<nav class="in-book in-page" aria-label="On this page">'
                         f'<p class="in-book-cap">On this page</p><ol>{items}</ol></nav>')
        parts.append(body)

    toc, seen, rendered = [], set(), []
    for s in sections:
        s.update(spell_heading(s["title"]))
        while s["id"] in seen:
            s["id"] += "-2"
        seen.add(s["id"])
        body, s["metal"] = transform_spell(s["blocks"], f'{meta["file"]} {plain(s["name"])}')
        rendered.append((s, body))
        toc.append({k: s[k] for k in ("id", "num", "name", "term", "metal", "locked")})
    if len(toc) > 1:
        items = "".join(toc_item(f'#{t["id"]}', t) for t in toc)
        parts.append(f'<nav class="in-book" aria-label="In this chapter"><p class="in-book-cap">'
                     f'In this chapter</p><ol>{items}</ol></nav>')
    for s, body in rendered:
        cls = "spell" if s["num"] else "spell spell-plain" + (" spell-locked" if s["locked"] else "")
        parts.append(f'<section class="{cls}" aria-labelledby="{s["id"]}">'
                     f'<h2 id="{s["id"]}">{spell_h2(s)}</h2>\n{body}\n</section>')
    return lede_text, "\n".join(parts), toc, heads


# ----------------------------------------------------------------- inline pass

SPELLS_RE = re.compile(r"\bSpells? \d+(?:(?:, | and | or |–)\d+)*\b")
CHAPTER_RE = re.compile(r"\bChapter ([IVX]+)\b")
APPENDIX_RE = re.compile(r"\bAppendix ([A-Z])\b")
FOUNDATION_RE = re.compile(r"\bFoundation\b")
BEFORE_RE = re.compile(r"“(Before you cast)”")
LOCKED_RE = re.compile(r"\b(?:[Tt]he )?Locked Spells\b")


def inline_pass(html, current, files):
    """Cross-references become links. Text inside links, headings, the navigation and
    the timeline's SVG is left alone; a reference to the page itself stays text."""
    spell_files, chapter_files, appendix_files = files["spells"], files["chapters"], files["appendices"]

    def href(target, frag=""):
        if not target:
            return None
        if target == current:
            return f"#{frag}" if frag else None
        return f"{target}#{frag}" if frag else target

    def link(text, h, name=None):
        if not h:
            return text
        label = f' aria-label="{name}"' if name else ""
        return f'<a class="xref" href="{h}"{label}>{text}</a>'

    def spell_link(n, text=None):
        """A bare number ("Spells 9 and 10", "2–3") is read aloud as "Spell 9"."""
        h = href(spell_files.get(n), f"spell-{n}") if n in spell_files else None
        return link(text or n, h, None if text else f"Spell {n}")

    def spells_ref(m):
        nums = re.findall(r"\d+", m.group(0))
        if len(nums) == 1:
            return spell_link(nums[0], m.group(0))
        return re.sub(r"\d+", lambda mm: spell_link(mm.group(0)), m.group(0))

    # Appendix A: "Hakuin’s soft butter (9)" names a spell; Appendix B: "2–3" are spell numbers
    html = re.sub(r'(data-label="Old relative here">)([^<>]+?) \((\d+)\)(</td>)',
                  lambda m: f"{m.group(1)}{spell_link(m.group(3), m.group(2))} ({m.group(3)}){m.group(4)}", html)
    html = re.sub(r'(data-label="Spells">)([\d–, ]+)(</td>)',
                  lambda m: m.group(1) + re.sub(r"\d+", lambda mm: spell_link(mm.group(0)), m.group(2))
                  + m.group(3), html)

    out, skip = [], 0
    for tok in re.split(r"(<[^>]+>)", html):
        if tok.startswith("<"):
            m = re.match(r"<(/?)(a|h1|h2|h3|nav|svg|summary)\b", tok)
            if m:
                skip += -1 if m.group(1) else 1
            out.append(tok)
            continue
        if not skip:
            tok = SPELLS_RE.sub(spells_ref, tok)
            tok = LOCKED_RE.sub(lambda m: link(m.group(0), href(files["locked"], "the-locked-spells")), tok)
            tok = CHAPTER_RE.sub(lambda m: link(m.group(0), href(chapter_files.get(m.group(1)))), tok)
            tok = APPENDIX_RE.sub(lambda m: link(m.group(0), href(appendix_files.get(m.group(1)))), tok)
            tok = FOUNDATION_RE.sub(lambda m: link(m.group(0), href(files["foundation"])), tok)
            tok = BEFORE_RE.sub(lambda m: "“" + link(m.group(1), href(files["before"])) + "”", tok)
        out.append(tok)
    return "".join(out)


def check_quotes(html, where):
    """Smart quotes facing the wrong way are the usual conversion slip."""
    text = plain(html)
    bad = re.findall(r".{0,20}(?:\s”|“\s|\s’(?![0-9])).{0,20}", text)
    for b in bad:
        print(f"  quote check {where}: …{b}…")


def check_font_coverage(paths):
    """Every character a reader sees must be in the web fonts (Old East's Gentium subset);
    a missing one would be drawn in a fallback font. CJK is expected to fall back (to the
    CJK fonts book.css names). Warns, does not fail."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("font coverage: skipped (fontTools not installed)")
        return
    fonts = sorted(f for f in os.listdir(FONT_DIR) if f.endswith(".woff")) if os.path.isdir(FONT_DIR) else []
    if not fonts:
        print(f"font coverage: skipped (no fonts in {FONT_DIR})")
        return
    seen, cjk = {}, set()
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            page = fh.read()
        body = page[page.find("<body"):]
        text = plain(body) + "".join(htmlmod.unescape(v) for v in re.findall(r'(?:data-label|aria-label)="([^"]*)"', body))
        for ch in text:
            if CJK_RUN.match(ch):
                cjk.add(ch)
            elif not ch.isspace() or ch == " ":
                seen.setdefault(ch, os.path.basename(path))
    missing = []
    for name in fonts:
        cmap = TTFont(os.path.join(FONT_DIR, name)).getBestCmap()
        missing += [(name, ch) for ch in seen if ord(ch) not in cmap]
    if missing:
        print("FONT COVERAGE: characters missing from the web fonts (they fall back to system serifs):")
        for name, ch in missing:
            print(f"   U+{ord(ch):04X} {ch!r} in {name} (first on {seen[ch]})")
    else:
        print(f"font coverage: all {len(seen)} characters in {len(fonts)} fonts "
              f"(+ {len(cjk)} CJK left to the system's CJK fonts)")


def description(text, limit=155):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"
    return text


# ----------------------------------------------------------------- the emblem

def emblem(cls, variant="orn"):
    """The moon over still water, and its reflection the width of the moon. "mark" is the
    top-bar size (heavier lines, one reflection); "cover" has the glow and a halo."""
    if variant == "mark":
        return (f'<svg class="{cls}" viewBox="0 0 48 48" aria-hidden="true" focusable="false">'
                '<circle class="em-moon" cx="24" cy="16.5" r="10"/>'
                '<path class="em-water" d="M5 33H43" stroke-width="3.4"/>'
                '<path class="em-water em-r1" d="M15 41.5H33" stroke-width="3.4"/></svg>')
    glow = ""
    if variant == "cover":
        glow = ('<defs><radialGradient id="moon-glow"><stop offset="0" stop-color="#f1e5c4" stop-opacity=".34"/>'
                '<stop offset=".55" stop-color="#f1e5c4" stop-opacity=".08"/>'
                '<stop offset="1" stop-color="#f1e5c4" stop-opacity="0"/></radialGradient></defs>'
                '<circle cx="80" cy="44" r="44" fill="url(#moon-glow)"/>'
                '<circle class="em-halo" cx="80" cy="44" r="27" stroke-width=".8"/>')
    return (f'<svg class="{cls}" viewBox="0 0 160 120" aria-hidden="true" focusable="false">{glow}'
            '<circle class="em-moon" cx="80" cy="44" r="20"/>'
            '<path class="em-water" d="M10 84H150" stroke-width="1.6"/>'
            '<path class="em-water em-r1" d="M60 93H100" stroke-width="2.4"/>'
            '<path class="em-water em-r2" d="M66 101H94" stroke-width="2.4"/>'
            '<path class="em-water em-r3" d="M72 109H88" stroke-width="2.4"/></svg>')


# ----------------------------------------------------------------- templates

HEAD = """<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f5f2e9" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0e1716" media="(prefers-color-scheme: dark)">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="{author}">
<link rel="canonical" href="{url}">
<link rel="icon" href="/img/profile.png">
<link rel="alternate" type="application/rss+xml" title="Febuse — RSS" href="{site}/feed.xml">
<meta property="og:site_name" content="Febuse">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site}/img/social-card-old-stillness.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{image_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{site}/img/social-card-old-stillness.png">
<link rel="preload" href="{fonts}old-east-text-regular.woff" as="font" type="font/woff" crossorigin>
<link rel="preload" href="{fonts}old-east-text-italic.woff" as="font" type="font/woff" crossorigin>
<link rel="stylesheet" href="/old-stillness/book.css">"""

TOPBAR = """<a class="skip-link" href="#{target}">Skip to the text</a>
<header class="topbar">
  <a class="topbar-book" href="/old-stillness/" aria-label="The Spellbook of Old Stillness">{mark}<span><span class="tb-pre">The Spellbook of </span>Old Stillness</span></a>
  {controls}
</header>"""

FONT_CONTROLS = ('<span class="font-controls"><button class="font-btn" id="fontDown" type="button" '
                 'title="Smaller text" aria-label="Decrease font size">A−</button>'
                 '<button class="font-btn" id="fontUp" type="button" title="Larger text" '
                 'aria-label="Increase font size">A+</button></span>')

FOOTER = """<footer class="book-foot">
  <p class="foot-note">{transparency}</p>
  <p class="foot-links"><a href="/old-stillness/">Contents</a> · <a href="/">Febuse</a> · <a href="/privacy/">Privacy</a></p>
</footer>"""


def head_html(title, desc, url, og_type):
    return HEAD.format(csp=CSP, title=attr(title), desc=attr(desc), author=AUTHOR, url=url, site=SITE_URL,
                       og_type=og_type, og_title=attr(title), image_alt=attr(IMAGE_ALT), fonts=FONT_URL)


def nav_title(meta):
    if meta["kind"] in ("chapter", "back"):
        return f'{meta["kicker"]} · {plain(meta["name"])}'
    return plain(meta["name"])


def chapter_head(meta):
    kicker = f'<p class="kicker">{meta["kicker"]}</p>' if meta["kicker"] else ""
    name, sep, gloss = split_title(meta["name"])
    h1 = (f'<h1>{name}<span class="vh">{sep}</span><span class="h1-gloss">{gloss}</span></h1>' if gloss
          else f'<h1>{name}</h1>')
    if meta["kind"] == "chapter":
        lane = next((ln for ln in GLANCE_LANES if ln[2] == meta["num"]), None)
        count = sum(1 for t in meta["toc"] if t["num"])
        span = f' · sources from {lane[5]} to {lane[6]}' if lane else ""
        extra = (f'<p class="chapter-span">{count} spell{"s" if count != 1 else ""}{span}</p>'
                 f'{lane_strip(meta["num"])}')
    else:
        extra = f'<div class="ornament">{emblem("orn-emblem")}</div>'
    return f'<header class="chapter-head">\n{kicker}{h1}\n{extra}\n</header>'


def render_page(meta, body, prev_meta, next_meta, desc):
    title = f"{nav_title(meta)} — {SHORT}"
    url = f"{SITE_URL}{BASE}{meta['file']}"
    head = head_html(title, desc, url, "article")
    rel = ""
    if prev_meta:
        rel += f'\n<link rel="prev" href="{prev_meta["file"]}">'
    if next_meta:
        rel += f'\n<link rel="next" href="{next_meta["file"]}">'

    def pager_link(m, cls, direction):
        if not m:
            return f'<span class="{cls} pager-empty"></span>'
        return (f'<a class="{cls}" href="{m["file"]}" rel="{direction}">'
                f'<span class="pager-dir">{"Previous" if direction == "prev" else "Next"}</span>'
                f'<span class="pager-title">{nav_title(m)}</span></a>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{head}{rel}
</head>
<body class="page-{meta['kind']}">
{TOPBAR.format(target="text", mark=emblem("mark", "mark"), controls=FONT_CONTROLS)}
<main id="text" class="book-text">
{chapter_head(meta)}
{body}
</main>
<nav class="pager" aria-label="Pages">
  {pager_link(prev_meta, "pager-prev", "prev")}
  <a class="pager-toc" href="/old-stillness/">Contents</a>
  {pager_link(next_meta, "pager-next", "next")}
</nav>
{FOOTER.format(transparency=TRANSPARENCY)}
<script src="/js/reader-font.js"></script>
</body>
</html>
"""


def render_cover(title, intro, date, pages, blurb, total_words):
    desc = ("Thirty-four meditation techniques from China, Japan, Tibet, India, Greece and Rome, "
            "the Christian desert and cloister and the Sufis, each traced to a named text or teacher "
            "from before 1800, with its method, its seal of provenance and its cautions. Free to read online.")
    url = f"{SITE_URL}{BASE}"
    head = head_html(title, desc, url, "book")
    chapters = [p for p in pages if p["kind"] == "chapter"]
    n_spells = sum(1 for p in chapters for t in p["toc"] if t["num"])
    total_min = minutes(total_words)
    reading = f"about {total_min // 60} h {total_min % 60:02d} min" if total_min >= 60 else f"about {total_min} min"
    # the intro paragraph: its first sentence under the title, the rest under that
    intro_html = md_inline(" ".join(intro))
    sub_main, _, sub_rest = intro_html.partition(". ")
    sub_html = f'<p class="cover-sub">{sub_main}.</p>' + (f'<p class="cover-sub2">{sub_rest}</p>' if sub_rest else "")

    groups = [("front", "Before the spells"),
              ("chapter", "The seven traditions" if len(chapters) == 7 else f"The {len(chapters)} traditions"),
              ("back", "At the back")]
    toc = []
    for kind, label in groups:
        items = []
        for p in (p for p in pages if p["kind"] == kind):
            if kind == "chapter":
                entries = "".join(toc_item(f'{p["file"]}#{t["id"]}', t) for t in p["toc"])
                sub = f'<ol class="toc-entries">{entries}</ol>' if entries else ""
            else:
                entries = ' <span class="sep" aria-hidden="true">·</span> '.join(
                    f'<a href="{p["file"]}#{sid}">{text}</a>' for sid, text in p["heads"])
                sub = f'<p class="toc-sections">{entries}</p>' if entries else ""
            items.append(
                f'<li><a class="toc-row" href="{p["file"]}"><span class="toc-num">{p["num"]}</span>'
                f'<span class="toc-title">{p["name"]}</span>'
                f'<span class="toc-time">{minutes(p["words"])} min</span></a>{sub}</li>')
        toc.append(f'<h3 class="toc-group">{label}</h3><ol class="toc toc-{kind}">{"".join(items)}</ol>')

    ld = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": title,
        "alternativeHeadline": plain(intro_html),
        "author": {"@type": "Person", "name": AUTHOR, "url": f"{SITE_URL}/"},
        "datePublished": date.isoformat(),
        "inLanguage": "en",
        "url": url,
        "bookFormat": "https://schema.org/EBook",
        "isAccessibleForFree": True,
        "hasPart": [{"@type": "Chapter", "name": nav_title(p), "url": f"{url}{p['file']}"} for p in pages],
    }
    ld_json = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    front = (f'---\nlayout: null\ntitle: "{title}"\n'
             f'description: "{desc}"\n'
             f"lang: en\ndate_published: {date.isoformat()}\nfeed_category: Book\n---\n")
    first = pages[0]["file"]
    date_label = f"{date.day} {date.strftime('%B')} {date.year}"
    return front + "{% raw %}" + f"""<!DOCTYPE html>
<html lang="en">
<head>
{head}
<script type="application/ld+json">{ld_json}</script>
</head>
<body class="page-cover">
<a class="skip-link" href="#contents">Skip to the contents</a>
<header class="topbar topbar-cover">
  <a class="topbar-back" href="/">← Febuse</a>
</header>
<div class="cover">
  <div class="cover-inner">
    {emblem("cover-emblem", "cover")}
    <h1>{title}</h1>
    {sub_html}
    <p class="cover-byline"><span>{AUTHOR}</span><span class="by-sep" aria-hidden="true"> · </span><span>{date_label}</span></p>
  </div>
</div>
<main id="contents" class="book-text cover-main">
{EPIGRAPH}
<p class="cover-blurb">{blurb}</p>
<p class="cover-actions"><a class="btn-begin" href="{first}">Begin reading</a></p>
<p class="cover-facts">{len(chapters)} traditions · {n_spells} spells · {total_words:,} words · {reading}</p>
<p class="cover-note">{TRANSPARENCY_COVER}</p>
<h2 class="contents-title">Contents</h2>
{"".join(toc)}
</main>
<footer class="book-foot">
  <p class="foot-links"><a href="/">Febuse</a> · <a href="/privacy/">Privacy</a> · <a href="/feed.xml">RSS</a></p>
</footer>
</body>
</html>
""" + "{% endraw %}\n"


# ----------------------------------------------------------------- build

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC, help="the book's Markdown file")
    args = ap.parse_args()
    if not os.path.isfile(args.src):
        sys.stderr.write(f"ERROR: missing {args.src}\n")
        return 1
    with open(args.src, encoding="utf-8") as fh:
        title, date, intro, sections = parse_book(fh.read())

    pages = []
    for s in sections:
        meta = page_meta(s["heading"])
        meta["html"] = tag_cjk(md_to_html(s["md"]), CJK_LANG.get(meta["plain_name"]), meta["file"])
        pages.append(meta)
    chapter_files = {p["num"]: p["file"] for p in pages if p["kind"] == "chapter"}

    total_words = 0
    for p in pages:
        p["lede"], p["body"], p["toc"], p["heads"] = build_body(p["html"], p, chapter_files)
        p["words"] = word_count(p["html"])
        total_words += p["words"]
    files = {
        "spells": {t["num"]: p["file"] for p in pages for t in p["toc"] if t["num"]},
        "chapters": chapter_files,
        "appendices": {p["num"]: p["file"] for p in pages if p["kind"] == "back"},
        "foundation": FRONT["The Foundation: the seat"] + ".html",
        "before": FRONT["Before you cast"] + ".html",
        "locked": next((p["file"] for p in pages for t in p["toc"] if t.get("locked")), None),
    }
    blurb = ""
    for p in pages:
        p["body"] = inline_pass(p["body"], p["file"], files)
        check_quotes(p["body"], p["file"])
        if p["file"] == FRONT["How to read this book"] + ".html":
            blurb = re.search(r'<p class="lede">(.*?)</p>', p["body"], re.S).group(1)

    for i, p in enumerate(pages):
        prev_meta = pages[i - 1] if i > 0 else None
        next_meta = pages[i + 1] if i + 1 < len(pages) else None
        html = render_page(p, p["body"], prev_meta, next_meta, description(p["lede"]))
        with open(os.path.join(BOOK_DIR, p["file"]), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html)

    with open(os.path.join(BOOK_DIR, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_cover(title, intro, date, pages, blurb, total_words))

    with open(DATA_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump([{"file": p["file"], "title": nav_title(p), "kind": p["kind"]} for p in pages],
                  fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # stale pages: every .html here is generated, so anything not in the book goes
    kept = {p["file"] for p in pages} | {"index.html"}
    for name in os.listdir(BOOK_DIR):
        if name.endswith(".html") and name not in kept:
            os.remove(os.path.join(BOOK_DIR, name))

    # link audit: every in-book href must hit a page and, with a #fragment, an id
    ids = {}
    for name in kept:
        with open(os.path.join(BOOK_DIR, name), encoding="utf-8") as fh:
            ids[name] = (fh.read(), set())
        ids[name][1].update(re.findall(r'\bid="([^"]+)"', ids[name][0]))
    broken = []
    for name, (text, _own) in ids.items():
        for href in re.findall(r'href="([^"]*)"', text):
            if href.startswith(("http", "/", "mailto:")):
                continue
            target, _, frag = href.partition("#")
            target = target or name
            if target not in ids or (frag and frag not in ids[target][1]):
                broken.append(f"{name}: {href!r}")
    n_spells = sum(1 for p in pages for t in p["toc"] if t["num"])
    print(f"pages written: {len(pages)} + index.html ({n_spells} spells)")
    print(f"words:         {total_words:,} (~{minutes(total_words)} min)")
    check_font_coverage([os.path.join(BOOK_DIR, name) for name in sorted(kept)])
    if broken:
        print("BROKEN LINKS:")
        for b in broken:
            print("  ", b)
        return 1
    print("link audit:    clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
