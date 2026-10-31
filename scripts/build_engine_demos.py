"""Copy the three Asteroids-lite web builds from the GameEngines benchmark into the site.

Source: C:/GIT/GameEngines/bench/<engine>/builds/web (the builds the 28 Oct 2026 sessions made,
change request included). Target: claude-code-2d-engines/play/<engine>/, served next to the article.

Each copy is the build as shipped, plus three edits to its index.html: a meta CSP (inline scripts
pinned by sha256, eval sources only where an engine needs them, see EXTRA_SCRIPT_SRC), the site's
referrer meta, and rel="noopener" on target="_blank" links. Each folder also gets a LICENSES.txt.

Usage: py scripts/build_engine_demos.py          (needs the Godot 4.7.2 console exe for its notices)
"""
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = "C:/GIT/GameEngines/bench"
GODOT = "C:/Tools/Godot/4.7.2/Godot_v4.7.2-stable_win64_console.exe"
DEST = os.path.join(SITE, "claude-code-2d-engines", "play")

GAMES = {
    "phaser": os.path.join(BENCH, "phaser", "builds", "web"),
    "godot": os.path.join(BENCH, "godot", "builds", "web"),
    "defold": os.path.join(BENCH, "defold", "builds", "web", "Asteroids-lite"),
}
# Extra script-src sources per engine. Both WebAssembly engines also need 'unsafe-eval': the Godot
# game reads ?seed= through JavaScriptBridge.eval, and Defold's engine evaluates JS strings at
# startup (without it the canvas stays blank and nothing is logged). Phaser needs neither.
EXTRA_SCRIPT_SRC = {
    "phaser": [],
    "godot": ["'wasm-unsafe-eval'", "'unsafe-eval'"],
    "defold": ["'wasm-unsafe-eval'", "'unsafe-eval'"],
}

INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", re.S | re.I)
INLINE_HANDLER = re.compile(r"\son[a-z]+=\"([^\"]*)\"", re.I)  # e.g. Defold's Fullscreen button
META_CHARSET = re.compile(r"<meta\s+charset[^>]*>", re.I)
BLANK_LINK = re.compile(r"<a\b(?![^>]*\brel=)([^>]*\btarget=\"_blank\"[^>]*)>", re.I)

PRINT_LICENSES_GD = """extends SceneTree

func _init() -> void:
\tvar out := FileAccess.open(OS.get_cmdline_user_args()[0], FileAccess.WRITE)
\tout.store_line("Godot Engine %s" % Engine.get_version_info().string)
\tout.store_line("")
\tout.store_line(Engine.get_license_text())
\tout.store_line("")
\tout.store_line("==== Third-party components (Engine.get_copyright_info) ====")
\tfor c in Engine.get_copyright_info():
\t\tout.store_line("")
\t\tout.store_line("- " + str(c["name"]))
\t\tfor p in c["parts"]:
\t\t\tout.store_line("  Files: " + ", ".join(PackedStringArray(p["files"])))
\t\t\tfor line in p["copyright"]:
\t\t\t\tout.store_line("  Copyright: " + str(line))
\t\t\tout.store_line("  License: " + str(p["license"]))
\tout.store_line("")
\tout.store_line("==== Licence texts (Engine.get_license_info) ====")
\tvar info := Engine.get_license_info()
\tfor k in info.keys():
\t\tout.store_line("")
\t\tout.store_line("---- " + str(k) + " ----")
\t\tout.store_line(str(info[k]))
\tout.close()
\tquit()
"""

HEADER = (
    "Asteroids-lite, {engine} web build\n"
    "Built by a Claude Code session in the benchmark of 28 October 2026 described in the article.\n"
    "Article: https://infuscy.github.io/claude-code-2d-engines/\n\n"
    "This build contains third-party software. Its licence notices follow.\n\n"
)


def sha(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode() + "'"


def csp(html, extra):
    scripts = ["'self'"] + extra + [sha(s) for s in INLINE_SCRIPT.findall(html)]
    handlers = INLINE_HANDLER.findall(html)
    if handlers:
        scripts += ["'unsafe-hashes'"] + [sha(h) for h in handlers]
    return ("default-src 'self'; script-src " + " ".join(scripts) + "; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; media-src 'self' data: blob:; connect-src 'self' data: blob:; "
            "object-src 'none'; base-uri 'self'; form-action 'self'")


def patch_index(path, extra):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    metas = ('<meta http-equiv="Content-Security-Policy" content="%s">\n'
             '<meta name="referrer" content="strict-origin-when-cross-origin">' % csp(html, extra))
    m = META_CHARSET.search(html)
    if not m:
        sys.exit("no <meta charset> in " + path)
    if not re.search(r"<link[^>]*rel=\"icon\"", html, re.I):
        metas += '\n<link rel="icon" href="/img/profile.png">'  # else the browser asks for /favicon.ico
    html = html[:m.end()] + "\n" + metas + html[m.end():]
    html = BLANK_LINK.sub(r'<a\1 rel="noopener">', html)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def godot_notices():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "project.godot"), "w") as f:
            f.write("config_version=5\n")
        with open(os.path.join(tmp, "print_licenses.gd"), "w", newline="\n") as f:
            f.write(PRINT_LICENSES_GD)
        out = os.path.join(tmp, "notices.txt")
        subprocess.run([GODOT, "--headless", "--path", tmp, "--script", "res://print_licenses.gd", "--", out],
                       check=True, capture_output=True, timeout=120)
        return read(out)


def licenses(engine):
    if engine == "phaser":
        pnpm = os.path.join(BENCH, "phaser", "game", "node_modules")
        ee3 = [d for d in os.listdir(os.path.join(pnpm, ".pnpm")) if d.startswith("eventemitter3@")][0]
        return ("==== Phaser 4.2.1 (MIT) ====\n\n" + read(os.path.join(pnpm, "phaser", "LICENSE.md"))
                + "\n\n==== " + ee3 + " (MIT), bundled by Phaser ====\n\n"
                + read(os.path.join(pnpm, ".pnpm", ee3, "node_modules", "eventemitter3", "LICENSE")))
    if engine == "godot":
        return godot_notices()
    return ("==== Defold 1.14.0 ====\n\n"
            "This build contains the Defold engine, distributed under the Defold License, Version 1.0\n"
            "(based on the Apache License 2.0). Full licence text: https://defold.com/license/\n"
            "Third-party components in the engine, with their licences and attribution:\n"
            "https://github.com/defold/defold/blob/dev/COMPLYING_WITH_LICENSES.md\n")


def main():
    os.makedirs(DEST, exist_ok=True)
    # core.autocrlf is on in this repo: store the builds byte for byte, so the CSP hashes and the
    # minified engine files stay exactly as built.
    with open(os.path.join(DEST, ".gitattributes"), "w", newline="\n") as f:
        f.write("* -text\n")
    for engine, src in GAMES.items():
        dst = os.path.join(DEST, engine)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        patch_index(os.path.join(dst, "index.html"), EXTRA_SCRIPT_SRC[engine])
        with open(os.path.join(dst, "LICENSES.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(HEADER.format(engine=engine.capitalize()) + licenses(engine))
        size = sum(os.path.getsize(os.path.join(r, n)) for r, _, fs in os.walk(dst) for n in fs)
        print(json.dumps({"engine": engine, "files": sum(len(fs) for _, _, fs in os.walk(dst)),
                          "mb": round(size / 1048576, 2)}))


if __name__ == "__main__":
    main()
