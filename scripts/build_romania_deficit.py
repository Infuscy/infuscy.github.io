#!/usr/bin/env python3
"""Build the web edition of "Poate România să plătească deficitul?" for infuscy.github.io.

Reads the main report from C:\\GIT\\RomaniaDeficit
(Raport_Romania_Deficit_Sustenabilitate.md) and writes one article page,
romania-deficit/index.html, plus the figures, the PDF and the Excel model next
to it.

The Markdown is parsed with the report repo's own tools/md_comun.py, the same
parser behind its DOCX and PDF, so the three editions stay content-identical.
What changes for online readers:

- an article header: kicker, title, the one-sentence answer as lede, reading
  time, downloads, the AI-transparency note (EU AI Act art. 50) and a
  "Pe scurt" box built from the lead sentence of each key conclusion in §1;
- a table of contents, heading anchors and a floating "Cuprins" link;
- citations [Sn] point to the page's own source list (with a hover title),
  and "§6.7"-style cross-references link to the section;
- wide tables scroll horizontally, figures are numbered and lazy-loaded;
- the shared civic theme, /css/civic.css (linked from the front matter), with the
  reading markup it styles: section numbers in a span, table columns of figures
  marked `num` (right-aligned), and each scenario named in the text (S1…S7, never the
  citation [S1]) marked with its line colour from the charts, read from the model's
  CULORI_SCENARII;
- links to files that exist only in the (private) report repo — code, CSVs,
  sub-reports, archived documents — become plain text, and the
  "Materiale documentare arhivate local" subsection is dropped.

Usage:
    python scripts/build_romania_deficit.py [--src C:\\GIT\\RomaniaDeficit]

Needs Pillow (the figures are published as lossless WebP). The script rewrites only
romania-deficit/index.html, romania-deficit/figuri/*.webp and the two download files.
"""
import argparse
import ast
import html
import os
import re
import shutil

from PIL import Image
import struct
import sys
import unicodedata

SITE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_SRC = os.path.abspath(os.path.join(SITE_ROOT, "..", "RomaniaDeficit"))

SLUG = "romania-deficit"
URL = f"/{SLUG}/"
OUT_DIR = os.path.join(SITE_ROOT, SLUG)
REPORT_MD = "Raport_Romania_Deficit_Sustenabilitate.md"
REPORT_PDF = "Raport_Romania_Deficit_Sustenabilitate.pdf"
MODEL_XLSX = "model/Model_DSA_Romania.xlsx"
CUT_HEADING = "### Materiale documentare arhivate local"

AUTHOR = "Buse Florin-Emilian"
EMAIL = "buse.florinx@gmail.com"
WORDS_PER_MINUTE = 200

# The page's look is the shared civic theme, /css/civic.css (hand-written; the front matter
# links it). The page itself adds only the scenario colours, read from the model's own
# charts so a scenario's mark in the text matches its line in the figures.
CIVIC_CSS = "/css/civic.css"
SCENARIO_COLORS_FILE = "model/model_dsa.py"   # defines CULORI_SCENARII


# ------------------------------------------------------------------ helpers

def load_parser(src):
    tools = os.path.join(src, "tools")
    if not os.path.isfile(os.path.join(tools, "md_comun.py")):
        sys.exit(f"ERROR: {tools}/md_comun.py not found (use --src)")
    sys.path.insert(0, tools)
    import md_comun
    return md_comun


def slugify(text, limit=48):
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:limit].rstrip("-") or "sectiune"


def plain(md):
    """Markdown inline -> plain text (for titles, TOC entries and tooltips)."""
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md)
    t = re.sub(r"<(https?://[^>\s]+)>", r"\1", t)
    return t.replace("**", "").replace("`", "").replace("*", "").strip()


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def fmt_size(path):
    n = os.path.getsize(path)
    return f"{n / 1048576:.1f} MB".replace(".", ",") if n >= 1048576 else f"{round(n / 1024)} KB"


def yaml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def first_sentences(text, n):
    parts = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(parts[:n])


def scenario_colors(src):
    """S1…S7 -> the colour of each scenario's line in the charts, read from the model's
    CULORI_SCENARII (parsed, not imported: the model needs numpy and matplotlib)."""
    path = os.path.join(src, SCENARIO_COLORS_FILE)
    with open(path, encoding="utf-8") as fh:
        m = re.search(r"^CULORI_SCENARII\s*=\s*(\{.*?\})", fh.read(), re.S | re.M)
    if not m:
        sys.exit(f"ERROR: CULORI_SCENARII not found in {path}")
    return ast.literal_eval(m.group(1))


def lighten(hex_color, share=0.4):
    """The colour mixed with white: a scenario's mark on the dark theme."""
    rgb = [int(hex_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(c + (255 - c) * share):02x}" for c in rgb)


def numeric(cell):
    """A table cell that is a figure (73,6%, ~5,36, +8,0 pp…) rather than prose."""
    t = re.sub(r"\[S\d+\]", "", plain(cell)).strip()
    return bool(t) and len(t) <= 24 and re.match(r"[~≈±+\-−–<>]?\s?\d", t) is not None


# ------------------------------------------------------------------ renderer

class Renderer:
    def __init__(self, mdc, refdefs, published, sources, section_ids, scenarios):
        self.mdc = mdc
        self.refdefs = refdefs
        self.published = published      # report-relative path -> site URL
        self.sources = sources          # "S1" -> tooltip text
        self.section_ids = section_ids  # "6.7" -> "s6-7"
        # a scenario named in the text ("S2", never the citation "[S2]") gets its chart colour
        keys = sorted((k[1:] for k in scenarios), key=len, reverse=True)
        self.scenario_re = re.compile(r"(?<![\[\w])(S(?:" + "|".join(keys) + r"))(?![\]\w])") if keys else None
        self.mark_scenarios = True      # off inside the source list
        # fișierele din repo-ul public (cod, CSV, sub-rapoarte) -> link GitHub; restul text
        self.url_public = getattr(mdc, "url_public", lambda url: None)

    def text(self, s):
        out = []
        pos = 0
        for m in re.finditer(r"<(https?://[^>\s]+)>", s):
            out.append(self._esc(s[pos:m.start()]))
            url = html.escape(m.group(1), quote=True)
            out.append(f'<a href="{url}">{html.escape(m.group(1))}</a>')
            pos = m.end()
        out.append(self._esc(s[pos:]))
        return "".join(out)

    def _esc(self, s):
        e = html.escape(s, quote=False)

        def sect(m):
            sid = self.section_ids.get(m.group(1))
            return f'<a href="#{sid}">{m.group(0)}</a>' if sid else m.group(0)
        e = re.sub(r"§(\d+(?:\.\d+)?)", sect, e)
        if self.scenario_re and self.mark_scenarios:
            e = self.scenario_re.sub(
                lambda m: f'<span class="scen scen-{m.group(1).lower()}">{m.group(1)}</span>', e)
        return e

    def label(self, s):
        if len(s) > 1 and s.startswith("`") and s.endswith("`"):
            return f"<code>{html.escape(s[1:-1])}</code>"
        return self.inline(s, links=False)

    def inline(self, s, links=True):
        out = []
        for tok in self.mdc.tokeni_inline(s, self.refdefs):
            kind = tok[0]
            if kind == "text":
                out.append(self.text(tok[1]))
            elif kind == "bold":
                out.append(f"<strong>{self.text(tok[1])}</strong>")
            elif kind == "italic":
                out.append(f"<em>{self.text(tok[1])}</em>")
            elif kind == "code":
                out.append(f"<code>{html.escape(tok[1])}</code>")
            elif kind == "link":
                lab, url = tok[1], tok[2]
                href = url if url.startswith(("http://", "https://", "#")) else (
                    self.published.get(url.rstrip("/")) or self.url_public(url))
                if href and links:
                    out.append(f'<a href="{html.escape(href, quote=True)}">{self.label(lab)}</a>')
                else:
                    out.append(self.label(lab))
            elif kind == "ref":
                key = tok[1][1:-1]
                if key in self.sources and links:
                    title = html.escape(self.sources[key], quote=True)
                    out.append(f'<a class="ref" href="#sursa-{key[1:]}" title="{title}">{tok[1]}</a>')
                else:
                    out.append(html.escape(tok[1]))
        return "".join(out)


# ------------------------------------------------------------------ build

def split_report(text):
    """-> (front lines, body text): the front matter ends at the first '---' line."""
    lines = text.split("\n")
    try:
        cut = next(i for i, l in enumerate(lines) if l.strip() == "---")
    except StopIteration:
        sys.exit("ERROR: no '---' separator after the report header")
    body = "\n".join(lines[cut + 1:])
    if CUT_HEADING in body:
        body = body[:body.index(CUT_HEADING)]
    return lines[:cut], body


def publish_figure(src, rel):
    """Write the report's PNG chart as lossless WebP (about a third of the bytes,
    pixel-identical) and return its URL."""
    name = os.path.splitext(os.path.basename(rel))[0] + ".webp"
    with Image.open(os.path.join(src, rel)) as im:
        im.save(os.path.join(OUT_DIR, "figuri", name), "WEBP", lossless=True, quality=100, method=6)
    return f"{URL}figuri/{name}"


RO_MONTHS = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
             "august", "septembrie", "octombrie", "noiembrie", "decembrie"]


def iso_date(ro_date):
    """'17 octombrie 2026' -> '2026-10-17' (front matter for the feed, sitemap and JSON-LD)."""
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", ro_date)
    if not m or m.group(2).lower() not in RO_MONTHS:
        sys.exit(f"ERROR: cannot read the report date '{ro_date}'")
    return f"{m.group(3)}-{RO_MONTHS.index(m.group(2).lower()) + 1:02d}-{int(m.group(1)):02d}"


def build(src):
    mdc = load_parser(src)
    md_path = os.path.join(src, REPORT_MD)
    text = mdc.citeste(md_path).replace("\r\n", "\n")
    refdefs = mdc.definitii_referinte(text)
    front, body = split_report(text)

    title = next((l[2:].strip() for l in front if l.startswith("# ")), None)
    subtitle = next((l[3:].strip() for l in front if l.startswith("## ")), "")
    m = re.search(r"\*\*Data raportului:\*\*\s*(.+)", "\n".join(front))
    if not title or not m:
        sys.exit("ERROR: report header must have a '# title' and '**Data raportului:**'")
    report_date = m.group(1).strip()

    blocks = mdc.blocuri(body)

    # --- published files: figures, PDF, Excel
    os.makedirs(os.path.join(OUT_DIR, "figuri"), exist_ok=True)
    published = {}
    for kind, payload in blocks:
        if kind == "img":
            _, rel = mdc.imagine(payload)
            published[rel] = publish_figure(src, rel)
    for rel in re.findall(r"\]\((model/figuri/[^)]+\.png)\)", body):
        if rel not in published and os.path.isfile(os.path.join(src, rel)):
            published[rel] = publish_figure(src, rel)
    for rel in (REPORT_PDF, MODEL_XLSX):
        shutil.copy2(os.path.join(src, rel), os.path.join(OUT_DIR, os.path.basename(rel)))
        published[rel] = f"{URL}{os.path.basename(rel)}"

    # --- first pass: heading ids, TOC, source tooltips, summary leads
    section_ids, heads, used = {}, [], set()
    parent = ""
    for kind, payload in blocks:
        if kind != "head":
            continue
        level, txt = mdc.titlu(payload)
        num = re.match(r"(\d+(?:\.\d+)*)\.?\s", txt)
        if num:
            hid = "s" + num.group(1).replace(".", "-")
            section_ids[num.group(1)] = hid
        else:
            hid = (parent + "-" if level >= 4 and parent else "") + slugify(plain(txt))
        while hid in used:
            hid += "-2"
        used.add(hid)
        if level <= 3:
            parent = hid
        heads.append((level, txt, hid))

    sources = {}
    for kind, payload in blocks:
        if kind == "par":
            sm = re.match(r"\*\*\[(S\d+)\]\*\*\s*(.*)", payload)
            if sm:
                tip = plain(sm.group(2))
                sources[sm.group(1)] = tip if len(tip) <= 170 else tip[:167].rstrip() + "…"

    colors = scenario_colors(src)
    r = Renderer(mdc, refdefs, published, sources, section_ids, colors)

    short_answer = one_liner = None
    leads = []
    in_summary = False
    for kind, payload in blocks:
        if kind == "head":
            in_summary = mdc.titlu(payload)[1].startswith("1.")
        elif kind == "par" and payload.startswith("**Răspunsul scurt:**"):
            short_answer = payload[len("**Răspunsul scurt:**"):].strip()
        elif kind == "par" and payload.startswith("**Răspunsul într-o propoziție:**"):
            one_liner = payload[len("**Răspunsul într-o propoziție:**"):].strip()
        elif kind == "numar" and in_summary:
            prefix, content = mdc.element_lista(kind, payload)
            lm = re.match(r"\*\*(.+?)\*\*", content)
            if lm and prefix:
                leads.append((prefix.strip().rstrip("."), lm.group(1).rstrip(":").strip()))
    if not (short_answer and one_liner and leads):
        sys.exit("ERROR: could not find 'Răspunsul scurt', 'Răspunsul într-o propoziție' "
                 "or the numbered key conclusions in §1")

    # --- second pass: body HTML
    out = []
    open_list = None            # "ul" / "ol"
    in_sources = False
    in_summary = False
    fig_no = 0
    last_head = ""
    head_iter = iter(heads)
    words = 0
    num_columns = 0

    def close_list():
        nonlocal open_list
        if open_list:
            out.append(f"</{open_list}>")
            open_list = None

    for kind, payload in blocks:
        if kind not in ("bullet", "numar"):
            close_list()
        if kind == "head":
            level, txt, hid = next(head_iter)
            in_summary = txt.startswith("1.")
            if in_sources and level <= 2:
                out.append("</div>")
                in_sources = False
                r.mark_scenarios = True
            n = min(level, 4)
            last_head = plain(txt)
            # the section number ("5.", "6.1") in its own span, set in the accent
            head_html = re.sub(r"^(\d+(?:\.\d+)*\.?)(\s)", r'<span class="sec-num">\1</span>\2',
                               r.inline(txt, links=False), count=1)
            out.append(f'<h{n} id="{hid}">{head_html}'
                       f'<a class="ancora" href="#{hid}" aria-label="Link către secțiune">#</a></h{n}>')
            if level == 2 and plain(txt) == "Surse":
                out.append('<div class="surse">')
                in_sources = True
                r.mark_scenarios = False
            words += len(plain(txt).split())
        elif kind == "par":
            sm = re.match(r"\*\*\[(S\d+)\]\*\*", payload)
            attr = f' id="sursa-{sm.group(1)[1:]}" class="sursa"' if sm else ""
            out.append(f"<p{attr}>{r.inline(payload)}</p>")
            words += 0 if in_sources else len(payload.split())
        elif kind in ("bullet", "numar"):
            tag = "ul" if kind == "bullet" else "ol"
            if open_list != tag:
                close_list()
                out.append(f"<{tag}>")
                open_list = tag
            prefix, content = mdc.element_lista(kind, payload)
            num = prefix.strip().rstrip(".")
            value = f' value="{num}"' if prefix else ""
            if prefix and in_summary:
                value += f' id="punct-{num}"'
            out.append(f"<li{value}>{r.inline(content)}</li>")
            words += len(content.split())
        elif kind == "table":
            rows = mdc.randuri_tabel(payload)
            if not rows:
                continue
            label = html.escape(f"Tabel: {last_head} (derulabil orizontal)", quote=True)
            # columns of figures align right, as in a ledger (the first column holds labels)
            num_cols = set()
            for ci in range(1, len(rows[0])):
                vals = [row[ci] for row in rows[1:] if ci < len(row) and plain(row[ci])]
                if len(vals) >= 2 and sum(map(numeric, vals)) >= 0.75 * len(vals):
                    num_cols.add(ci)
            num_columns += len(num_cols)

            def cls(ci):
                return ' class="num"' if ci in num_cols else ""
            t = [f'<div class="tabel-scroll" role="region" tabindex="0" aria-label="{label}">'
                 "<table><thead><tr>"]
            t += [f'<th scope="col"{cls(ci)}>{r.inline(c)}</th>' for ci, c in enumerate(rows[0])]
            t.append("</tr></thead><tbody>")
            for row in rows[1:]:
                t.append("<tr>" + "".join(f"<td{cls(ci)}>{r.inline(c)}</td>"
                                          for ci, c in enumerate(row)) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
        elif kind == "img":
            alt, rel = mdc.imagine(payload)
            fig_no += 1
            src_url = published[rel]
            size = png_size(os.path.join(src, rel))
            dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
            a = html.escape(alt, quote=True)
            out.append(f'<figure><a href="{src_url}"><img src="{src_url}" alt="{a}"{dims} '
                       f'loading="lazy" decoding="async"></a>'
                       f"<figcaption><strong>Figura {fig_no}.</strong> {html.escape(alt)} "
                       f"(clic pentru mărime completă)</figcaption></figure>")
        elif kind == "cod":
            out.append(f"<pre><code>{html.escape(payload)}</code></pre>")
    close_list()
    if in_sources:
        out.append("</div>")

    minutes = max(1, round(words / WORDS_PER_MINUTE / 5) * 5)

    # --- TOC (h2 + h3)
    toc = ['<nav class="toc" id="cuprins" aria-label="Cuprins"><strong>Cuprins</strong><ol>']
    open_sub = False
    for level, txt, hid in heads:
        if level == 2:
            if open_sub:
                toc.append("</ol>")
                open_sub = False
            toc.append(("</li>" if len(toc) > 1 else "")
                       + f'<li><a href="#{hid}">{html.escape(plain(txt))}</a>')
        elif level == 3:
            if not open_sub:
                toc.append("<ol>")
                open_sub = True
            toc.append(f'<li><a href="#{hid}">{html.escape(plain(txt))}</a></li>')
    if open_sub:
        toc.append("</ol>")
    toc.append("</li></ol></nav>")

    # --- header
    summary_id = section_ids.get("1", "s1")
    leads_html = "".join(f'<li><a href="#punct-{n}">{html.escape(plain(l))}</a></li>' for n, l in leads)
    pdf_url, xlsx_url = published[REPORT_PDF], published[MODEL_XLSX]
    repo_url = getattr(mdc, "REPO_PUBLIC", "https://github.com/Infuscy/romania-deficit")
    pdf_size = fmt_size(os.path.join(src, REPORT_PDF))
    xlsx_size = fmt_size(os.path.join(src, MODEL_XLSX))
    header = f"""
<div class="kicker">Finanțe publice · Datoria României · 2026–2040</div>
<h1>{html.escape(title)}</h1>
<p class="subtitlu">{html.escape(subtitle)}</p>
<p class="lede">{r.inline(one_liner)}</p>
<p class="art-meta"><strong>Data raportului:</strong> {html.escape(report_date)} &middot; <strong>Autor:</strong> {AUTHOR} &middot; <strong>Categorie:</strong> analiză de sustenabilitate a datoriei (DSA) &middot; ~{minutes} de minute de citit</p>
<p class="descarcari"><a href="{pdf_url}" download>Descarcă raportul (PDF, {pdf_size})</a> <a href="{xlsx_url}" download>Modelul și rezultatele (Excel, {xlsx_size})</a> <a href="{repo_url}">Codul și datele (GitHub)</a></p>
<p class="small-note nota-ai"><strong>Transparență:</strong> această analiză a fost redactată cu asistența unui sistem de inteligență artificială; cifrele au fost verificate pe surse primare, iar textul a fost revizuit și corectat de autor (revizuire umană). Responsabilitate editorială: {AUTHOR} &mdash; <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
<p class="small-note">Analiză independentă, cu scop informativ: nu este o prognoză oficială și nici consiliere de investiții. Rezultatele marcate „model propriu” provin dintr-un model DSA rulat de autor, calibrat pe date oficiale; trimiterile [S1], [S2]… duc la lista de surse de la final.</p>

<div class="box warn">
<h2>Pe scurt</h2>
<p><strong>Răspunsul scurt:</strong> {r.inline(short_answer)}</p>
<ul>{leads_html}</ul>
<p class="small-note" style="margin: 10px 0 0;">Detaliile și cifrele pentru fiecare punct: <a href="#{summary_id}">Rezumatul executiv</a>.</p>
</div>
"""

    footer = f"""
<div class="box info">
<h3>Despre această ediție web</h3>
<p class="small-note" style="margin: 0;">Pagina este generată din aceeași sursă ca raportul PDF ({html.escape(report_date)}), cu cuprins, trimiteri interne și surse cu link. Codul modelelor (Python), seriile CSV, graficele și rapoartele tematice sunt publice în <a href="{repo_url}">repo-ul GitHub</a> (licențe: CC BY 4.0 pentru texte, date și grafice; MIT pentru cod); rezultatele numerice sunt și în fișierul <a href="{xlsx_url}">Excel</a>. Copiile documentelor altor instituții nu sunt republicate; fiecare are linkul original în lista de surse. Redactarea asistată de AI a fost verificată de autor — declarație de transparență conform art. 50 din Regulamentul (UE) 2024/1689 (AI Act).</p>
</div>
<a class="la-cuprins" href="#cuprins">&uarr; Cuprins</a>
"""

    description = (f"{subtitle}. Răspunsul scurt: {first_sentences(plain(short_answer), 2)}")
    # each scenario's chart colour, and a lighter one for the dark theme
    scenario_css = " ".join(f".civic .scen-{k.lower()} {{ --scen: {v}; --scen-dark: {lighten(v)}; }}"
                            for k, v in sorted(colors.items()))
    page = (
        "---\n"
        "layout: page\n"
        f"title: {yaml_str(title + ' Datoria publică a României 2026–2040')}\n"
        f"description: {yaml_str(description)}\n"
        f"img: {SLUG}.png\n"
        "og_type: article\n"
        f"date_published: {iso_date(report_date)}\n"
        "feed_category: Analiză economică\n"
        f"permalink: {URL}\n"
        f"css: {CIVIC_CSS}\n"
        "---\n"
        "<!-- Generated by scripts/build_romania_deficit.py from "
        f"RomaniaDeficit/{REPORT_MD}. Do not edit by hand. -->\n"
        "{% raw %}\n"
        '<div class="container articol civic civic-deficit">\n'
        f"<style>{scenario_css}</style>\n"
        + header + "\n".join(toc) + "\n" + "\n".join(out) + "\n" + footer
        + "</div>\n{% endraw %}\n"
    )
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)

    marks = page.count('class="scen ')
    print(f"wrote {SLUG}/index.html: {len(heads)} headings, {fig_no} figures, "
          f"{len(sources)} sources, {len(leads)} key points, ~{minutes} min read, "
          f"{marks} scenario marks, {num_columns} figure columns")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", default=DEFAULT_SRC, help="RomaniaDeficit checkout")
    build(os.path.abspath(ap.parse_args().src))


if __name__ == "__main__":
    main()
