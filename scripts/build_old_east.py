#!/usr/bin/env python3
"""Build the web edition of THE OLD BOOK OF THE EAST for infuscy.github.io.

Source: old-east/the-old-book-of-the-east.md, the book's Markdown (kept in the
repo, excluded from the site by _config.yml). Each `##` section becomes one
reader page in old-east/:

    introduction.html   "Before you begin: what "old" means here"
    anatomy.html        "The anatomy of an Eastern charm"
    calendar.html       "The calendar of power"
    book-1.html …       "Book I — Charms against the eye, fright and fever" …
    bestiary.html       "Bestiary — who walks at night"
    sources.html        "Sources and further reading"

plus old-east/index.html (cover and contents, with Jekyll front matter so the
book is in feed.xml and the sitemap) and _data/old_east_pages.json (the page
list the sitemap reads).

The text is never rewritten, only marked up for reading:
  * "### I.1 Name — gloss"      -> the entry head: number, name, gloss on its own line
  * the italic line under it    -> where it was recorded and what it is for (.where)
  * "You need:"                 -> the materials panel
  * numbered steps              -> ol.steps
  * "The words …"               -> the words, set as an embroidered ritual towel; a
    charm given as blockquotes is set line by line, the original beside its English
  * "Age: <rating>."            -> the evidence note, with a four-diamond gauge for
    the rating (ancient root, medieval / early modern, folk-recorded, local)
  * "Safety…"                   -> a warning callout
  * other bold leads            -> red small-capital rubrics
  * "I.4", "Book V"             -> links to that entry or book
  * Romanian words in italics   -> lang="ro"; Cyrillic -> lang="bg"/"ru"
  * tables                      -> data-label cells that stack on phones

The pages share old-east/book.css (hand-written: this script never touches it)
and /js/reader-font.js (the A-/A+ buttons). CSP is script-src 'self' and
style-src 'self': the pages carry no inline scripts or styles.

Usage:
    py scripts/build_old_east.py [--src path/to/book.md]

Requires Python 3 + the `markdown` package (pip install markdown).
"""
import argparse
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

sys.dont_write_bytecode = True  # importing the stitches module must not leave __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import old_east_stitches as stitches  # noqa: E402

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOOK_DIR = os.path.join(SITE_ROOT, "old-east")
DEFAULT_SRC = os.path.join(BOOK_DIR, "the-old-book-of-the-east.md")
DATA_JSON = os.path.join(SITE_ROOT, "_data", "old_east_pages.json")

SITE_URL = "https://infuscy.github.io"
BASE = "/old-east/"
SHORT = "The Old Book of the East"
AUTHOR = "Buse Florin-Emilian"
PUBLISHED = "2026-11-23"
PUBLISHED_LABEL = "23 November 2026"
WORDS_PER_MINUTE = 230

# Sections outside the six books: heading -> (kind, page file stem).
SECTIONS = {
    'Before you begin: what "old" means here': ("front", "introduction"),
    "The anatomy of an Eastern charm": ("front", "anatomy"),
    "The calendar of power": ("front", "calendar"),
    "Bestiary — who walks at night": ("back", "bestiary"),
    "Sources and further reading": ("back", "sources"),
}

# Voluntary AI transparency note (EU AI Act art. 50; see CLAUDE.md, Compliance):
# in every page's footer, and on the cover with the article reference.
TRANSPARENCY = (
    "<strong>Transparency:</strong> this book was compiled and its English renderings "
    "drafted with the help of an AI system (Claude), working from the collections and "
    "studies listed in <a href=\"sources.html\">Sources and further reading</a>; the author "
    "reviewed the text against those sources before publication. Editorial responsibility: "
    f"{AUTHOR} (<a href=\"/#contact\">contact</a>)."
)
TRANSPARENCY_COVER = (TRANSPARENCY + " A transparency statement under Article 50 of "
                      "Regulation (EU) 2024/1689 (the AI Act).")

# The cover's epigraph: the seal of a Romanian charm, from "The anatomy of an Eastern charm".
EPIGRAPH = ('<figure class="epigraph"><blockquote><p lang="ro">De la mine descântecul, '
            'de la Dumnezeu leacul.</p><p class="epigraph-tr">“From me the charm, from God the cure.”'
            '</p></blockquote><figcaption>the last words of a Romanian charm</figcaption></figure>')

# The share image (img/social-card-old-east.png) is made by scripts/make_old_east_card.py.
IMAGE_ALT = ("The Old Book of the East: the title in linen white on madder red, under an "
             "embroidered rhombus, between two cross-stitched bands of diamonds")

CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "font-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'; connect-src 'self'")

ICON_WARN = ('<svg class="safety-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
             'stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round">'
             '<path d="M12 3.5L21.5 20h-19z"/><path d="M12 10v4.5"/><path d="M12 17.3v.2"/></svg>')

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}
RO_LETTERS = re.compile(r"[ăâîșțĂÂÎȘȚ]")

# The evidence ratings of "Before you begin", strongest first: (class, depth of the gauge).
RATINGS = (("ancient", 4, re.compile(r"^ancient", re.I)),
           ("medieval", 3, re.compile(r"medieval|early modern", re.I)),
           ("folk", 2, re.compile(r"^folk", re.I)),
           ("local", 1, re.compile(r"local|revived", re.I)))


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


def rating_class(rating):
    """'Medieval / early modern' -> ('medieval', 3), judged on the rating's first clause."""
    head = re.split(r"[;,]", rating, maxsplit=1)[0]
    for cls, depth, pat in RATINGS:
        if pat.search(head):
            return cls, depth
    return "folk", 2


def gauge(depth):
    marks = "".join('<i class="on"></i>' if k < depth else "<i></i>" for k in range(4))
    return f'<span class="gauge" aria-hidden="true">{marks}</span>'


# ----------------------------------------------------------------- source

def parse_book(text):
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    m = re.match(r"# (.+)", lines[0])
    if not m:
        raise SystemExit("ERROR: the source must start with '# <title>'")
    title = m.group(1).strip()
    first_h2 = next(i for i, ln in enumerate(lines) if ln.startswith("## "))
    head = [ln.strip() for ln in lines[1:first_h2] if ln.strip()]
    subtitle = head[0].strip("*") if head else ""
    sections, cur = [], None
    for ln in lines[first_h2:]:
        if ln.startswith("## "):
            cur = {"heading": ln[3:].strip(), "md": []}
            sections.append(cur)
        else:
            cur["md"].append(ln)
    for s in sections:
        s["md"] = "\n".join(s["md"]).strip() + "\n"
    return title, subtitle, sections


SMARTY_ENTITIES = {"&ldquo;": "“", "&rdquo;": "”", "&lsquo;": "‘",
                   "&rsquo;": "’", "&hellip;": "…", "&ndash;": "–",
                   "&mdash;": "—", "&laquo;": "«", "&raquo;": "»"}


def md_to_html(src):
    # Verse line breaks are a trailing backslash (CommonMark); Python-Markdown wants two spaces.
    src = re.sub(r"(?<!\\)\\$", "  ", src, flags=re.M)
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


def split_title(s):
    """'Name — gloss' or 'Name: gloss' -> (name, separator, gloss)."""
    m = re.match(r"^(.*?)( — |: )(.+)$", s)
    return (m.group(1), m.group(2), m.group(3)) if m else (s, "", "")


def page_meta(heading):
    m = re.match(r"Book ([IVX]+) — (.+)$", heading)
    if m:
        n = roman_to_int(m.group(1))
        return {"kind": "book", "num": m.group(1), "n": n, "name": md_inline(m.group(2)),
                "kicker": f"Book {m.group(1)}", "file": f"book-{n}.html"}
    if heading in SECTIONS:
        kind, stem = SECTIONS[heading]
        return {"kind": kind, "num": "", "n": "", "name": md_inline(heading), "kicker": "",
                "file": stem + ".html"}
    raise SystemExit(f"ERROR: unknown section heading {heading!r} (add it to SECTIONS)")


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
WHOLE_EM = re.compile(r"<em>((?:(?!</?em>).)*)</em>", re.S)


def lead(block):
    """(label, rest) when a paragraph opens with a bold label, else (None, None)."""
    m = LEAD_STRONG.match(p_inner(block))
    return (m.group(1), m.group(2)) if m else (None, None)


def region_lang(where):
    """The language of an entry's charms when the words do not say: its first country."""
    first = plain(where).split(",")[0].split(".")[0].split(";")[0].strip().lower()
    return "ro" if first.startswith(("romania", "moldova")) else None


def guess_lang(text, default):
    """Language of an original line: Romanian letters or the entry's country; a
    transliteration (Russian, Bulgarian …) gets no tag, which reads better aloud."""
    t = plain(text)
    if RO_LETTERS.search(t):
        return "ro"
    if re.search(r"\w’\w|\w’(?=[\s,.!?]|$)|zh|kh|shch", t, re.I):
        return None
    return default


def verse_groups(quotes):
    """Blockquotes -> one [(is_original, html)] list per stanza. Python-Markdown merges
    blockquotes that only a blank line separates, so the stanza (<p>) is the unit."""
    groups = []
    for block in quotes:
        inner = re.sub(r"^<blockquote>\s*|\s*</blockquote>$", "", block, flags=re.S)
        for para in re.findall(r"<p>(.*?)</p>", inner, re.S):
            lines = []
            for line in re.split(r"<br />\s*", para.strip()):
                line = line.strip()
                m = WHOLE_EM.fullmatch(line)
                lines.append((True, m.group(1)) if m else (False, line))
            groups.append(lines)
    return groups


def charm_pairs(quotes, default_lang):
    """Blockquotes -> [(original, translation, lang)], or None when the lines do not
    pair up (they are then set as they stand)."""
    groups = verse_groups(quotes)
    pairs, k = [], 0
    while k < len(groups):
        g = groups[k]
        nxt = groups[k + 1] if k + 1 < len(groups) else None
        # all originals, then all translations, line for line (I.1)
        if (all(o for o, _ in g) and nxt and not any(o for o, _ in nxt) and len(g) == len(nxt)):
            pairs += [(a, b) for (_, a), (_, b) in zip(g, nxt)]
            k += 2
            continue
        # original, translation, original, translation … in one quote (I.3)
        if len(g) % 2 == 0 and all(g[j][0] and not g[j + 1][0] for j in range(0, len(g), 2)):
            pairs += [(g[j][1], g[j + 1][1]) for j in range(0, len(g), 2)]
            k += 1
            continue
        return None
    return [(a, b, guess_lang(a, default_lang)) for a, b in pairs]


def render_pairs(pairs):
    rows = []
    for orig, tr, lang in pairs:
        lang_attr = f' lang="{lang}"' if lang else ""
        rows.append(f'<div class="pair"><p class="orig"{lang_attr}>{orig}</p><p class="tr">{tr}</p></div>')
    return f'<div class="charm">{"".join(rows)}</div>'


def render_quotes_plain(quotes):
    """Blockquotes that do not pair up: kept as verse, line by line."""
    out = []
    for g in verse_groups(quotes):
        lines = "".join(f'<span class="l{" orig" if o else ""}">{t}</span>' for o, t in g)
        out.append(f'<p class="verse">{lines}</p>')
    return "".join(out)


def words_panel(label, rest, quotes, default_lang):
    """'The words' + its note or its prose, + the blockquotes that follow."""
    rest = rest.strip()
    note, body = "", rest
    m = re.match(r"^\(([^)]*)\)\s*:?\s*(.*)$", rest, re.S)
    if m:
        note, body = m.group(1), m.group(2)
    body = re.sub(r"^[.:]\s*", "", body)
    cap = '<span class="cap-label">The words</span>'
    if note:
        cap += f' <span class="cap-note">{note}</span>'
    inner = ""
    # "(composite): *original* “translation”" — one line, set as a pair (I.6)
    pm = re.fullmatch(r"<em>((?:(?!</?em>).)+)</em>\s*(“.+”)\.?", body, re.S)
    if pm and not quotes:
        inner = render_pairs([(pm.group(1), pm.group(2), guess_lang(pm.group(1), default_lang))])
    elif body:
        inner = f"<p>{body}</p>"
    if quotes:
        pairs = charm_pairs(quotes, default_lang)
        inner += render_pairs(pairs) if pairs else render_quotes_plain(quotes)
    wide = " words-pairs" if 'class="charm"' in inner else ""
    return f'<figure class="words{wide}"><figcaption>{cap}</figcaption>{inner}</figure>'


def age_block(label, rest):
    rating = re.sub(r"^Age:\s*", "", plain(label)).strip().rstrip(".")
    cls, depth = rating_class(rating)
    rating_html = re.sub(r"^Age:\s*", "", label).strip()
    rating_html = re.sub(r"\.$", "", rating_html)
    return (f'<div class="age age-{cls}" role="note"><p class="age-head">'
            f'<span class="age-cap">Age<span class="vh">:</span></span> {gauge(depth)} '
            f'<span class="age-rating">{rating_html}</span></p><p>{rest.strip()}</p></div>')


def safety_block(label, rest):
    return (f'<div class="safety" role="note">{ICON_WARN}<p><strong class="safety-cap">{label}</strong>'
            f'{rest}</p></div>')


def render_list(block, ordered_cls=None):
    block = block.replace("<li><strong>", '<li><strong class="rubric">')
    if ordered_cls and block.startswith("<ol>"):
        block = f'<ol class="{ordered_cls}">' + block[len("<ol>"):]
    return block


CYRILLIC_RUN = re.compile(r"[Ѐ-ӿ](?:[Ѐ-ӿ\s!?,.–—-]*[Ѐ-ӿ!?.])?")


def cyrillic_lang(text):
    if re.search(r"[ыэё]", text, re.I):
        return "ru"
    if re.search(r"ъ\w|ѝ", text, re.I):
        return "bg"
    return "ru"


def render_table(block):
    heads = [plain(h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", block, re.S)]
    kind = {"Rating": "ratings", "Date": "calendar", "Language": "curses", "Being": "bestiary"}.get(
        heads[0] if heads else "", "")

    def row(m):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), re.S)
        first = plain(cells[0]).strip() if cells else ""
        out = []
        for k, c in enumerate(cells):
            label = heads[k] if k < len(heads) else ""
            if kind == "ratings" and k == 0:
                c = gauge(rating_class(first)[1]) + " " + c
            if kind == "curses" and k == 1:
                lang = {"Romanian": "ro", "Serbian": "sr-Latn"}.get(first)
                if lang:
                    c = f'<span lang="{lang}">{c}</span>'
            out.append(f'<td role="cell" data-label="{attr(label)}">{c}</td>')
        return '<tr role="row">' + "".join(out) + "</tr>"

    block = re.sub(r"<tr>\s*(<td.*?)</tr>", row, block, flags=re.S)
    block = (block.replace("<table>", f'<table role="table"{f" class={chr(34)}{kind}{chr(34)}" if kind else ""}>')
             .replace("<thead>", '<thead role="rowgroup">')
             .replace("<tbody>", '<tbody role="rowgroup">')
             .replace("<th>", '<th role="columnheader">')
             .replace("<tr>", '<tr role="row">'))
    # the four-column tables widen past the text column on large screens
    wide = " table-wide" if kind in ("calendar", "bestiary") else ""
    return f'<div class="table-wrap{wide}">{block}</div>'


def transform(blocks, entry=None):
    """Mark up one run of blocks (an entry's body, or a page's text outside the entries)."""
    out, i, n = [], 0, len(blocks)
    default_lang = None
    while i < n:
        tag, b = blocks[i]
        if tag == "p":
            inner = p_inner(b)
            label, rest = lead(b)
            m = WHOLE_EM.fullmatch(inner)
            if entry is not None and i == 0 and m:
                default_lang = region_lang(m.group(1))
                out.append(f'<p class="where">{m.group(1)}</p>')
                i += 1
                continue
            if label is not None:
                key = plain(label).strip()
                if key.startswith("You need"):
                    out.append(f'<div class="need"><p><strong class="rubric">{label}</strong>{rest}</p></div>')
                    i += 1
                    continue
                if key.startswith("The words"):
                    j = i + 1
                    while j < n and blocks[j][0] == "blockquote":
                        j += 1
                    out.append(words_panel(label, rest, [q for _, q in blocks[i + 1:j]], default_lang))
                    i = j
                    continue
                if key.startswith("Age:"):
                    out.append(age_block(label, rest))
                    i += 1
                    continue
                if key.startswith("Safety"):
                    out.append(safety_block(label, rest))
                    i += 1
                    continue
                if not rest.strip():
                    # a label on its own line introduces the list or table after it
                    out.append(f'<p class="rubric-head"><strong class="rubric">{label}</strong></p>')
                else:
                    out.append(f'<p><strong class="rubric">{label}</strong>{rest}</p>')
                i += 1
                continue
            out.append(b)
            i += 1
            continue
        if tag == "blockquote":
            j = i
            while j < n and blocks[j][0] == "blockquote":
                j += 1
            quotes = [q for _, q in blocks[i:j]]
            pairs = charm_pairs(quotes, default_lang)
            out.append('<figure class="words words-pairs">'
                       + (render_pairs(pairs) if pairs else render_quotes_plain(quotes)) + "</figure>")
            i = j
            continue
        if tag == "ol":
            out.append(render_list(b, "steps" if entry is not None else "parts"))
        elif tag == "ul":
            out.append(render_list(b))
        elif tag == "table":
            out.append(render_table(b))
        else:
            out.append(b)
        i += 1
    return "\n".join(out)


def entry_heading(h3_html):
    """'I.1 Descântecul de deochi — lifting the evil eye' -> (id, number, name, sep, gloss)."""
    m = re.match(r"^([IVX]+)\.(\d+)\s+(.+)$", h3_html, re.S)
    if not m:
        name, sep, gloss = split_title(h3_html)
        return slugify(h3_html), "", name, sep, gloss
    num = f"{m.group(1)}.{m.group(2)}"
    name, sep, gloss = split_title(m.group(3))
    return f"{m.group(1).lower()}-{m.group(2)}", num, name, sep, gloss


def heading_html(num, name, sep, gloss):
    parts = []
    if num:
        parts.append(f'<span class="e-num">{num}</span><span class="vh"> </span>')
    parts.append(f'<span class="e-name">{name}</span>')
    if gloss:
        parts.append(f'<span class="vh">{sep}</span><span class="e-gloss">{gloss}</span>')
    return "".join(parts)


def build_body(html, meta):
    """Section HTML -> (lede text, body html, [(title html, id, number, name)] of its entries)."""
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

    parts, lede_text = [], ""
    if intro and intro[0][0] == "p" and not lead(intro[0][1])[0]:
        lede_text = plain(p_inner(intro[0][1]))
        parts.append(intro[0][1].replace("<p>", '<p class="lede">', 1))
        intro = intro[1:]
    if intro:
        parts.append(transform(intro))

    toc, seen = [], set()
    for s in sections:
        sid, num, name, sep, gloss = entry_heading(s["title"])
        while sid in seen:
            sid += "-2"
        seen.add(sid)
        s.update(id=sid, num=num, name=name, sep=sep, gloss=gloss)
        toc.append({"id": sid, "num": num, "name": name, "gloss": gloss})
    if len(toc) > 1:
        label = "In this book" if meta["kind"] == "book" else "On this page"
        items = "".join(
            f'<li><a href="#{t["id"]}">'
            + (f'<span class="toc-n">{t["num"]}</span> ' if t["num"] else "")
            + f'<span class="toc-name">{t["name"]}</span>'
            + (f'<span class="vh"> — </span><span class="toc-gloss">{t["gloss"]}</span>' if t["gloss"] else "")
            + "</a></li>" for t in toc)
        parts.append(f'<nav class="in-book" aria-label="{label}"><p class="in-book-cap">{label}</p>'
                     f'<ol>{items}</ol></nav>')
    for s in sections:
        is_entry = bool(s["num"])
        head = heading_html(s["num"], s["name"], s["sep"], s["gloss"])
        body = transform(s["blocks"], entry=s["num"] if is_entry else None)
        cls = "entry" if is_entry else "entry entry-plain"
        parts.append(f'<section class="{cls}" aria-labelledby="{s["id"]}">'
                     f'<h2 id="{s["id"]}">{head}</h2>\n{body}\n</section>')
    return lede_text, "\n".join(parts), toc


# ----------------------------------------------------------------- inline pass

def inline_pass(html, current, book_files, entry_files):
    """Cross-references become links, Romanian italics get lang="ro", Cyrillic runs
    their language. Text inside links, headings and captions is left alone."""
    def entry_ref(m):
        key = f"{m.group(1).lower()}-{m.group(2)}"
        target = entry_files.get(key)
        if not target:
            return m.group(0)
        href = f"#{key}" if target == current else f"{target}#{key}"
        return f'<a class="xref" href="{href}">{m.group(0)}</a>'

    def book_ref(m):
        target = book_files.get(roman_to_int(m.group(1)))
        if not target or target == current:
            return m.group(0)
        return f'<a class="xref" href="{target}">{m.group(0)}</a>'

    out, skip = [], 0
    for tok in re.split(r"(<[^>]+>)", html):
        if tok.startswith("<"):
            m = re.match(r"<(/?)(a|h1|h2|figcaption|nav)\b", tok)
            if m:
                skip += -1 if m.group(1) else 1
            out.append(tok)
            continue
        if not skip:
            tok = re.sub(r"\b([IVX]+)\.(\d+)\b", entry_ref, tok)
            tok = re.sub(r"\bBook ([IVX]+)\b", book_ref, tok)
        tok = CYRILLIC_RUN.sub(lambda m: f'<span lang="{cyrillic_lang(m.group(0))}">{m.group(0)}</span>', tok)
        out.append(tok)
    html = "".join(out)
    # Romanian words in italics (their letters ă â î ș ț are Romanian only here)
    return re.sub(r"<em>((?:(?!</?em>).)*)</em>",
                  lambda m: f'<em lang="ro">{m.group(1)}</em>' if RO_LETTERS.search(plain(m.group(1)))
                  else m.group(0), html, flags=re.S)


def check_quotes(html, where):
    """Smart quotes facing the wrong way are the usual conversion slip."""
    text = plain(html)
    bad = re.findall(r".{0,20}(?:\s”|“\s|\s’(?![0-9])).{0,20}", text)
    for b in bad:
        print(f"  quote check {where}: …{b}…")


def check_font_coverage(paths):
    """Every character a reader sees must be in old-east/fonts (a subset of Gentium
    Book Plus, see scripts/subset_old_east_fonts.py); a missing one would be drawn
    in a fallback font. Warns, does not fail: re-run the subsetter with a wider range."""
    font_dir = os.path.join(BOOK_DIR, "fonts")
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("font coverage: skipped (fontTools not installed)")
        return
    fonts = sorted(f for f in os.listdir(font_dir) if f.endswith(".woff")) if os.path.isdir(font_dir) else []
    if not fonts:
        print("font coverage: skipped (no fonts in old-east/fonts)")
        return
    seen = {}
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            page = fh.read()
        body = page[page.find("<body"):]
        text = plain(body) + "".join(htmlmod.unescape(v) for v in re.findall(r'data-label="([^"]*)"', body))
        for ch in text:
            if not ch.isspace() or ch == " ":
                seen.setdefault(ch, os.path.basename(path))
    missing = []
    for name in fonts:
        cmap = TTFont(os.path.join(font_dir, name)).getBestCmap()
        missing += [(name, ch) for ch in seen if ord(ch) not in cmap]
    if missing:
        print("FONT COVERAGE: characters missing from the web fonts (they fall back to system serifs):")
        for name, ch in missing:
            print(f"   U+{ord(ch):04X} {ch!r} in {name} (first on {seen[ch]})")
    else:
        print(f"font coverage: all {len(seen)} characters in {len(fonts)} fonts")


def description(text, limit=155):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"
    return text


# ----------------------------------------------------------------- templates

HEAD = """<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f8f4ec" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#161211" media="(prefers-color-scheme: dark)">
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
<meta property="og:image" content="{site}/img/social-card-old-east.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{image_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{site}/img/social-card-old-east.png">
<link rel="preload" href="/old-east/fonts/old-east-text-regular.woff" as="font" type="font/woff" crossorigin>
<link rel="preload" href="/old-east/fonts/old-east-text-italic.woff" as="font" type="font/woff" crossorigin>
<link rel="stylesheet" href="/old-east/book.css">"""

TOPBAR = """<a class="skip-link" href="#{target}">Skip to the text</a>
<header class="topbar">
  <a class="topbar-book" href="/old-east/">{mark}<span>The Old Book of the East</span></a>
  {controls}
</header>"""

FONT_CONTROLS = ('<span class="font-controls"><button class="font-btn" id="fontDown" type="button" '
                 'title="Smaller text" aria-label="Decrease font size">A−</button>'
                 '<button class="font-btn" id="fontUp" type="button" title="Larger text" '
                 'aria-label="Increase font size">A+</button></span>')

FOOTER = """<footer class="book-foot">
  <p class="foot-note">{transparency}</p>
  <p class="foot-links"><a href="/old-east/">Contents</a> · <a href="/">Febuse</a> · <a href="/privacy/">Privacy</a></p>
</footer>"""


def nav_title(meta):
    if meta["kind"] == "book":
        return f'{meta["kicker"]} · {plain(meta["name"])}'
    return plain(meta["name"])


def h1_html(meta):
    if meta["kind"] == "book":
        return f'<h1>{meta["name"]}</h1>'
    name, sep, gloss = split_title(meta["name"])
    if not gloss:
        return f"<h1>{name}</h1>"
    return f'<h1>{name}<span class="vh">{sep}</span><span class="h1-gloss">{gloss}</span></h1>'


def render_page(meta, body, prev_meta, next_meta, desc):
    title = f"{nav_title(meta)} — {SHORT}"
    url = f"{SITE_URL}{BASE}{meta['file']}"
    head = HEAD.format(csp=CSP, title=attr(title), desc=attr(desc), author=AUTHOR, url=url,
                       site=SITE_URL, og_type="article", og_title=attr(title),
                       image_alt=attr(IMAGE_ALT))
    rel = ""
    if prev_meta:
        rel += f'\n<link rel="prev" href="{prev_meta["file"]}">'
    if next_meta:
        rel += f'\n<link rel="next" href="{next_meta["file"]}">'
    kicker = f'<p class="kicker">{meta["kicker"]}</p>' if meta["kicker"] else ""

    def pager_link(m, cls, direction):
        if not m:
            return f'<span class="{cls} pager-empty"></span>'
        return (f'<a class="{cls}" href="{m["file"]}" rel="{direction}">'
                f'<span class="pager-dir">{"Previous" if direction == "prev" else "Next"}</span>'
                f'<span class="pager-title">{nav_title(m)}</span></a>')

    mark = stitches.inline_svg("mini", "mark")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{head}{rel}
</head>
<body class="page-{meta['kind']}">
{TOPBAR.format(target="text", mark=mark, controls=FONT_CONTROLS)}
<main id="text" class="book-text">
<header class="chapter-head">
{kicker}{h1_html(meta)}
<div class="band-ornament" aria-hidden="true"></div>
</header>
{body}
</main>
<nav class="pager" aria-label="Pages">
  {pager_link(prev_meta, "pager-prev", "prev")}
  <a class="pager-toc" href="/old-east/">Contents</a>
  {pager_link(next_meta, "pager-next", "next")}
</nav>
{FOOTER.format(transparency=TRANSPARENCY)}
<script src="/js/reader-font.js"></script>
</body>
</html>
"""


def render_cover(title, subtitle, pages, blurb, total_words):
    desc = ("Charms, curses and rites from Romania, the Balkans and the Slavic lands, each with "
            "the evidence for how old it really is: village charmers' words in English beside "
            "the originals, with the rite, its season and its sources. Free to read online.")
    url = f"{SITE_URL}{BASE}"
    head = HEAD.format(csp=CSP, title=attr(title), desc=attr(desc), author=AUTHOR, url=url,
                       site=SITE_URL, og_type="book", og_title=attr(title),
                       image_alt=attr(IMAGE_ALT))
    books = [p for p in pages if p["kind"] == "book"]
    n_entries = sum(len(p["toc"]) for p in books)
    total_min = minutes(total_words)
    reading = f"about {total_min // 60} h {total_min % 60:02d} min" if total_min >= 60 else f"about {total_min} min"
    sub_main, _, sub_rest = subtitle.partition(" — ")

    groups = [("front", "Before the charms"), ("book", "The six books"), ("back", "At the back")]
    toc = []
    for kind, label in groups:
        items = []
        for p in (p for p in pages if p["kind"] == kind):
            if kind == "book":
                entries = "".join(
                    f'<li><a href="{p["file"]}#{t["id"]}"><span class="toc-n">{t["num"]}</span> '
                    f'<span class="toc-name">{t["name"]}</span>'
                    + (f'<span class="vh"> — </span><span class="toc-gloss">{t["gloss"]}</span>' if t["gloss"] else "")
                    + "</a></li>" for t in p["toc"])
                sub = f'<ol class="toc-entries">{entries}</ol>' if entries else ""
            else:
                entries = " <span class=\"sep\" aria-hidden=\"true\">·</span> ".join(
                    f'<a href="{p["file"]}#{t["id"]}">{t["name"]}</a>' for t in p["toc"])
                sub = f'<p class="toc-sections">{entries}</p>' if entries else ""
            items.append(
                f'<li><a class="toc-row" href="{p["file"]}"><span class="toc-num">{p["num"]}</span>'
                f'<span class="toc-title">{plain(p["name"]) if kind != "book" else p["name"]}</span>'
                f'<span class="toc-time">{minutes(p["words"])} min</span></a>{sub}</li>')
        toc.append(f'<h3 class="toc-group">{label}</h3><ol class="toc toc-{kind}">{"".join(items)}</ol>')

    ld = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": title,
        "alternativeHeadline": subtitle,
        "author": {"@type": "Person", "name": AUTHOR, "url": f"{SITE_URL}/"},
        "datePublished": PUBLISHED,
        "inLanguage": "en",
        "url": url,
        "bookFormat": "https://schema.org/EBook",
        "isAccessibleForFree": True,
        "hasPart": [{"@type": "Chapter", "name": nav_title(p), "url": f"{url}{p['file']}"}
                    for p in pages],
    }
    ld_json = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    front = (f'---\nlayout: null\ntitle: "{title}"\n'
             f'description: "{desc}"\n'
             f"lang: en\ndate_published: {PUBLISHED}\nfeed_category: Book\n---\n")
    first = pages[0]["file"]
    emblem = stitches.inline_svg("emblem", "cover-emblem", mode="x")
    sub_html = f'<p class="cover-sub">{sub_main}</p>'
    if sub_rest:
        sub_html += f'<p class="cover-sub2">{sub_rest}</p>'
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
    {emblem}
    <h1>{title}</h1>
    {sub_html}
    <p class="cover-byline">{AUTHOR} · {PUBLISHED_LABEL}</p>
  </div>
</div>
<main id="contents" class="book-text cover-main">
{EPIGRAPH}
<p class="cover-blurb">{blurb}</p>
<p class="cover-actions"><a class="btn-begin" href="{first}">Begin reading</a></p>
<p class="cover-facts">{len(books)} books · {n_entries} charms and rites · {total_words:,} words · {reading}</p>
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
        title, subtitle, sections = parse_book(fh.read())

    pages = []
    for s in sections:
        meta = page_meta(s["heading"])
        meta["html"] = md_to_html(s["md"])
        pages.append(meta)
    book_files = {p["n"]: p["file"] for p in pages if p["kind"] == "book"}

    total_words, blurb = 0, ""
    for p in pages:
        p["lede"], p["body"], p["toc"] = build_body(p["html"], p)
        p["words"] = word_count(p["html"])
        total_words += p["words"]
    entry_files = {t["id"]: p["file"] for p in pages for t in p["toc"] if t["num"]}
    for p in pages:
        p["body"] = inline_pass(p["body"], p["file"], book_files, entry_files)
        check_quotes(p["body"], p["file"])
        if p["file"] == "introduction.html":
            blurb = re.sub(r'^<p class="lede">|</p>$', "", re.search(r'<p class="lede">.*?</p>', p["body"], re.S).group(0))

    for i, p in enumerate(pages):
        prev_meta = pages[i - 1] if i > 0 else None
        next_meta = pages[i + 1] if i + 1 < len(pages) else None
        html = render_page(p, p["body"], prev_meta, next_meta, description(p["lede"]))
        with open(os.path.join(BOOK_DIR, p["file"]), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html)

    with open(os.path.join(BOOK_DIR, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_cover(title, subtitle, pages, blurb, total_words))

    with open(DATA_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump([{"file": p["file"], "title": nav_title(p), "kind": p["kind"]} for p in pages],
                  fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # stale pages: anything generated earlier that is no longer in the book
    kept = {p["file"] for p in pages} | {"index.html"}
    for name in os.listdir(BOOK_DIR):
        if (re.match(r"^(book-\d+|introduction|anatomy|calendar|bestiary|sources)\.html$", name)
                and name not in kept):
            os.remove(os.path.join(BOOK_DIR, name))

    # link audit: every in-book href must hit a page and, with a #fragment, an id
    ids = {}
    for name in kept:
        with open(os.path.join(BOOK_DIR, name), encoding="utf-8") as fh:
            ids[name] = (fh.read(), set())
        ids[name][1].update(re.findall(r'\bid="([^"]+)"', ids[name][0]))
    broken = []
    for name, (text, own) in ids.items():
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http", "/", "mailto:")):
                continue
            target, _, frag = href.partition("#")
            target = target or name
            if target not in ids:
                broken.append(f"{name}: {href}")
            elif frag and frag not in ids[target][1]:
                broken.append(f"{name}: {href}")
    n_entries = sum(1 for p in pages for t in p["toc"] if t["num"])
    print(f"pages written: {len(pages)} + index.html ({n_entries} entries)")
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
