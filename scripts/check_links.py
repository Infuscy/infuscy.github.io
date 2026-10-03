"""Fail on broken internal links in a built site.

Scans every .html file under the build dir for href/src values that point inside
the site (root-relative or relative), and checks that each resolves to a file
(a directory resolves to its index.html). External, mailto:, data: and pure
#fragment links are skipped.

Usage: python scripts/check_links.py _site
"""
import os
import re
import sys
from urllib.parse import unquote, urlsplit

ATTR = re.compile(r'''(?:href|src)\s*=\s*["']([^"'<>]+)["']''', re.I)
SKIP = ("http://", "https://", "//", "mailto:", "data:", "javascript:", "#", "tel:")


def resolve(root, page_dir, link):
    path = unquote(urlsplit(link).path)
    if not path:
        return True
    target = os.path.join(root, path.lstrip("/")) if path.startswith("/") else os.path.join(page_dir, path)
    target = os.path.normpath(target)
    if os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return os.path.isfile(target)


def main(root):
    broken = []
    pages = 0
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".html"):
                continue
            pages += 1
            page = os.path.join(dirpath, name)
            with open(page, encoding="utf-8", errors="replace") as fh:
                html = fh.read()
            for link in set(ATTR.findall(html)):
                if link.startswith(SKIP) or "{{" in link:
                    continue
                if not resolve(root, dirpath, link):
                    broken.append(f"{os.path.relpath(page, root)}: {link}")
    print(f"pages scanned: {pages}")
    if broken:
        print(f"BROKEN LINKS ({len(broken)}):")
        for b in sorted(broken):
            print("  " + b)
        return 1
    print("links: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "_site"))
