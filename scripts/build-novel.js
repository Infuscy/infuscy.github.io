// Build script: converts translated/*.md → translated/*.html + _data/novel_chapters.json
// Run once: node scripts/build-novel.js
// Re-run whenever chapters are added/updated.

const fs = require('fs');
const path = require('path');

const TRANSLATED_DIR = path.join(__dirname, '..', 'translated');
const DATA_DIR = path.join(__dirname, '..', '_data');
const NOVEL_TITLE = 'The Wobbly Peach'; // ponytail: hardcoded, extract from source if needed

// ---- Markdown to HTML (minimal — chapters are mostly plain prose) ----

function mdToHtml(text) {
  if (!text) return '';
  const paragraphs = text.split(/\n\n+/);
  return paragraphs
    .map(p => {
      p = p.trim();
      if (!p) return '';
      // Horizontal rule
      if (p === '---' || p === '***' || p === '* * *') return '<hr>';
      // Headings (## Flags, ## Author's Postscript, etc.)
      if (p.startsWith('## ')) {
        const heading = p.replace(/^## /, '');
        return `<h2>${inlineMarkdown(heading)}</h2>`;
      }
      // Paragraph
      return `<p>${inlineMarkdown(p)}</p>`;
    })
    .filter(Boolean)
    .join('\n');
}

function inlineMarkdown(text) {
  // Escape HTML entities first
  text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // Bold
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Italic (must run after bold to avoid matching **)
  text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
  return text;
}

function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ---- Parse a chapter ----

function parseChapter(content) {
  // Find Flags section boundary
  const flagsMatch = content.match(/\n## Flags/);
  let body, flagsRaw;

  if (flagsMatch) {
    body = content.slice(0, flagsMatch.index).trim();
    flagsRaw = content.slice(flagsMatch.index + 1).trim();
  } else {
    body = content.trim();
    flagsRaw = null;
  }

  // Extract heading: first line is "## Chapter N: Title"
  const headingMatch = body.match(/^## (Chapter \d+: .+)$/m);
  const heading = headingMatch ? headingMatch[1] : 'Chapter';
  const title = heading.replace(/^Chapter \d+: /, '');

  // Remove heading from body
  body = body.replace(/^## Chapter \d+: .+\n*/, '').trim();

  // Remove trailing --- separator before Flags
  body = body.replace(/\n*---\s*$/, '').trim();

  return { heading, title, bodyHtml: mdToHtml(body), flagsHtml: flagsRaw ? mdToHtml(flagsRaw) : null };
}

// ---- Main ----

function main() {
  // Read and sort all chapter files
  const allFiles = fs.readdirSync(TRANSLATED_DIR)
    .filter(f => /^chapter\d+\.md$/.test(f));

  const fileMap = {}; // chapterNum -> baseFilename (without extension)
  for (const f of allFiles) {
    const num = parseInt(f.match(/\d+/)[0]);
    fileMap[num] = f.replace(/\.md$/, '');
  }

  const chapterNums = Object.keys(fileMap).map(Number).sort((a, b) => a - b);

  const chapters = [];
  let generated = 0;

  for (const num of chapterNums) {
    const baseName = fileMap[num];
    const mdPath = path.join(TRANSLATED_DIR, baseName + '.md');
    const content = fs.readFileSync(mdPath, 'utf-8');
    const parsed = parseChapter(content);

    chapters.push({ num, title: parsed.title, file: baseName + '.html' });

    // Build prev/next links
    const prevBase = num > 1 ? fileMap[num - 1] : null;
    const nextBase = num < chapterNums.length ? fileMap[num + 1] : null;

    const prevLink = prevBase ? `<a href="${prevBase}.html" class="reader-nav-link">← Chapter ${num - 1}</a>` : `<span class="reader-nav-link disabled">← Start</span>`;
    const nextLink = nextBase ? `<a href="${nextBase}.html" class="reader-nav-link">Chapter ${num + 1} →</a>` : `<span class="reader-nav-link disabled">End →</span>`;

    const flagsBlock = parsed.flagsHtml
      ? `\n<details class="flags-section">\n<summary>Translator Notes</summary>\n${parsed.flagsHtml}\n</details>`
      : '';

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(parsed.heading)} — ${escapeHtml(NOVEL_TITLE)}</title>
<link rel="stylesheet" href="/style.css">
<link rel="stylesheet" href="/css/font-awesome/css/font-awesome.min.css">
<style>
/* Reading layout — ponytail: inline so generated pages need no Jekyll build */
:root {
  --reader-max: 42rem;
  --reader-bg: #fefefe;
  --reader-text: #1e293b;
  --reader-muted: #64748b;
  --reader-accent: #2563eb;
  --reader-border: #e2e8f0;
}
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
.reader-top-bar a {
  color: var(--reader-accent);
  text-decoration: none;
  font-weight: 600;
}
.reader-top-bar a:hover { text-decoration: underline; }
.reader-progress {
  color: var(--reader-muted);
  font-size: .85rem;
}
.reader-content {
  max-width: var(--reader-max);
  margin: 0 auto;
  padding: 2.5rem 1.25rem 3rem;
}
.reader-content h1 {
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -.02em;
  color: #0f172a;
  margin: 0 0 2rem;
  text-align: center;
}
.reader-content h2 {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 2rem 0 .75rem;
  color: #0f172a;
}
.reader-content p {
  font-size: 1.1rem;
  line-height: 1.8;
  margin: 0 0 1.25rem;
  color: var(--reader-text);
}
.reader-content hr {
  border: 0;
  text-align: center;
  margin: 2rem auto;
  max-width: 6rem;
}
.reader-content hr::before {
  content: '· · ·';
  color: var(--reader-muted);
  font-size: 1.2rem;
  letter-spacing: .3em;
}
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
.reader-nav-link:hover {
  background: #eff6ff;
  border-color: var(--reader-accent);
}
.reader-nav-link.disabled {
  color: var(--reader-muted);
  border-color: transparent;
  pointer-events: none;
}
.reader-toc-link {
  color: var(--reader-muted);
  text-decoration: none;
  font-size: .9rem;
}
.reader-toc-link:hover { color: var(--reader-accent); }

/* Flags */
.flags-section {
  max-width: var(--reader-max);
  margin: 2rem auto 0;
  padding: 0 1.25rem;
}
.flags-section summary {
  cursor: pointer;
  color: var(--reader-muted);
  font-size: .9rem;
  font-weight: 600;
  padding: .5rem 0;
  border-top: 1px solid var(--reader-border);
  margin-top: 2rem;
}
.flags-section summary:hover { color: var(--reader-text); }
.flags-section h2 { font-size: 1rem; font-weight: 700; margin: 1rem 0 .5rem; }
.flags-section p { font-size: .9rem; line-height: 1.6; color: var(--reader-muted); }

@media (max-width: 600px) {
  .reader-content { padding: 1.5rem 1rem 2rem; }
  .reader-content h1 { font-size: 1.4rem; }
  .reader-content p { font-size: 1.05rem; line-height: 1.75; }
}
</style>
</head>
<body>
<div class="reader-top-bar">
  <a href="/novel/">← Table of Contents</a>
  <span class="reader-progress">Chapter ${num} of ${chapterNums.length}</span>
</div>
<main class="reader-content">
<h1>${escapeHtml(parsed.heading)}</h1>
${parsed.bodyHtml}
</main>
${flagsBlock}
<nav class="reader-bottom-nav">
  ${prevLink}
  <a href="/novel/" class="reader-toc-link">Contents</a>
  ${nextLink}
</nav>
</body>
</html>`;

    const htmlPath = path.join(TRANSLATED_DIR, baseName + '.html');
    fs.writeFileSync(htmlPath, html, 'utf-8');
    generated++;
  }

  // Write chapter list for Jekyll ToC page
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  const jsonPath = path.join(DATA_DIR, 'novel_chapters.json');
  fs.writeFileSync(jsonPath, JSON.stringify(chapters, null, 2), 'utf-8');

  console.log(`Done. ${generated} HTML pages generated.`);
  console.log(`Chapter list: ${jsonPath}`);
}

main();
