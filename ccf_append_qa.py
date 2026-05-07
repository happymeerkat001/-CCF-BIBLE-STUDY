#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

COMMENTARY_OPEN_RE = re.compile(
    r"<details>\n<summary><strong>Commentary — (?P<book>[^<]+?) (?P<verse>\d+:\d+)</strong></summary>\n",
    re.MULTILINE,
)
CCF_SUMMARY_RE = re.compile(r"<summary>✏️  CCF 問題與解答 \((\d+) notes?\)</summary>")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append CCF Q&A foldable commentary blocks to an existing diagram markdown file."
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to the diagram markdown file.")
    parser.add_argument("--qa", required=True, type=Path, help="Path to the CCF Q&A JSON index.")
    return parser.parse_args()


def load_qa_index(path: Path) -> dict[str, list[str]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Q&A JSON root must be an object keyed by chapter:verse.")
    normalized: dict[str, list[str]] = {}
    for verse_key, entries in data.items():
        if not isinstance(verse_key, str) or not isinstance(entries, list) or not all(
            isinstance(entry, str) for entry in entries
        ):
            raise ValueError("Each Q&A entry must be keyed by a string with a list of strings.")
        normalized[verse_key] = entries
    return normalized


def find_matching_details_close(text: str, open_start: int) -> int:
    cursor = open_start
    depth = 0
    tag_re = re.compile(r"</?details>")
    while True:
        match = tag_re.search(text, cursor)
        if match is None:
            raise ValueError("Unbalanced <details> tags in markdown input.")
        if match.group() == "<details>":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return match.start()
        cursor = match.end()


def remove_existing_ccf_block(block: str) -> str:
    summary_match = CCF_SUMMARY_RE.search(block)
    if summary_match is None:
        return block

    open_start = block.rfind("<details>\n", 0, summary_match.start())
    if open_start == -1:
        return block
    close_start = find_matching_details_close(block, open_start)
    close_end = close_start + len("</details>")
    while close_end < len(block) and block[close_end] == "\n":
        close_end += 1
    return block[:open_start] + block[close_end:]


def format_ccf_block(entries: list[str]) -> str:
    note_word = "note" if len(entries) == 1 else "notes"
    lines = [
        "<details>",
        f"<summary>✏️  CCF 問題與解答 ({len(entries)} {note_word})</summary>",
        "",
    ]
    for entry in entries:
        entry_lines = [line.strip() for line in entry.splitlines() if line.strip()]
        if not entry_lines:
            continue
        lines.append(f"- {entry_lines[0]}")
        for extra_line in entry_lines[1:]:
            lines.append(f"- {extra_line}")
    lines.append("</details>")
    return "\n".join(lines)


def inject_ccf_blocks(text: str, qa_index: dict[str, list[str]]) -> tuple[str, int]:
    result: list[str] = []
    last_index = 0
    injections = 0

    for match in COMMENTARY_OPEN_RE.finditer(text):
        open_start = match.start()
        result.append(text[last_index:open_start])

        close_start = find_matching_details_close(text, open_start)
        close_end = close_start + len("</details>")
        block = text[open_start:close_end]
        verse_key = match.group("verse")

        cleaned_block = remove_existing_ccf_block(block)
        entries = qa_index.get(verse_key, [])
        if entries:
            ccf_block = format_ccf_block(entries)
            cleaned_block = cleaned_block[:-len("</details>")] + ccf_block + "\n</details>"
            injections += 1

        result.append(cleaned_block)
        last_index = close_end

    result.append(text[last_index:])
    return "".join(result), injections


def main() -> int:
    args = parse_args()
    qa_index = load_qa_index(args.qa)
    original_text = args.input.read_text(encoding="utf-8")
    updated_text, injections = inject_ccf_blocks(original_text, qa_index)
    changed = updated_text != original_text
    if changed:
        args.input.write_text(updated_text, encoding="utf-8")
    status = "updated" if changed else "no changes"
    print(f"Processed {injections} commentary block(s); file {status}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
