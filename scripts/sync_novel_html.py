"""Re-render the novel chapters from translated/*.md into the shipped translated/*.html.

Only the generated parts of each page are replaced -- <title>, the <h1> + body inside
<main class="reader-content">, and the "Translator Notes" block -- so everything patched in
after the original build (CSP metas, font controls, disclaimers, nav) is kept as is.
_data/novel_chapters.json (chapter titles for the ToC) is rewritten too.

Use this instead of scripts/build-novel.js after editing a chapter's markdown: that script
regenerates whole pages from an older template and would drop those later patches.

The markdown -> HTML rules mirror build-novel.js (paragraphs split on blank lines, `## ` headings,
`---` rules, **bold**, *italic*, everything from "## Flags" on goes into Translator Notes).
Sources are read as LF: chapters once built from CRLF files had the whole text collapsed
into a single <p>.

Usage: py scripts/sync_novel_html.py            rewrite pages that differ from their markdown
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

RX_TITLE = re.compile(r"<title>.*?</title>", re.S)
RX_MAIN = re.compile(r'(<main class="reader-content">\n).*?(\n</main>)', re.S)
RX_NOTES = re.compile(r'(</main>)\n.*?\n(<nav class="reader-bottom-nav">)', re.S)


def escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text):
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)


def trim(text):
    return text.strip(JS_WHITESPACE)


def md_to_html(text):
    out = []
    for block in re.split(r"\n\n+", text or ""):
        block = trim(block)
        if not block:
            continue
        if block in ("---", "***", "* * *"):
            out.append("<hr>")
        elif block.startswith("## "):
            out.append("<h2>" + inline(block[3:]) + "</h2>")
        else:
            out.append("<p>" + inline(block) + "</p>")
    return "\n".join(out)


def parse_chapter(content):
    notes_at = re.search(r"\n## Flags", content)
    if notes_at:
        body, notes = trim(content[: notes_at.start()]), trim(content[notes_at.start() + 1 :])
    else:
        body, notes = trim(content), None
    found = re.search(r"^## (Chapter \d+: .+)$", body, re.M)
    heading = found.group(1) if found else "Chapter"
    title = re.sub(r"^Chapter \d+: ", "", heading)
    body = trim(re.sub(r"\A## Chapter \d+: .+\n*", "", body))
    body = trim(re.sub(r"\n*---\s*\Z", "", body))
    return heading, title, md_to_html(body), md_to_html(notes) if notes else None


def render(page, heading, body_html, notes_html):
    page = RX_TITLE.sub(lambda m: f"<title>{escape(heading)} — {escape(NOVEL_TITLE)}</title>", page, 1)
    page = RX_MAIN.sub(lambda m: m.group(1) + f"<h1>{escape(heading)}</h1>\n{body_html}" + m.group(2), page, 1)
    notes = (
        f'\n<details class="flags-section">\n<summary>Translator Notes</summary>\n{notes_html}\n</details>'
        if notes_html
        else ""
    )
    return RX_NOTES.sub(lambda m: m.group(1) + "\n" + notes + "\n" + m.group(2), page, 1)


def read_lf(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read().replace(CR + LF, LF).replace(CR, LF)


def main(check_only):
    sources = glob.glob(os.path.join(ROOT, "translated", "chapter*.md"))
    sources.sort(key=lambda p: int(re.search(r"(\d+)\.md$", p).group(1)))
    chapters, stale = [], []
    for md_path in sources:
        num = int(re.search(r"(\d+)\.md$", md_path).group(1))
        html_path = md_path[:-3] + ".html"
        with open(html_path, encoding="utf-8", newline="") as fh:
            current = fh.read()
        heading, title, body_html, notes_html = parse_chapter(read_lf(md_path))
        fresh = render(current.replace(CR, ""), heading, body_html, notes_html)
        chapters.append({"num": num, "title": title, "file": os.path.basename(html_path)})
        if fresh != current:
            stale.append(os.path.basename(html_path))
            if not check_only:
                with open(html_path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(fresh)

    index_path = os.path.join(ROOT, "_data", "novel_chapters.json")
    fresh_index = json.dumps(chapters, indent=2, ensure_ascii=False)
    with open(index_path, encoding="utf-8", newline="") as fh:
        index_stale = fh.read() != fresh_index
    if index_stale and not check_only:
        with open(index_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(fresh_index)

    verb = "out of sync" if check_only else "updated"
    print(f"chapters: {len(sources)}  pages {verb}: {len(stale)}  chapter index {verb}: {'yes' if index_stale else 'no'}")
    for name in stale[:10]:
        print("  ", name)
    return 1 if check_only and (stale or index_stale) else 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv[1:]))
