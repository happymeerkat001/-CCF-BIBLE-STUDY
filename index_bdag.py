#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def download_pdf(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "CCF Bible Study BDAG Indexer/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            destination.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} while downloading BDAG PDF: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error while downloading BDAG PDF: {exc}") from exc


def _extract_pages(pdf_path: Path) -> list[str]:
    """Return a list of per-page text strings from the PDF."""
    errors: list[str] = []

    try:
        import fitz  # type: ignore

        with fitz.open(pdf_path) as document:
            return [page.get_text("text") for page in document]
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"PyMuPDF failed: {exc}")

    try:
        import pdfplumber  # type: ignore

        pages: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
        return pages
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"pdfplumber failed: {exc}")

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"pypdf failed: {exc}")

    raise RuntimeError(
        "Could not extract text from the PDF. Install one of: pymupdf, pdfplumber, or pypdf.\n"
        + "\n".join(f"- {error}" for error in errors)
    )


def extract_pdf_text(pdf_path: Path) -> str:
    pages = _extract_pages(pdf_path)
    # Skip front matter / TOC: dictionary entries use ⟦transliteration⟧ markers.
    # Find the first page containing multiple such markers — that's where entries begin.
    start_page = 0
    for i, text in enumerate(pages):
        if text.count("⟦") >= 3:
            start_page = i
            break
    print(f"Skipping {start_page} front-matter pages", file=sys.stderr)
    return "\n".join(pages[start_page:])


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = text.replace("\u00AD", "")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


ENTRY_RE = re.compile(
    r"([\u0370-\u03FF\u1F00-\u1FFF][\u0370-\u03FF\u1F00-\u1FFF\u0300-\u036F ,.’·;/()-]*?)"
    r"\s*⟦([^⟧]+)⟧"
)


def parse_bdag_entries(text: str, snippet_length: int) -> dict[str, str]:
    text = normalize_text(text)
    matches = list(ENTRY_RE.finditer(text))
    entries: dict[str, str] = {}

    for i, match in enumerate(matches):
        raw_lemma = match.group(1).strip(" ,.;:()")
        # Normalize: keep only the first word-form (before comma or space+morphology)
        lemma = re.split(r"[,;]\s*", raw_lemma)[0].strip()
        if len(lemma) < 2:
            continue

        # Body runs from end of ⟦...⟧ to start of next entry
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end]
        body = re.sub(r"\s+", " ", body).strip(" -;:.")

        if body:
            entries.setdefault(lemma, body[:snippet_length].rstrip())

    return entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and index BDAG lemma snippets into JSON.")
    parser.add_argument("--url", help="Agathon Library BDAG PDF URL. Defaults to BDAG_PDF_URL env var.")
    parser.add_argument("--pdf-path", default="data/bdag.pdf", help="Local path for the downloaded PDF.")
    parser.add_argument(
        "--index-path",
        default="data/bdag_index.json",
        help="Output JSON path for the lemma index.",
    )
    parser.add_argument(
        "--snippet-length",
        type=int,
        default=200,
        help="Maximum number of characters to keep per entry snippet.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    url = args.url or os.getenv("BDAG_PDF_URL")
    if not url:
        raise SystemExit("BDAG PDF URL is required via --url or BDAG_PDF_URL.")

    pdf_path = Path(args.pdf_path)
    index_path = Path(args.index_path)

    if not pdf_path.exists():
        download_pdf(url, pdf_path)

    text = extract_pdf_text(pdf_path)
    entries = parse_bdag_entries(text, args.snippet_length)
    if not entries:
        raise SystemExit("No BDAG entries were parsed. Inspect the PDF text extraction and parsing heuristics.")

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(index_path)
    print(f"Indexed {len(entries)} BDAG entries", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
