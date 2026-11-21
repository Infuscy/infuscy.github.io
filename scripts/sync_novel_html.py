"""Render the novel's chapter pages: translated/*.md -> translated/*.html.

Every page is written whole from PAGE below: the head (CSP metas, colour scheme,
prev/next links), the top bar (contents link, position, font buttons), the fan-work
disclaimer, the chapter (title, text, Translator Notes), a previous/next pager that
names the neighbouring chapters, and the footnote. The look is css/reader.css, the
reader theme shared with the contents page novel/index.html. _data/novel_chapters.json
(the titles behind the contents page) is rewritten too. Never hand-edit the pages, and
don't use scripts/build-novel.js: it is an older template without any of this.

Text rules follow the original build-novel.js: paragraphs split on blank lines, `## `
headings, `---` scene breaks, **bold**, *italic*, and everything from "## Flags" on
goes into Translator Notes. Added since: `>` blocks become a blockquote (a letter, a
song), and the page gets book typography -- curly quotes and apostrophes, " -- " as an
em dash, "..." as an ellipsis. The .md sources are never changed.
The first paragraph is marked as the chapter's opening (small capitals); a long one
that starts with a letter also gets the drop cap, which a short or quoted first line
would leave hanging. Sources are read as LF: chapters once built from CRLF files had
the whole text collapsed into a single <p>. Pages are compared as LF too: with
core.autocrlf Git checks them out with CRLF, which is no change to their content.

Usage: py scripts/sync_novel_html.py            rewrite the pages that differ
       py scripts/sync_novel_html.py --check    report only (exit 1 if anything is out of sync)
"""
import glob
import json
import os
import re
import sys

NOVEL_TITLE = "The Wobbly Peach"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CR, LF = chr(13), chr(10)
JS_WHITESPACE = " \t\n\r\f\v ﻿  "
DROP_CAP_MIN = 180  # characters: about three lines at the widest measure

DISCLAIMER = (
    '<div class="reader-disclaimer"><strong>Non-commercial fan translation (hobby).</strong> '
    "The original novel and its characters belong to their author; Warcraft is a trademark of "
    "Blizzard Entertainment — not affiliated with or endorsed by the original author, the "
    "publishers or Blizzard. No ads, donations or tracking; removed on request of the rights "
    'holders. <span lang="ro">Traducere neoficială de fandom, publicată gratuit, fără scop '
    "comercial; se retrage la cererea deținătorilor de drepturi.</span></div>"
)
FOOTNOTE = (
    '<p class="reader-footnote">Unofficial non-commercial fan work (hobby). The original novel '
    "and its characters belong to their author; Warcraft is a trademark of Blizzard "
    "Entertainment — this project is not affiliated with or endorsed by the original author, "
    "the publishers or Blizzard. No ads, no donations, no tracking. This translation will be "
    "removed at the request of the rights holders.</p>"
)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'; connect-src 'self'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f4eee2" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#16121e" media="(prefers-color-scheme: dark)">
<title>{page_title}</title>
<link rel="icon" href="/img/profile.png">
<link rel="stylesheet" href="/css/reader.css">
{rel_links}</head>
<body>
<a class="skip-link" href="#text">Skip to the text</a>
<header class="reader-top-bar">
  <a class="reader-book" href="/novel/">Contents</a>
  <span class="reader-progress">Chapter {num} of {total}</span>
  <span class="reader-font-controls"><button class="font-btn" id="fontDown" type="button" title="Smaller text" aria-label="Decrease font size">A−</button><button class="font-btn" id="fontUp" type="button" title="Larger text" aria-label="Increase font size">A+</button></span>
</header>
{disclaimer}
<main id="text" class="reader-content">
<h1><span class="chapter-kicker">Chapter {num}<span class="visually-hidden">:</span></span> {title}</h1>
{body}
</main>
{notes}<nav class="reader-pager" aria-label="Chapters">
{prev}
  <a class="pager-toc" href="/novel/">Contents</a>
{next}
</nav>
{footnote}
<script src="/js/reader-font.js"></script>
</body>
</html>
"""

# ---------- typography ----------
OPENS_AFTER = set(" \t\n([{—–-/\"'“‘")
CLOSES_BEFORE = set(",.;:!?)]}…—–-")
ELISIONS = {"em", "tis", "twas", "cause", "til", "bout", "round", "ere"}


def smarten(text):
    """Curly quotes and apostrophes, em dashes and ellipses, as a typesetter would set them."""
    text = text.replace(" -- ", " — ").replace("...", "…")
    out = []
    for i, c in enumerate(text):
        if c != '"' and c != "'":
            out.append(c)
            continue
        j = i - 1  # look past *emphasis* markers on both sides
        while j >= 0 and text[j] == "*":
            j -= 1
        k = i + 1
        while k < len(text) and text[k] == "*":
            k += 1
        prev = text[j] if j >= 0 else " "
        nxt = text[k] if k < len(text) else " "
        if c == '"':
            if nxt.isspace() or nxt in CLOSES_BEFORE:
                out.append("”")
            elif prev.isspace() or prev in OPENS_AFTER:
                out.append("“")
            else:
                out.append("”")
        elif prev.isalnum() and nxt.isalnum():  # don't, Quel'Thalas
            out.append("’")
        elif prev.isspace() or prev in OPENS_AFTER:
            word = re.match(r"[A-Za-z]+", text[k:])
            elided = nxt.isdigit() or (word is not None and word.group(0).lower() in ELISIONS)
            out.append("’" if elided else "‘")  # 'em, '90s keep an apostrophe
        else:
            out.append("’")
    return "".join(out)


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text):
    text = escape(smarten(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)


def trim(text):
    return text.strip(JS_WHITESPACE)


# ---------- markdown ----------
def render_quote(block):
    """A `>` block: a letter or a song. Blank `>` lines split paragraphs; other line breaks stay."""
    lines = [re.sub(r"^> ?", "", line) for line in block.split("\n")]
    paras = [p for p in (trim(p) for p in re.split(r"\n[ \t]*\n", "\n".join(lines))) if p]
    inner = "\n".join("<p>" + "<br>\n".join(inline(trim(line)) for line in p.split("\n")) + "</p>" for p in paras)
    return "<blockquote>\n" + inner + "\n</blockquote>"


def md_to_html(text, opening=False):
    out = []
    for block in re.split(r"\n\n+", text or ""):
        block = trim(block)
        if not block:
            continue
        if block in ("---", "***", "* * *"):
            out.append("<hr>")
        elif block.startswith("## "):
            out.append("<h2>" + inline(block[3:]) + "</h2>")
        elif all(line.startswith(">") for line in block.split("\n")):
            out.append(render_quote(block))
        elif opening and not out:
            drop = len(block) >= DROP_CAP_MIN and block.lstrip("*")[:1].isalpha()
            out.append(f'<p class="opening{" drop" if drop else ""}">' + inline(block) + "</p>")
        else:
            out.append("<p>" + inline(block) + "</p>")
    return "\n".join(out)


def parse_chapter(content, path):
    notes_at = re.search(r"\n## Flags", content)
    if notes_at:
        body, notes = trim(content[: notes_at.start()]), trim(content[notes_at.start() + 1 :])
    else:
        body, notes = trim(content), None
    found = re.search(r"^## Chapter (\d+): (.+)$", body, re.M)
    if not found:
        sys.exit(f"{path}: no '## Chapter N: Title' heading")
    body = trim(re.sub(r"\A## Chapter \d+: .+\n*", "", body))
    body = trim(re.sub(r"\n*---\s*\Z", "", body))
    return int(found.group(1)), smarten(trim(found.group(2))), body, notes


# ---------- page ----------
def pager_link(ch, cls, rel, label):
    if ch is None:
        return f'  <span class="{cls} pager-empty" aria-hidden="true"></span>'
    return (
        f'  <a class="{cls}" href="{ch["file"]}" rel="{rel}"><span class="pager-dir">{label} · '
        f'Chapter {ch["num"]}</span><span class="pager-title">{escape(ch["title"])}</span></a>'
    )


def render_page(ch, prev, nxt, total):
    rel = "".join(
        f'<link rel="{rel}" href="{other["file"]}">\n'
        for rel, other in (("prev", prev), ("next", nxt))
        if other is not None
    )
    notes = (
        '<details class="flags-section">\n<summary>Translator Notes</summary>\n'
        + md_to_html(ch["notes"])
        + "\n</details>\n"
        if ch["notes"]
        else ""
    )
    return PAGE.format(
        page_title=escape(f"Chapter {ch['num']}: {ch['title']} — {NOVEL_TITLE}"),
        rel_links=rel,
        num=ch["num"],
        total=f"{total:,}",
        disclaimer=DISCLAIMER,
        title=escape(ch["title"]),
        body=md_to_html(ch["body"], opening=True),
        notes=notes,
        prev=pager_link(prev, "pager-prev", "prev", "Previous"),
        next=pager_link(nxt, "pager-next", "next", "Next"),
        footnote=FOOTNOTE,
    )


def read_lf(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read().replace(CR + LF, LF).replace(CR, LF)


def main(check_only):
    sources = glob.glob(os.path.join(ROOT, "translated", "chapter*.md"))
    sources.sort(key=lambda p: int(re.search(r"(\d+)\.md$", p).group(1)))
    chapters = []
    for md_path in sources:
        num, title, body, notes = parse_chapter(read_lf(md_path), md_path)
        if num != int(re.search(r"(\d+)\.md$", md_path).group(1)):
            sys.exit(f"{md_path}: heading says chapter {num}")
        html_path = md_path[:-3] + ".html"
        chapters.append({"num": num, "title": title, "file": os.path.basename(html_path),
                         "path": html_path, "body": body, "notes": notes})

    stale = []
    for i, ch in enumerate(chapters):
        prev = chapters[i - 1] if i > 0 else None
        nxt = chapters[i + 1] if i + 1 < len(chapters) else None
        fresh = render_page(ch, prev, nxt, len(chapters))
        if "<style" in fresh or ' style="' in fresh or "<script>" in fresh:
            sys.exit(f"{ch['path']}: inline style or script (the CSP blocks it)")
        try:
            current = read_lf(ch["path"])
        except FileNotFoundError:
            current = None
        if fresh != current:
            stale.append(ch["file"])
            if not check_only:
                with open(ch["path"], "w", encoding="utf-8", newline="") as fh:
                    fh.write(fresh)

    index = [{"num": ch["num"], "title": ch["title"], "file": ch["file"]} for ch in chapters]
    index_path = os.path.join(ROOT, "_data", "novel_chapters.json")
    fresh_index = json.dumps(index, indent=2, ensure_ascii=False)
    index_stale = read_lf(index_path) != fresh_index
    if index_stale and not check_only:
        with open(index_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(fresh_index)

    verb = "out of sync" if check_only else "updated"
    print(f"chapters: {len(chapters)}  pages {verb}: {len(stale)}  chapter index {verb}: {'yes' if index_stale else 'no'}")
    for name in stale[:10]:
        print("  ", name)
    return 1 if check_only and (stale or index_stale) else 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv[1:]))
