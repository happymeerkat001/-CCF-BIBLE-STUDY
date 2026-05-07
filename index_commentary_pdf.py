#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


VERSE_RE = re.compile(r"(?<!\d)(\d+):(\d+)(?:-(\d+))?")
# Chinese number words → digits for chapter detection in CCF headers
_CN_DIGITS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
    "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
    "二十一": 21, "二十二": 22, "二十三": 23, "二十四": 24, "二十五": 25,
    "二十六": 26, "二十七": 27, "二十八": 28,
}
# Known Chinese book name prefixes used in cross-references (not John itself)
_CROSS_REF_BOOK_PREFIXES = (
    "路", "太", "可", "腓", "弗", "西", "帖", "提", "多", "門",
    "來", "雅", "彼", "約壹", "約貳", "約叁", "猶", "啟",
    "創", "出", "利", "民", "申", "書", "士", "得", "撒",
    "王", "代", "拉", "尼", "斯", "伯", "詩", "箴", "傳",
    "歌", "賽", "耶", "哀", "結", "但", "何", "珥", "摩",
    "俄", "拿", "彌", "鴻", "哈", "番", "該", "亞", "瑪",
    "徒", "羅", "林", "加",
    "路加福音", "馬太福音", "馬可福音", "使徒行傳",
    "腓立比書", "以弗所書", "歌羅西書", "彼得前書", "彼得後書",
)
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


def ocr_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF via OCR (for PDFs with broken font encodings)."""
    import fitz  # type: ignore

    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "OCR requires pytesseract and Pillow. "
            "Install: pip install pytesseract Pillow; brew install tesseract tesseract-lang"
        ) from exc

    import io

    doc = fitz.open(pdf_path)
    pages: list[str] = []
    for page in doc:
        # 3x zoom for better CJK OCR accuracy
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(
            img, lang="chi_tra+eng",
            config="--psm 6",
        )
        pages.append(text)
    return "\n".join(pages)


def _text_looks_garbled(text: str) -> bool:
    """Heuristic: if CJK text has very few real CJK chars, extraction is garbled."""
    cjk_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf")
    total = len(text.strip())
    if total < 50:
        return True
    return cjk_count / total < 0.05


def _detect_chapter_from_header(text: str) -> int | None:
    """Detect chapter number from CCF header like '第十三章'."""
    match = re.search(r"第([一二三四五六七八九十]+)章", text)
    if not match:
        return None
    cn = match.group(1)
    return _CN_DIGITS.get(cn)


def _is_cross_reference(text_before_ref: str) -> bool:
    """Check if a verse reference is preceded by a cross-ref book name."""
    stripped = text_before_ref.rstrip()
    for prefix in _CROSS_REF_BOOK_PREFIXES:
        if stripped.endswith(prefix):
            return True
    return False


def _extract_local_verses(line: str, chapter: int) -> list[int] | None:
    """Extract all verse numbers for *this* chapter from a line.

    Handles patterns like (13:1), (13:4-5), (13:18,21), (13:10 下-11,26-27).
    Returns a sorted list of individual verse numbers, or None if no match.
    """
    verses: set[int] = set()
    # Match chapter:verse patterns, possibly followed by comma-separated extras
    pattern = re.compile(
        rf"(?<!\d){chapter}\s*:\s*(\d+)"
        r"(?:\s*[下上])?"
        r"(?:\s*[-–]\s*(\d+))?"
        r"((?:\s*[,，]\s*\d+(?:\s*[-–]\s*\d+)?)*)"
    )
    for m in pattern.finditer(line):
        prefix = line[:m.start()]
        if _is_cross_reference(prefix):
            continue
        start_v = int(m.group(1))
        end_v = int(m.group(2)) if m.group(2) else start_v
        for v in range(start_v, end_v + 1):
            verses.add(v)
        # Parse comma-separated trailing verse numbers
        if m.group(3):
            for extra in re.finditer(r"(\d+)(?:\s*[-–]\s*(\d+))?", m.group(3)):
                ev_start = int(extra.group(1))
                ev_end = int(extra.group(2)) if extra.group(2) else ev_start
                for v in range(ev_start, ev_end + 1):
                    verses.add(v)
    return sorted(verses) if verses else None


def build_ccf_index(text: str) -> dict[str, list[str]]:
    """Parse CCF Q&A answer sheets into a verse-keyed index.

    Understands numbered questions (3., 4.), sub-questions ((1), (2)),
    and correctly inherits verse references for sub-questions that don't
    specify their own verse.
    """
    normalized = normalize_text(text)
    chapter = _detect_chapter_from_header(normalized)
    if chapter is None:
        ch_counts: dict[int, int] = {}
        for m in VERSE_RE.finditer(normalized):
            ch = int(m.group(1))
            ch_counts[ch] = ch_counts.get(ch, 0) + 1
        if ch_counts:
            chapter = max(ch_counts, key=ch_counts.get)  # type: ignore[arg-type]
        else:
            return {}

    lines = normalized.splitlines()
    main_q_re = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*")
    sub_q_re = re.compile(r"^\s*[（(]\s*(\d)\s*[）)]\s*")
    day_re = re.compile(r"^\s*第[一二三四五六七八九十]+天\s*[:：]")
    skip_re = re.compile(
        r"^(背誦金句|本查經|此問題特為|CCF International|請勿複印|P\d+$)"
    )

    index: dict[str, list[str]] = {}
    current_verses: list[int] = []
    main_q_verses: list[int] = []  # verse(s) from the main question (for sub-q inheritance)
    current_block: list[str] = []

    def flush_block() -> None:
        nonlocal current_block
        if not current_block or not current_verses:
            current_block = []
            return
        note = " ".join(current_block).strip()
        note = re.sub(r"\s+", " ", note)
        if not note:
            current_block = []
            return
        for v in current_verses:
            index.setdefault(f"{chapter}:{v}", []).append(note)
        current_block = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if day_re.match(stripped):
            flush_block()
            continue
        if skip_re.match(stripped):
            flush_block()
            continue

        main_match = main_q_re.match(stripped)
        sub_match = sub_q_re.match(stripped) if not main_match else None

        is_question_start = bool(main_match or sub_match)

        # Even on non-question lines, check for a verse ref — this handles
        # garbled OCR where the question number is lost but the ref survives.
        line_verses = _extract_local_verses(stripped, chapter)

        if is_question_start:
            flush_block()
            if line_verses:
                current_verses = line_verses
                if main_match:
                    main_q_verses = line_verses
            elif main_match:
                # Main question with no verse ref — reset inheritance
                current_verses = main_q_verses  # keep previous main
            # else: sub-question inherits current_verses
            current_block = [stripped]
        elif line_verses and not current_block:
            # Orphan line with a verse ref (garbled question start)
            flush_block()
            current_verses = line_verses
            main_q_verses = line_verses
            current_block = [stripped]
        else:
            current_block.append(stripped)

    flush_block()
    return dict(sorted(index.items(), key=_sort_key))


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
    if key == "ccf":
        text = extract_pdf_text_for_book(pdf_path, book)
        if _text_looks_garbled(text):
            print("Text extraction garbled, falling back to OCR...", file=sys.stderr)
            text = ocr_pdf_text(pdf_path)
        index = build_ccf_index(text)
    else:
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
