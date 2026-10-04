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
- links to files that exist only in the (private) report repo — code, CSVs,
  sub-reports, archived documents — become plain text, and the
  "Materiale documentare arhivate local" subsection is dropped.

Usage:
    python scripts/build_romania_deficit.py [--src C:\\GIT\\RomaniaDeficit]

Standard library only. The script rewrites only romania-deficit/index.html,
romania-deficit/figuri/*.png and the two download files.
"""
import argparse
import html
import os
import re
import shutil
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

CSS = """
  .articol { font-size: 18.5px; line-height: 1.7; }
  /* The theme sets p { font-size: 1.0625rem } site-wide; the article keeps its own scale. */
  .articol p, .articol li { font-size: 18.5px; line-height: 1.7; }
  .articol .kicker { color: #2563eb; font-weight: bold; letter-spacing: .08em; text-transform: uppercase; font-size: 15px; margin-bottom: 10px; }
  .articol h1 { font-size: 37px; line-height: 1.25; margin-top: 0; }
  .articol .subtitlu { font-size: 21px; color: #475569; margin: 10px 0 0; line-height: 1.45; }
  .articol .lede { font-size: 21px; line-height: 1.6; color: #334155; margin-top: 18px; }
  .articol .art-meta { color: #64748b; font-size: 17px; margin: 14px 0 8px; }
  .articol .small-note { font-size: 16px; color: #64748b; line-height: 1.6; }
  .articol .box { border: 1px solid #cbd5e1; border-radius: 6px; padding: 18px 22px; margin: 22px 0; background: #f8fafc; }
  .articol .box.warn { border-color: #f59e0b; background: #fffbeb; }
  .articol .box.info { border-color: #93c5fd; background: #eff6ff; }
  .articol .box h2, .articol .box h3 { margin-top: 0; font-size: 21px; border: 0; padding: 0; }
  .articol .box ul { margin-bottom: 0; padding-left: 22px; }
  .articol .box li { margin-bottom: 6px; }
  .articol .descarcari { display: flex; flex-wrap: wrap; gap: 10px 18px; margin: 16px 0 6px; font-size: 16.5px; }
  .articol .descarcari a { font-weight: 600; }
  .articol h2 { margin-top: 48px; padding-bottom: 6px; border-bottom: 1px solid #e2e8f0; font-size: 30px; line-height: 1.3; }
  .articol h3 { margin-top: 32px; font-size: 23px; line-height: 1.35; }
  .articol h4 { margin-top: 26px; font-size: 19.5px; color: #1e3a8a; }
  .articol [id] { scroll-margin-top: 90px; }
  .articol .ancora { visibility: hidden; margin-left: 8px; color: #94a3b8; text-decoration: none; font-weight: normal; }
  .articol h2:hover .ancora, .articol h3:hover .ancora, .articol h4:hover .ancora, .articol .ancora:focus { visibility: visible; }
  .articol .toc { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 18px 24px; margin: 24px 0; }
  .articol .toc > ol { margin-bottom: 0; padding-left: 0; list-style: none; }
  .articol .toc li { font-size: 17px; line-height: 1.5; margin: 4px 0; }
  .articol .toc ol ol { list-style: none; padding-left: 22px; margin: 2px 0 6px; }
  .articol .toc ol ol li { font-size: 15.5px; margin: 2px 0; }
  .articol .tabel-scroll { overflow-x: auto; margin: 6px 0 22px; border: 1px solid #e2e8f0; border-radius: 6px; }
  .articol .tabel-scroll:focus-visible { outline: 3px solid rgba(37,99,235,.55); }
  .articol table { border-collapse: collapse; width: 100%; font-size: 15.5px; line-height: 1.45; }
  .articol th, .articol td { padding: 7px 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; text-align: left; }
  .articol th { background: #f1f5f9; font-weight: 700; }
  .articol tbody tr:nth-child(even) td { background: #fafbfc; }
  .articol td:first-child, .articol th:first-child { min-width: 9em; }
  .articol figure { margin: 26px 0; }
  .articol figure img { width: 100%; height: auto; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; }
  .articol figcaption { font-size: 15.5px; color: #64748b; margin-top: 6px; }
  .articol pre { font-size: 15px; white-space: pre-wrap; }
  .articol a.ref { font-size: .8em; text-decoration: none; white-space: nowrap; }
  .articol .surse p { font-size: 15.5px; line-height: 1.55; overflow-wrap: anywhere; }
  .articol .surse p:target, .articol .surse p.sursa:target { background: #fef9c3; outline: 6px solid #fef9c3; }
  .articol .la-cuprins { position: fixed; left: 18px; bottom: 18px; z-index: 20; background: #0f172a; color: #fff; border-radius: 999px; padding: 8px 16px; font-size: 15px; font-weight: 600; box-shadow: 0 4px 14px rgb(15 23 42 / .25); text-decoration: none; }
  .articol .la-cuprins:hover, .articol .la-cuprins:focus { background: #2563eb; color: #fff; }
  @media (max-width: 767px) {
    .articol, .articol p, .articol li { font-size: 17px; }
    .articol h1 { font-size: 29px; }
    .articol h2 { font-size: 24px; }
    .articol h3 { font-size: 20px; }
    .articol .lede, .articol .subtitlu { font-size: 18.5px; }
    .articol .box { padding: 14px 16px; }
    .articol table { font-size: 14.5px; }
  }
  @media print { .articol .la-cuprins, .articol .ancora { display: none; } }
"""


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


# ------------------------------------------------------------------ renderer

class Renderer:
    def __init__(self, mdc, refdefs, published, sources, section_ids):
        self.mdc = mdc
        self.refdefs = refdefs
        self.published = published      # report-relative path -> site URL
        self.sources = sources          # "S1" -> tooltip text
        self.section_ids = section_ids  # "6.7" -> "s6-7"

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
        return re.sub(r"§(\d+(?:\.\d+)?)", sect, e)

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
                href = url if url.startswith(("http://", "https://", "#")) else self.published.get(url.rstrip("/"))
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
            name = os.path.basename(rel)
            shutil.copy2(os.path.join(src, rel), os.path.join(OUT_DIR, "figuri", name))
            published[rel] = f"{URL}figuri/{name}"
    for rel in re.findall(r"\]\((model/figuri/[^)]+\.png)\)", body):
        if rel not in published and os.path.isfile(os.path.join(src, rel)):
            name = os.path.basename(rel)
            shutil.copy2(os.path.join(src, rel), os.path.join(OUT_DIR, "figuri", name))
            published[rel] = f"{URL}figuri/{name}"
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

    r = Renderer(mdc, refdefs, published, sources, section_ids)

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
    head_iter = iter(heads)
    words = 0

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
            n = min(level, 4)
            out.append(f'<h{n} id="{hid}">{r.inline(txt, links=False)}'
                       f'<a class="ancora" href="#{hid}" aria-label="Link către secțiune">#</a></h{n}>')
            if level == 2 and plain(txt) == "Surse":
                out.append('<div class="surse">')
                in_sources = True
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
            t = ['<div class="tabel-scroll" role="region" tabindex="0" aria-label="Tabel (derulabil orizontal)">'
                 "<table><thead><tr>"]
            t += [f"<th>{r.inline(c)}</th>" for c in rows[0]]
            t.append("</tr></thead><tbody>")
            for row in rows[1:]:
                t.append("<tr>" + "".join(f"<td>{r.inline(c)}</td>" for c in row) + "</tr>")
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
    pdf_size = fmt_size(os.path.join(src, REPORT_PDF))
    xlsx_size = fmt_size(os.path.join(src, MODEL_XLSX))
    header = f"""
<div class="kicker">Finanțe publice · Datoria României · 2026–2040</div>
<h1>{html.escape(title)}</h1>
<p class="subtitlu">{html.escape(subtitle)}</p>
<p class="lede">{r.inline(one_liner)}</p>
<p class="art-meta"><strong>Data raportului:</strong> {html.escape(report_date)} &middot; <strong>Autor:</strong> {AUTHOR} &middot; <strong>Categorie:</strong> analiză de sustenabilitate a datoriei (DSA) &middot; ~{minutes} de minute de citit</p>
<p class="descarcari"><a href="{pdf_url}" download>Descarcă raportul (PDF, {pdf_size})</a> <a href="{xlsx_url}" download>Modelul și rezultatele (Excel, {xlsx_size})</a></p>
<p class="small-note"><strong>Transparență:</strong> această analiză a fost redactată cu asistența unui sistem de inteligență artificială; cifrele au fost verificate pe surse primare, iar textul a fost revizuit și corectat de autor (revizuire umană). Responsabilitate editorială: {AUTHOR} &mdash; <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
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
<p class="small-note" style="margin: 0;">Pagina este generată din aceeași sursă ca raportul PDF ({html.escape(report_date)}), cu cuprins, trimiteri interne și surse cu link. Codul modelelor (Python), seriile CSV, rapoartele tematice și documentele arhivate pe care le citează raportul nu sunt publicate pe site; rezultatele lor numerice sunt în fișierul <a href="{xlsx_url}">Excel</a>. Redactarea asistată de AI a fost verificată de autor — declarație de transparență conform art. 50 din Regulamentul (UE) 2024/1689 (AI Act).</p>
</div>
<a class="la-cuprins" href="#cuprins">&uarr; Cuprins</a>
"""

    description = (f"{subtitle}. Răspunsul scurt: {first_sentences(plain(short_answer), 2)}")
    page = (
        "---\n"
        "layout: page\n"
        f"title: {yaml_str(title + ' Datoria publică a României 2026–2040')}\n"
        f"description: {yaml_str(description)}\n"
        f"img: {SLUG}.png\n"
        "og_type: article\n"
        "twitter_card: summary_large_image\n"
        f"permalink: {URL}\n"
        "---\n"
        "<!-- Generated by scripts/build_romania_deficit.py from "
        f"RomaniaDeficit/{REPORT_MD}. Do not edit by hand. -->\n"
        "{% raw %}\n"
        '<div class="container articol" style="padding-top: 110px; max-width: 920px;">\n'
        f"<style>{CSS}</style>\n"
        + header + "\n".join(toc) + "\n" + "\n".join(out) + "\n" + footer
        + "</div>\n{% endraw %}\n"
    )
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)

    print(f"wrote {SLUG}/index.html: {len(heads)} headings, {fig_no} figures, "
          f"{len(sources)} sources, {len(leads)} key points, ~{minutes} min read")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", default=DEFAULT_SRC, help="RomaniaDeficit checkout")
    build(os.path.abspath(ap.parse_args().src))


if __name__ == "__main__":
    main()
