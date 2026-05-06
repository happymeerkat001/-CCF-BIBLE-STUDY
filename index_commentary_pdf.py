#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


VERSE_RE = re.compile(r"(?<!\d)(\d+):(\d+)(?:-(\d+))?")
BOOK_ORDER = [
    "matthew",
    "mark",
    "luke",
    "john",
    "acts",
    "romans",
    "1corinthians",
    "2corinthians",
    "galatians",
    "ephesians",
    "philippians",
    "colossians",
    "1thessalonians",
    "2thessalonians",
    "1timothy",
    "2timothy",
    "titus",
    "philemon",
    "hebrews",
    "james",
    "1peter",
    "2peter",
    "1john",
    "2john",
    "3john",
    "jude",
    "revelation",
]
BOOK_HEADINGS = {
    "matthew": "Matthew",
    "mark": "Mark",
    "luke": "Luke",
    "john": "John",
    "acts": "Acts",
    "romans": "Romans",
    "1corinthians": "1 Corinthians",
    "2corinthians": "2 Corinthians",
    "galatians": "Galatians",
    "ephesians": "Ephesians",
    "philippians": "Philippians",
    "colossians": "Colossians",
    "1thessalonians": "1 Thessalonians",
    "2thessalonians": "2 Thessalonians",
    "1timothy": "1 Timothy",
    "2timothy": "2 Timothy",
    "titus": "Titus",
    "philemon": "Philemon",
    "hebrews": "Hebrews",
    "james": "James",
    "1peter": "1 Peter",
    "2peter": "2 Peter",
    "1john": "1 John",
    "2john": "2 John",
    "3john": "3 John",
    "jude": "Jude",
    "revelation": "Revelation",
}


def extract_pdf_text(pdf_path: Path) -> str:
    errors: list[str] = []

    try:
        import fitz  # type: ignore

        with fitz.open(pdf_path) as document:
            return "\n".join(page.get_text("text") for page in document)
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"PyMuPDF failed: {exc}")

    try:
        import pdfplumber  # type: ignore

        chunks: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                chunks.append(page.extract_text() or "")
        return "\n".join(chunks)
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"pdfplumber failed: {exc}")

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"pypdf failed: {exc}")

    raise RuntimeError(
        "Could not extract text from the PDF. Install one of: pymupdf, pdfplumber, or pypdf.\n"
        + "\n".join(f"- {error}" for error in errors)
    )


def extract_pdf_text_for_book(pdf_path: Path, book: str) -> str:
    try:
        import fitz  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        return extract_pdf_text(pdf_path)

    book_heading = BOOK_HEADINGS.get(book)
    if not book_heading:
        return extract_pdf_text(pdf_path)

    with fitz.open(pdf_path) as document:
        pages = [page.get_text("text") for page in document]

    start_page = _find_book_start_page(pages, book_heading)
    if start_page is None:
        return "\n".join(pages)

    end_page = len(pages)
    for next_book in BOOK_ORDER[BOOK_ORDER.index(book) + 1 :]:
        next_heading = BOOK_HEADINGS[next_book]
        next_page = _find_book_start_page(pages, next_heading)
        if next_page is not None and next_page > start_page:
            end_page = next_page
            break

    return "\n".join(pages[start_page:end_page])


def _find_book_start_page(pages: list[str], heading: str) -> int | None:
    heading_re = re.compile(rf"^\s*{re.escape(heading)}\s*\nINTRODUCTION\b", re.MULTILINE)
    for index, text in enumerate(pages):
        if heading_re.search(text):
            return index
    return None


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = text.replace("\u00AD", "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def build_commentary_index(text: str) -> dict[str, list[str]]:
    normalized = normalize_text(text)
    matches = list(VERSE_RE.finditer(normalized))
    index: dict[str, list[str]] = {}
    for i, match in enumerate(matches):
        chapter = int(match.group(1))
        start_verse = int(match.group(2))
        end_verse = int(match.group(3) or start_verse)
        chunk_start = match.end()
        chunk_end = matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
        note = _clean_note_chunk(normalized[chunk_start:chunk_end])
        if not note:
            continue
        for verse_num in range(start_verse, end_verse + 1):
            index.setdefault(f"{chapter}:{verse_num}", []).append(note)
    return dict(sorted(index.items(), key=_sort_key))


def _clean_note_chunk(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(" -\n\t")
    cleaned = re.sub(r"^[:.;,)\]]+\s*", "", cleaned)
    return cleaned


def _sort_key(item: tuple[str, list[str]]) -> tuple[int, int]:
    chapter, verse = item[0].split(":")
    return int(chapter), int(verse)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a verse-keyed JSON index from a commentary PDF.")
    parser.add_argument("--pdf", required=True, help="Path to the commentary PDF.")
    parser.add_argument("--book", required=True, help="Canonical book slug used in runtime lookup, e.g. john.")
    parser.add_argument("--key", required=True, help="Commentary key, e.g. pentecost or keener.")
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to data/{key}_{book}.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    book = args.book.strip().lower()
    key = args.key.strip().lower()
    pdf_path = Path(args.pdf).expanduser()
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    output_path = Path(args.output or f"data/{key}_{book}.json")
    text = extract_pdf_text_for_book(pdf_path, book)
    index = build_commentary_index(text)
    if not index:
        raise SystemExit("No chapter:verse note anchors were parsed from the PDF.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output_path)
    print(f"Indexed {len(index)} verse entries", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
