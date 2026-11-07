"""Inventory visible template text that is not yet covered by FOCOST i18n keys.

Run from the project root:
    python scripts/audit_i18n_coverage.py

This is an audit aid, not an automatic translator. It intentionally does not
rewrite user-generated content or attempt unsafe heuristic translation.
"""
from collections import Counter
from html import unescape
from pathlib import Path
import csv
import re

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "app" / "templates"
SERVICE_FILE = ROOT / "app" / "services" / "language_service.py"
OUTPUT = ROOT / "docs" / "i18n_template_inventory.csv"


def known_texts(source: str):
    keys = set()
    sections = re.findall(r"TEXT_KEY_MAP\s*=\s*\{(.*?)\}", source, flags=re.S)
    sections += re.findall(r"TEXT_KEY_MAP\.update\(\s*\{(.*?)\}\s*\)", source, flags=re.S)
    for section in sections:
        keys.update(re.findall(r"['\"]([^'\"]+)['\"]\s*:\s*['\"][^'\"]+['\"]", section))
    return keys


def main():
    source = SERVICE_FILE.read_text(encoding="utf-8")
    known = known_texts(source)
    rows = []
    counts = Counter()

    for path in sorted(TEMPLATE_ROOT.rglob("*.html")):
        content = path.read_text(encoding="utf-8", errors="replace")
        content = re.sub(r"{%.*?%}|{{.*?}}", " ", content, flags=re.S)
        content = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", content, flags=re.S | re.I)
        for match in re.finditer(r">([^<>]+)<", content):
            text = " ".join(unescape(match.group(1)).split())
            if len(text) < 3 or not re.search(r"[A-Za-z]", text):
                continue
            if re.fullmatch(r"[-–—|/\s\d.,:%]+", text):
                continue
            line = content.count("\n", 0, match.start()) + 1
            covered = text in known
            counts["covered" if covered else "uncovered"] += 1
            rows.append({
                "template": str(path.relative_to(ROOT)).replace("\\", "/"),
                "line_approx": line,
                "text": text,
                "covered_by_exact_text_map": covered,
            })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["template", "line_approx", "text", "covered_by_exact_text_map"])
        writer.writeheader()
        writer.writerows(rows)

    total = sum(counts.values())
    print(f"Visible text candidates: {total}")
    print(f"Exact-text mapped: {counts['covered']}")
    print(f"Not mapped: {counts['uncovered']}")
    print(f"Inventory: {OUTPUT}")


if __name__ == "__main__":
    main()
