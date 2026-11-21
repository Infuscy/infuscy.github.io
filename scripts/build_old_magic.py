#!/usr/bin/env python3
"""Build the web edition of THE BOOK OF OLD MAGIC for infuscy.github.io.

Source: old-magic/the-book-of-old-magic.md, the Markdown export of the book
(kept in the repo, excluded from the site by _config.yml). Each `##` section
becomes one reader page in old-magic/:

    introduction.html     "Before you open this book"
    grammar.html          "The grammar of a spell"
    ch01.html … ch10.html
    appendix-a.html …

plus old-magic/index.html (cover and contents, with Jekyll front matter so the
book is in feed.xml and the sitemap) and _data/old_magic_pages.json (the page
list the sitemap reads).

The text is never rewritten, only marked up for reading:
  * Source / Use / Label paragraphs  -> a catalogue card (<dl class="catalogue">)
  * the incantations ("Words")       -> <figure class="tablet">, one line per
    verse line (hanging indent), italic line numbers moved to a gutter, and the
    Akkadian transliteration that follows attached under it
  * Close / Composite / Summary      -> small labels
  * "Today." notes                   -> a callout; a warning one when it says "No."/"Not"
  * [...] and (?)                    -> muted, as the book's own sigla
  * "Chapter IV", "Appendix C"       -> links to those pages
  * tables                           -> data-label cells that stack on phones

The pages share old-magic/book.css (hand-written: this script never touches it)
and /js/reader-font.js (the A-/A+ buttons). CSP is script-src 'self' and
style-src 'self': the pages carry no inline scripts or styles.

Usage:
    py scripts/build_old_magic.py [--src path/to/book.md]

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

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BOOK_DIR = os.path.join(SITE_ROOT, "old-magic")
DEFAULT_SRC = os.path.join(BOOK_DIR, "the-book-of-old-magic.md")
DATA_JSON = os.path.join(SITE_ROOT, "_data", "old_magic_pages.json")

SITE_URL = "https://infuscy.github.io"
BASE = "/old-magic/"
AUTHOR = "Buse Florin-Emilian"
PUBLISHED = "2026-11-21"
PUBLISHED_LABEL = "21 November 2026"
WORDS_PER_MINUTE = 230

# Front-matter sections: heading -> page file stem.
FRONT = {
    "Before you open this book": "introduction",
    "The grammar of a spell": "grammar",
}

# Voluntary AI transparency note (EU AI Act art. 50; see CLAUDE.md, Compliance):
# in every page's footer, and on the cover with the article reference.
TRANSPARENCY = (
    "<strong>Transparency:</strong> this book was compiled and its English renderings "
    "drafted with the help of an AI system (Claude), working from the published "
    "editions listed in <a href=\"appendix-c.html\">Appendix C</a>; the author reviewed "
    "the text against those sources before publication. Editorial responsibility: "
    f"{AUTHOR} (<a href=\"/#contact\">contact</a>)."
)
TRANSPARENCY_COVER = (TRANSPARENCY + " A transparency statement under Article 50 of "
                      "Regulation (EU) 2024/1689 (the AI Act).")

# The share image (img/social-card-old-magic.png) is made by scripts/make_old_magic_card.py.
IMAGE_ALT = ("The Book of Old Magic: the title in cream on lapis-blue glazed brick, under "
             "Ištar's eight-pointed star, between two rosette friezes")

CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "font-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'; connect-src 'self'")

# Ištar's eight-pointed star (24x24), the book's one ornament.
STAR_PATH = ("M12 .5L13.68 7.93L20.13 3.87L16.07 10.32L23.5 12L16.07 13.68L20.13 20.13"
             "L13.68 16.07L12 23.5L10.32 16.07L3.87 20.13L7.93 13.68L.5 12L7.93 10.32"
             "L3.87 3.87L10.32 7.93Z")
STAR_SVG = f'<svg class="star" viewBox="0 0 24 24" aria-hidden="true"><path d="{STAR_PATH}"/></svg>'

ICON_TODAY = ('<svg class="today-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
              'stroke="currentColor" stroke-width="1.6" stroke-linecap="round">'
              '<path d="M6.5 16a5.5 5.5 0 0 1 11 0"/><path d="M3 19.5h18"/>'
              '<path d="M12 5.5V8M5.1 8.6l1.6 1.6M18.9 8.6l-1.6 1.6M2.5 14h1.8M19.7 14h1.8"/></svg>')
ICON_WARN = ('<svg class="today-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
             'stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round">'
             '<path d="M12 3.5L21.5 20h-19z"/><path d="M12 10v4.5"/><path d="M12 17.3v.2"/></svg>')

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}


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


def page_meta(heading):
    m = re.match(r"Chapter ([IVXL]+) · (.+)$", heading)
    if m:
        n = roman_to_int(m.group(1))
        return {"kind": "chapter", "num": m.group(1), "n": n, "name": m.group(2),
                "kicker": f"Chapter {m.group(1)}", "file": f"ch{n:02d}.html"}
    m = re.match(r"Appendix ([A-Z]) · (.+)$", heading)
    if m:
        return {"kind": "appendix", "num": m.group(1), "n": m.group(1), "name": m.group(2),
                "kicker": f"Appendix {m.group(1)}", "file": f"appendix-{m.group(1).lower()}.html"}
    if heading in FRONT:
        return {"kind": "front", "num": "", "n": "", "name": heading, "kicker": "",
                "file": FRONT[heading] + ".html"}
    raise SystemExit(f"ERROR: unknown section heading {heading!r} (add it to FRONT)")


SMARTY_ENTITIES = {"&ldquo;": "“", "&rdquo;": "”", "&lsquo;": "‘",
                   "&rsquo;": "’", "&hellip;": "…", "&ndash;": "–",
                   "&mdash;": "—", "&laquo;": "«", "&raquo;": "»"}


def md_to_html(src):
    # The export marks verse line breaks with a trailing backslash (CommonMark);
    # Python-Markdown wants two trailing spaces.
    src = re.sub(r"(?<!\\)\\$", "  ", src, flags=re.M)
    # The source switches bullet character ("-" then "*") after a blank line inside
    # one list; Python-Markdown would make the whole list loose (<li><p>).
    src = re.sub(r"^([-*] .+)\n\n(?=[-*] )", r"\1\n", src, flags=re.M)
    src = re.sub(r"^\* ", "- ", src, flags=re.M)
    md = markdown.Markdown(extensions=["tables", "sane_lists", "smarty"])
    out = md.convert(src)
    for ent, ch in SMARTY_ENTITIES.items():
        out = out.replace(ent, ch)
    # The source switches bullet character ("-" then "*") inside one list.
    out = re.sub(r"</ul>\s*<ul>\s*", "", out)
    if re.search(r"<li>\s*<p>", out):
        raise SystemExit("ERROR: a loose list (blank lines between items) slipped in; "
                         "the block splitter expects tight lists")
    return out


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
LINE_NO = re.compile(r"^<em>((?:obv\.|rev\.)\s*)?\d+′?(?:–\d+′?)?</em>\s+")
CATALOGUE = {"Source.": "Source", "Use.": "Use", "Label.": "Label"}
KINDS = ("Close", "Composite", "Summary")


def lead(block):
    """(label, rest) when a paragraph opens with a bold label, else (None, None)."""
    m = LEAD_STRONG.match(p_inner(block))
    return (m.group(1), m.group(2)) if m else (None, None)


def is_verse_para(block):
    inner = p_inner(block)
    return "<br />" in inner and not inner.startswith("<strong>")


def mark_kinds(s):
    return re.sub(r"\b(%s)\b" % "|".join(KINDS),
                  lambda m: f'<span class="kind kind-{m.group(1).lower()}">{m.group(1)}</span>', s)


def render_lines(inner, translit=False):
    """One verse paragraph -> (html, numbered?)."""
    numbered = False
    spans = []
    raw = [ln.strip() for ln in re.split(r"<br />\s*", inner.strip())]
    for line in raw:
        cls, num, extra = "l", "", ""
        m = LINE_NO.match(line)
        if m:
            num = f'<span class="ln">{strip_tags(m.group(0)).strip()}</span>'
            line = line[m.end():]
            numbered = True
        text = plain(line).strip()
        # A whole line in brackets is an editor's or healer's note, not the spell.
        if re.fullmatch(r"\((?:[^()]|\([^()]*\))*\)\.?", text) and not line.startswith("<em>"):
            cls += " ed"
        elif translit:
            line = re.sub(r"</?em>", "", line)
            extra = ' lang="akk"'
        spans.append(f'<span class="{cls}"{extra}>{num}{line}</span>')
    longest = max(len(plain(x)) for x in raw)
    cls = "stanza long" if longest > 150 else "stanza"
    return f'<p class="{cls}">{"".join(spans)}</p>', numbered


def render_translit(label, rest):
    body, _ = render_lines(rest, translit=True)
    # "Akkadian (I 1–3)." -> small-caps "Akkadian" + the reference in normal case
    m = re.match(r"^(Akkadian)\s*\((.*)\)\.?$", label)
    cap = (f'<span class="cap-label">{m.group(1)}</span> <span class="cap-ref">({m.group(2)})</span>'
           if m else label.rstrip("."))
    return f'<div class="translit"><p class="translit-cap">{cap}</p>{body}</div>'


def caption_html(label, rest):
    rest = rest.strip()
    if rest:
        return (f'<span class="cap-label">{label.rstrip(".")}</span> '
                f'<span class="cap-ref">{rest.rstrip(".")}</span>')
    return f'<span class="cap-label">{label.rstrip(".")}</span>'


def build_tablet(blocks, start, caption, first_free):
    """Collect the verse paragraphs from blocks[start:]; returns (next index, html)."""
    stanzas, numbered, j, n = [], False, start, len(blocks)
    while j < n and blocks[j][0] == "p":
        inner = p_inner(blocks[j][1])
        if inner.startswith("<strong>") or inner.startswith("<em>Rite.</em>"):
            break
        if not ("<br />" in inner or LINE_NO.match(inner) or (first_free and j == start)):
            break
        body, num = render_lines(inner)
        stanzas.append(body)
        numbered = numbered or num
        j += 1
    if not stanzas:
        return start, None
    translit = ""
    if j < n and blocks[j][0] == "p":
        label, rest = lead(blocks[j][1])
        if label and label.startswith("Akkadian"):
            translit = render_translit(label, rest)
            j += 1
    cls = "tablet numbered" if numbered else "tablet"
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return j, (f'<figure class="{cls}">{cap}<blockquote class="verse">{"".join(stanzas)}'
               f'</blockquote>{translit}</figure>')


def build_catalogue(blocks, i):
    rows, j, n = [], i, len(blocks)
    while j < n and blocks[j][0] == "p":
        label, rest = lead(blocks[j][1])
        if label not in CATALOGUE:
            break
        name, value = CATALOGUE[label], rest.strip()
        j += 1
        # "Two tablets from Assur, edited by …:" + the list that follows
        if value.endswith(":") and j < n and blocks[j][0] in ("ul", "ol"):
            value = f"<p>{value}</p>{render_list(blocks[j][1])}"
            j += 1
        if name == "Label":
            value = mark_kinds(value)
            # "Close." alone: the label needs no full stop
            value = re.sub(r'^(<span class="kind[^"]*">\w+</span>)\.$', r"\1", value)
        rows.append(f"<div><dt>{name}</dt><dd>{value}</dd></div>")
    return j, f'<dl class="catalogue">{"".join(rows)}</dl>'


def render_list(block):
    # The legend of the three labels ("Close:", "Composite:", "Summary:").
    block = re.sub(r"<li><strong>(%s):</strong>\s*" % "|".join(KINDS),
                   lambda m: f'<li><span class="kind kind-{m.group(1).lower()}">{m.group(1)}</span> ',
                   block)
    return block.replace("<li><strong>", '<li><strong class="rubric">')


def render_table(block):
    heads = [plain(h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", block, re.S)]

    def row(m):
        k = -1

        def cell(_m):
            nonlocal k
            k += 1
            label = heads[k] if k < len(heads) else ""
            return f'<td role="cell" data-label="{attr(label)}">'

        return '<tr role="row">' + re.sub(r"<td[^>]*>", cell, m.group(1)) + "</tr>"

    block = re.sub(r"<tr>(.*?)</tr>", row, block, flags=re.S)
    block = (block.replace("<table>", '<table role="table">')
             .replace("<thead>", '<thead role="rowgroup">')
             .replace("<tbody>", '<tbody role="rowgroup">')
             .replace("<th>", '<th role="columnheader">'))
    return f'<div class="table-wrap">{block}</div>'


def render_today(rest):
    text = plain(rest).strip()
    warn = text.startswith(("No.", "Not "))
    icon = ICON_WARN if warn else ICON_TODAY
    cls = "today warn" if warn else "today"
    return (f'<div class="{cls}" role="note">{icon}<p><strong class="rubric">Today.</strong>'
            f'{rest}</p></div>')


def transform(blocks):
    """Mark up one run of blocks (a section's body)."""
    out, i, n = [], 0, len(blocks)
    while i < n:
        tag, b = blocks[i]
        if tag in ("ul", "ol"):
            out.append(render_list(b))
            i += 1
            continue
        if tag == "table":
            out.append(render_table(b))
            i += 1
            continue
        if tag != "p":
            out.append(b)
            i += 1
            continue
        label, rest = lead(b)
        if label in CATALOGUE:
            i, html = build_catalogue(blocks, i)
            out.append(html)
            continue
        if label and label.startswith("Akkadian"):
            out.append(render_translit(label, rest))
            i += 1
            continue
        if label == "Today.":
            out.append(render_today(rest))
            i += 1
            continue
        nxt = blocks[i + 1] if i + 1 < n else None
        # A bold label that introduces verse becomes the tablet's caption:
        # "Words: her portrait." or "No. 14 (KAR 236:1–17; …)."
        if label and nxt and nxt[0] == "p":
            words_label = label.startswith("Words") and not rest.strip()
            short_intro = len(plain(label + rest)) < 140 and is_verse_para(nxt[1])
            if words_label or short_intro:
                j, html = build_tablet(blocks, i + 1, caption_html(label, rest), words_label)
                if html:
                    out.append(html)
                    i = j
                    continue
        if not label and is_verse_para(b):
            j, html = build_tablet(blocks, i, None, False)
            if html:
                out.append(html)
                i = j
                continue
        inner = p_inner(b)
        if label is not None:
            if not rest.strip():
                # a label on its own line ("Ritual.", "Sigla.") is set as a small heading
                out.append(f'<p class="rubric-head"><strong class="rubric">{label.rstrip(".")}'
                           "</strong></p>")
            else:
                out.append(f'<p><strong class="rubric">{label}</strong>{rest}</p>')
        elif inner.startswith("<em>Rite.</em>"):
            out.append('<p><em class="rubric rubric-sub">Rite.</em>'
                       + inner[len("<em>Rite.</em>"):] + "</p>")
        else:
            out.append(b)
        i += 1
    return "\n".join(out)


def build_body(html, meta):
    """Section HTML -> (lede text, body html, [(title, slug)] of its subsections)."""
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
    # epigraph: *"quoted words"* — attribution (opens the introduction)
    if intro and intro[0][0] == "p":
        m = re.match(r"^<em>(“.*?”)</em>\s*—\s*(.*)$", p_inner(intro[0][1]), re.S)
        if m:
            parts.append(f'<figure class="epigraph"><blockquote><p>{m.group(1)}</p></blockquote>'
                         f"<figcaption>{m.group(2)}</figcaption></figure>")
            intro = intro[1:]
    if intro and intro[0][0] == "p" and not lead(intro[0][1])[0]:
        lede_text = plain(p_inner(intro[0][1]))
        parts.append(intro[0][1].replace("<p>", '<p class="lede">', 1))
        intro = intro[1:]
    if intro:
        parts.append(transform(intro))

    toc, seen = [], set()
    for s in sections:
        slug = slugify(s["title"])
        while slug in seen:
            slug += "-2"
        seen.add(slug)
        toc.append((s["title"], slug))
    if len(toc) > 1:
        items = "".join(f'<li><a href="#{slug}">{title}</a></li>' for title, slug in toc)
        label = "In this chapter" if meta["kind"] == "chapter" else "On this page"
        parts.append(f'<nav class="in-chapter" aria-label="{label}">'
                     f'<p class="in-chapter-cap">{label}</p><ol>{items}</ol></nav>')
    for s, (title, slug) in zip(sections, toc):
        parts.append(f'<section class="entry" aria-labelledby="{slug}">'
                     f'<h2 id="{slug}">{title}</h2>\n{transform(s["blocks"])}\n</section>')
    return lede_text, "\n".join(parts), toc


# ----------------------------------------------------------------- inline pass

def inline_pass(html, current, ch_files, ap_files):
    """Cross-references become links; the book's sigla […] and (?) get a class.
    Text inside tags, links and headings is left alone."""
    def chap(m):
        target = ch_files.get(roman_to_int(m.group(2)))
        if not target or target == current:
            return m.group(0)
        return f'<a class="xref" href="{target}">{m.group(0)}</a>'

    def appx(m):
        target = ap_files.get(m.group(1))
        if not target or target == current:
            return m.group(0)
        return f'<a class="xref" href="{target}">{m.group(0)}</a>'

    out, skip = [], 0
    for tok in re.split(r"(<[^>]+>)", html):
        if tok.startswith("<"):
            m = re.match(r"<(/?)(a|h1|h2|figcaption)\b", tok)
            if m:
                skip += -1 if m.group(1) else 1
            out.append(tok)
            continue
        if not skip:
            tok = re.sub(r"\b(Chapters?) ([IVX]+)\b(?:–([IVX]+)\b)?", chap, tok)
            tok = re.sub(r"\bAppendix ([A-Z])\b", appx, tok)
        tok = tok.replace("[…]", '<span class="gap">[…]</span>')
        tok = tok.replace("(?)", '<span class="unc">(?)</span>')
        out.append(tok)
    return "".join(out)


def check_quotes(html, where):
    """Smart quotes facing the wrong way are the usual conversion slip."""
    text = plain(html)
    bad = re.findall(r".{0,20}(?:\s”|“\s|\s’(?![0-9])).{0,20}", text)
    for b in bad:
        print(f"  quote check {where}: …{b}…")


def check_font_coverage(paths):
    """Every character a reader sees must be in old-magic/fonts (a subset of Gentium
    Book Plus, see scripts/subset_old_magic_fonts.py); a missing one would be drawn
    in a fallback font. Warns, does not fail: re-run the subsetter with a wider range."""
    font_dir = os.path.join(BOOK_DIR, "fonts")
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("font coverage: skipped (fontTools not installed)")
        return
    fonts = sorted(f for f in os.listdir(font_dir) if f.endswith(".woff")) if os.path.isdir(font_dir) else []
    if not fonts:
        print("font coverage: skipped (no fonts in old-magic/fonts)")
        return
    seen = {}
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            page = fh.read()
        body = page[page.find("<body"):]
        # visible text, plus the column labels the stacked tables show via CSS
        text = plain(body) + "".join(htmlmod.unescape(v) for v in re.findall(r'data-label="([^"]*)"', body))
        for ch in text:
            if not ch.isspace() or ch == " ":
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
<meta name="theme-color" content="#f6f0e4" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#11141c" media="(prefers-color-scheme: dark)">
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
<meta property="og:image" content="{site}/img/social-card-old-magic.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{image_alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{site}/img/social-card-old-magic.png">
<link rel="preload" href="/old-magic/fonts/old-magic-text-regular.woff" as="font" type="font/woff" crossorigin>
<link rel="preload" href="/old-magic/fonts/old-magic-text-italic.woff" as="font" type="font/woff" crossorigin>
<link rel="stylesheet" href="/old-magic/book.css">"""

TOPBAR = """<a class="skip-link" href="#{target}">Skip to the text</a>
<header class="topbar">
  <a class="topbar-book" href="/old-magic/">{star}<span>The Book of Old Magic</span></a>
  {controls}
</header>"""

FONT_CONTROLS = ('<span class="font-controls"><button class="font-btn" id="fontDown" type="button" '
                 'title="Smaller text" aria-label="Decrease font size">A−</button>'
                 '<button class="font-btn" id="fontUp" type="button" title="Larger text" '
                 'aria-label="Increase font size">A+</button></span>')

FOOTER = """<footer class="book-foot">
  <p class="foot-note">{transparency}</p>
  <p class="foot-links"><a href="/old-magic/">Contents</a> · <a href="/">Febuse</a> · <a href="/privacy/">Privacy</a></p>
</footer>"""


def nav_title(meta):
    if meta["kind"] == "front":
        return meta["name"]
    return f'{meta["kicker"]} · {meta["name"]}'


def render_page(meta, body, prev_meta, next_meta, desc):
    title = f"{nav_title(meta)} — The Book of Old Magic"
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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{head}{rel}
</head>
<body class="page-{meta['kind']}">
{TOPBAR.format(target="text", star=STAR_SVG, controls=FONT_CONTROLS)}
<main id="text" class="book-text">
<header class="chapter-head">
{kicker}<h1>{meta['name']}</h1>
<div class="ornament" aria-hidden="true"></div>
</header>
{body}
</main>
<nav class="pager" aria-label="Chapters">
  {pager_link(prev_meta, "pager-prev", "prev")}
  <a class="pager-toc" href="/old-magic/">Contents</a>
  {pager_link(next_meta, "pager-next", "next")}
</nav>
{FOOTER.format(transparency=TRANSPARENCY)}
<script src="/js/reader-font.js"></script>
</body>
</html>
"""


def render_cover(title, subtitle, pages, epigraph_html, blurb, total_words):
    desc = ("Incantations, rituals and curses from Sumer, Babylon and Assyria, c. 2600–100 BCE: "
            "real ancient texts in a fresh English rendering, with their sources, rituals and notes. "
            "Free to read online.")
    url = f"{SITE_URL}{BASE}"
    head = HEAD.format(csp=CSP, title=attr(title), desc=attr(desc), author=AUTHOR, url=url,
                       site=SITE_URL, og_type="book", og_title=attr(title),
                       image_alt=attr(IMAGE_ALT))
    n_ch = sum(1 for p in pages if p["kind"] == "chapter")
    n_ap = sum(1 for p in pages if p["kind"] == "appendix")
    total_min = minutes(total_words)
    reading = f"about {total_min // 60} h {total_min % 60:02d} min" if total_min >= 60 else f"{total_min} min"

    groups = [("front", "Before the spells"), ("chapter", "Chapters"), ("appendix", "Appendices")]
    toc = []
    for kind, label in groups:
        items = []
        for p in (p for p in pages if p["kind"] == kind):
            # the no-break space keeps each "·" at a line's end, never at the start
            entries = " <span class=\"sep\" aria-hidden=\"true\">·</span> ".join(
                f'<a href="{p["file"]}#{slug}">{t}</a>' for t, slug in p["toc"])
            num = p["num"] if kind != "front" else ""
            items.append(
                f'<li><a class="toc-row" href="{p["file"]}"><span class="toc-num">{num}</span>'
                f'<span class="toc-title">{p["name"]}</span>'
                f'<span class="toc-time">{minutes(p["words"])} min</span></a>'
                + (f'<p class="toc-entries">{entries}</p>' if entries else "") + "</li>")
        toc.append(f'<h3 class="toc-group">{label}</h3><ol class="toc">{"".join(items)}</ol>')

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
    <svg class="cover-emblem" viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="46"/><circle cx="50" cy="50" r="41"/><path d="M50 12L54.97 37.99L76.87 23.13L62.01 45.03L88 50L62.01 54.97L76.87 76.87L54.97 62.01L50 88L45.03 62.01L23.13 76.87L37.99 54.97L12 50L37.99 45.03L23.13 23.13L45.03 37.99Z"/></svg>
    <h1>{title}</h1>
    <p class="cover-sub">{subtitle}</p>
    <p class="cover-byline">{AUTHOR} · {PUBLISHED_LABEL}</p>
  </div>
</div>
<main id="contents" class="book-text cover-main">
{epigraph_html}
<p class="cover-blurb">{blurb}</p>
<p class="cover-actions"><a class="btn-begin" href="{first}">Begin reading</a></p>
<p class="cover-facts">{n_ch} chapters · {n_ap} appendices · {total_words:,} words · {reading}</p>
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
    ch_files = {p["n"]: p["file"] for p in pages if p["kind"] == "chapter"}
    ap_files = {p["n"]: p["file"] for p in pages if p["kind"] == "appendix"}

    total_words, epigraph_html, blurb = 0, "", ""
    for p in pages:
        lede, body, toc = build_body(p["html"], p)
        p["body"] = inline_pass(body, p["file"], ch_files, ap_files)
        p["lede"], p["toc"] = lede, toc
        p["words"] = word_count(p["html"])
        total_words += p["words"]
        check_quotes(p["body"], p["file"])
        if p["file"] == "introduction.html":
            m = re.search(r'<figure class="epigraph">.*?</figure>', p["body"], re.S)
            epigraph_html = m.group(0) if m else ""
            blurb = lede

    for i, p in enumerate(pages):
        prev_meta = pages[i - 1] if i > 0 else None
        next_meta = pages[i + 1] if i + 1 < len(pages) else None
        html = render_page(p, p["body"], prev_meta, next_meta, description(p["lede"]))
        with open(os.path.join(BOOK_DIR, p["file"]), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html)

    with open(os.path.join(BOOK_DIR, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_cover(title, subtitle, pages, epigraph_html, blurb, total_words))

    with open(DATA_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump([{"file": p["file"], "title": nav_title(p), "kind": p["kind"]} for p in pages],
                  fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # stale pages: anything generated earlier that is no longer in the book
    kept = {p["file"] for p in pages} | {"index.html"}
    for name in os.listdir(BOOK_DIR):
        if re.match(r"^(ch\d{2}|appendix-[a-z]|introduction|grammar)\.html$", name) and name not in kept:
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
    print(f"pages written: {len(pages)} + index.html")
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
