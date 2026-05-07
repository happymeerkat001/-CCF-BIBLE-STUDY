#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ccf_preview_message import BOOK_ALIASES, CHINESE_BOOK_ALIASES

DEFAULT_BIBLE_API_ENDPOINT = "https://api.scripture.api.bible/v1"
DEFAULT_MACULA_BASE_URL = (
    "https://raw.githubusercontent.com/Clear-Bible/macula-greek/main/"
    "Nestle1904/lowfat"
)
DEFAULT_OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324"
DEFAULT_FALLBACK_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_FREEBIBLECOMMENTARY_BASE_URL = "https://www.freebiblecommentary.org"
DEFAULT_NET_BIBLE_NOTES_URL = "https://labs.bible.org/api/"
DEFAULT_OBSIDIAN_BIBLE_STUDY_DIR = (
    "/Users/leon/Library/Mobile Documents/iCloud~md~obsidian/Documents/"
    "Neural-orchestrator/Bible Study"
)
ALLOWED_MARK_BACKGROUNDS = {"yellow", "salmon", "cyan", "lightgreen"}
ALLOWED_MARK_TEXT = {
    "and",
    "but",
    "now",
    "then",
    "therefore",
    "so",
    "because",
    "that",
    "which",
    "who",
    "where",
    "when",
    "for",
    "if",
    "unless",
    "so that",
    "by which",
}
ALLOWED_PREPOSITION_TEXT = {
    "to",
    "from",
    "in",
    "on",
    "with",
    "for",
    "into",
    "of",
    "at",
    "by",
    "after",
    "before",
    "upon",
    "over",
    "under",
    "through",
    "across",
    "within",
    "without",
    "among",
    "between",
    "around",
    "toward",
    "towards",
    "out of",
}
COMMON_FUNCTION_LEMMAS = {
    "ὁ",
    "καί",
    "δέ",
    "γάρ",
    "οὖν",
    "ἐν",
    "εἰς",
    "ἐκ",
    "ἀπό",
    "πρός",
    "διά",
    "μετά",
    "παρά",
    "ὑπό",
    "περί",
    "ἀντί",
    "ἐπί",
    "σύν",
    "ἀλλά",
    "ἵνα",
    "ὅτι",
    "ὅς",
    "ὅς/ὅ",
    "ἐγώ",
    "σύ",
    "αὐτός",
    "οὐ",
    "μή",
    "εἰμί",
}
COMMON_FUNCTION_SURFACES = ALLOWED_MARK_TEXT | ALLOWED_PREPOSITION_TEXT | {
    "the",
    "a",
    "an",
    "is",
    "was",
    "were",
    "be",
    "been",
    "being",
    "he",
    "she",
    "it",
    "they",
    "him",
    "his",
    "her",
    "their",
    "this",
    "that",
    "these",
    "those",
    "as",
    "or",
    "not",
    "also",
    "all",
}

BOOK_CODE_TO_SLUG = {
    "MAT": "matthew",
    "MRK": "mark",
    "LUK": "luke",
    "JHN": "john",
    "ACT": "acts",
    "ROM": "romans",
    "1CO": "1corinthians",
    "2CO": "2corinthians",
    "GAL": "galatians",
    "EPH": "ephesians",
    "PHP": "philippians",
    "COL": "colossians",
    "1TH": "1thessalonians",
    "2TH": "2thessalonians",
    "1TI": "1timothy",
    "2TI": "2timothy",
    "TIT": "titus",
    "PHM": "philemon",
    "HEB": "hebrews",
    "JAS": "james",
    "1PE": "1peter",
    "2PE": "2peter",
    "1JN": "1john",
    "2JN": "2john",
    "3JN": "3john",
    "JUD": "jude",
    "REV": "revelation",
}

SLUG_TO_CODE = {value: key for key, value in BOOK_CODE_TO_SLUG.items()}
BOOK_FILENAME_ORDER = [
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
BOOK_XML_FILENAMES = {
    slug: f"{index:02d}-{slug}.xml" for index, slug in enumerate(BOOK_FILENAME_ORDER, start=1)
}
BOOK_TO_FBC_SERIES = {
    "matthew": ("VOL01", "VOL01"),
    "mark": ("VOL02", "VOL02"),
    "1peter": ("VOL02", "VOL02B"),
    "2peter": ("VOL02", "VOL02B"),
    "luke": ("VOL03A", "VOL03A"),
    "acts": ("VOL03B", "VOL03B"),
    "john": ("VOL04", "VOL04"),
    "1john": ("VOL04", "VOL04"),
    "2john": ("VOL04", "VOL04"),
    "3john": ("VOL04", "VOL04"),
    "romans": ("VOL05", "VOL05"),
    "1corinthians": ("VOL06", "VOL06"),
    "2corinthians": ("VOL06", "VOL06"),
    "galatians": ("VOL07", "VOL07"),
    "1thessalonians": ("VOL07", "VOL07"),
    "2thessalonians": ("VOL07", "VOL07"),
    "ephesians": ("VOL08", "VOL08"),
    "philippians": ("VOL08", "VOL08"),
    "colossians": ("VOL08", "VOL08"),
    "philemon": ("VOL08", "VOL08"),
    "1timothy": ("VOL09", "VOL09"),
    "2timothy": ("VOL09", "VOL09"),
    "titus": ("VOL09", "VOL09"),
    "hebrews": ("VOL10", "VOL10"),
    "james": ("VOL11", "VOL11"),
    "jude": ("VOL11", "VOL11"),
    "revelation": ("VOL12", "VOL12"),
}
PROMPT_PATH = Path("prompts/diagram_system.md")


class DiagramError(RuntimeError):
    pass


@dataclass
class Reference:
    original: str
    book_slug: str
    book_label: str
    chapter: int
    start_verse: int | None = None
    end_verse: int | None = None

    @property
    def output_stem(self) -> str:
        if self.start_verse is None:
            return f"{self.book_label} {self.chapter}"
        if self.start_verse == self.end_verse:
            return f"{self.book_label} {self.chapter}.{self.start_verse}"
        return f"{self.book_label} {self.chapter}.{self.start_verse}-{self.end_verse}"

    @property
    def verse_range_label(self) -> str:
        if self.start_verse is None:
            return f"{self.book_label} {self.chapter}"
        if self.start_verse == self.end_verse:
            return f"{self.book_label} {self.chapter}:{self.start_verse}"
        return f"{self.book_label} {self.chapter}:{self.start_verse}-{self.end_verse}"


@dataclass
class WordEntry:
    text: str
    ref: str
    lemma: str
    morph: str
    word_class: str
    role: str
    gloss: str
    english: str
    after: str
    depth: int
    groups: list[dict[str, str]] = field(default_factory=list)


@dataclass
class CommentaryNote:
    heading: str
    body_parts: list[str] = field(default_factory=list)

    def render(self) -> str:
        heading = _normalize_commentary_text(self.heading)
        body = " ".join(_normalize_commentary_text(part) for part in self.body_parts if part.strip())
        return f"{heading} {body}".strip() if body else heading


@dataclass
class CommentarySource:
    key: str
    label: str
    emoji: str
    notes: dict[int, list[str]]


@dataclass
class BoldWord:
    verse: int
    surface: str
    lemma: str
    gloss: str


COMMENTARY_SOURCE_METADATA = {
    "fbc": {"label": "FreeBibleCommentary — Utley", "emoji": "📖"},
    "net": {"label": "NET Bible Notes", "emoji": "📗"},
    "keener": {"label": "IVP Bible Background — Keener", "emoji": "🌍"},
}


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def parse_reference(reference: str) -> Reference:
    compact = re.sub(r"\s+", " ", reference.strip())
    if not compact:
        raise DiagramError("Reference is required.")

    normalized = compact.replace("：", ":")
    match = re.match(
        r"^(?P<book>.+?)\s*(?P<chapter>\d+)(?::(?P<start>\d+)(?:-(?P<end>\d+))?)?$",
        normalized,
    )
    if not match:
        raise DiagramError(f"Unsupported reference format: {reference}")

    book_text = re.sub(r"\s+", "", match.group("book")).lower()
    book_slug = BOOK_ALIASES.get(book_text) or CHINESE_BOOK_ALIASES.get(match.group("book"))
    if not book_slug:
        book_slug = BOOK_ALIASES.get(match.group("book").strip().lower())
    if not book_slug:
        raise DiagramError(f"Unknown book name: {match.group('book')}")

    chapter = int(match.group("chapter"))
    start_verse = int(match.group("start")) if match.group("start") else None
    end_verse = int(match.group("end")) if match.group("end") else start_verse

    english_label = next(
        (
            alias.title()
            for alias, chinese_name in BOOK_ALIASES.items()
            if chinese_name == book_slug and alias.isalpha() and len(alias) > 2
        ),
        book_slug,
    )
    return Reference(
        original=reference,
        book_slug=_canonical_slug(book_slug),
        book_label=english_label,
        chapter=chapter,
        start_verse=start_verse,
        end_verse=end_verse,
    )


def _canonical_slug(book_name: str) -> str:
    for slug in SLUG_TO_CODE:
        chinese_name = BOOK_ALIASES.get(slug, "")
        if chinese_name == book_name:
            return slug
    mapping = {
        chinese_value: alias
        for alias, chinese_value in BOOK_ALIASES.items()
        if alias in SLUG_TO_CODE
    }
    return mapping.get(book_name, book_name)


def http_get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DiagramError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise DiagramError(f"Network error for {url}: {exc}") from exc


def http_get_text(url: str, headers: dict[str, str] | None = None) -> str:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DiagramError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise DiagramError(f"Network error for {url}: {exc}") from exc


def build_fbc_url(reference: Reference) -> str:
    series = BOOK_TO_FBC_SERIES.get(reference.book_slug)
    if not series:
        raise DiagramError(
            f"FreeBibleCommentary mapping is not available for {reference.book_slug}."
        )
    directory_code, file_code = series
    chapter_label = f"{reference.chapter:02d}"
    return (
        f"{DEFAULT_FREEBIBLECOMMENTARY_BASE_URL}/new_testament_studies/"
        f"{directory_code}/{file_code}_{chapter_label}.html"
    )


def fetch_commentary(reference: Reference) -> dict[int, list[str]]:
    url = build_fbc_url(reference)
    html_text = http_get_text(
        url,
        headers={"User-Agent": "CCF Bible Study Diagram Generator/1.0"},
    )
    lines = extract_fbc_text_lines(html_text, url)
    return parse_fbc_commentary_lines(reference, lines)


def fetch_fbc_commentary_source(reference: Reference) -> CommentarySource:
    meta = COMMENTARY_SOURCE_METADATA["fbc"]
    return CommentarySource(
        key="fbc",
        label=meta["label"],
        emoji=meta["emoji"],
        notes=fetch_commentary(reference),
    )


def extract_fbc_text_lines(raw_html: str, base_url: str) -> list[str]:
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", "\n", raw_html)

    def replace_anchor(match: re.Match[str]) -> str:
        href = match.group(1)
        label = re.sub(r"(?is)<[^>]+>", "", match.group(2))
        absolute = urllib.parse.urljoin(base_url, html.unescape(href))
        return f"[{html.unescape(label).strip()}]({absolute})"

    text = re.sub(
        r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        replace_anchor,
        text,
    )
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</?(?:p|div|tr|td|th|table|section|article|blockquote|ul|ol|li|h[1-6]|hr)\b[^>]*>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


def parse_fbc_commentary_lines(reference: Reference, lines: list[str]) -> dict[int, list[str]]:
    section_re = re.compile(
        rf"^NASB \(UPDATED\) TEXT:\s+.*?\b{reference.chapter}:(\d+)(?:-(\d+))?$",
        re.IGNORECASE,
    )
    verse_re = re.compile(
        rf"^{reference.chapter}:(\d+)(?:-(\d+))?\s+(.*)$",
        re.IGNORECASE,
    )
    commentary: dict[int, list[str]] = {}
    in_word_study = False
    current_targets: list[int] = []
    current_note: CommentaryNote | None = None

    def store_note() -> None:
        nonlocal current_note
        if not current_note or not current_targets:
            current_note = None
            return
        rendered = current_note.render()
        if rendered:
            for verse in current_targets:
                commentary.setdefault(verse, []).append(rendered)
        current_note = None

    for line in lines:
        normalized = _normalize_commentary_text(line)
        if not normalized:
            continue
        if normalized == "WORD AND PHRASE STUDY":
            in_word_study = True
            continue
        if not in_word_study:
            continue
        if normalized.startswith("DISCUSSION QUESTIONS"):
            break

        section_match = section_re.match(normalized)
        if section_match:
            store_note()
            start_verse = int(section_match.group(1))
            current_targets = [start_verse] if _verse_in_scope(reference, start_verse) else []
            continue

        verse_match = verse_re.match(normalized)
        if verse_match:
            store_note()
            start_verse = int(verse_match.group(1))
            end_verse = int(verse_match.group(2) or start_verse)
            current_targets = [start_verse] if _verse_in_scope(reference, start_verse) else []
            heading = f"{reference.chapter}:{start_verse}"
            if end_verse > start_verse:
                heading = f"{reference.chapter}:{start_verse}-{end_verse}"
            current_note = CommentaryNote(heading=heading, body_parts=[verse_match.group(3)])
            continue

        if normalized.startswith("▣"):
            store_note()
            current_note = CommentaryNote(heading=normalized[1:].strip())
            continue

        if "SPECIAL TOPIC:" in normalized:
            if current_note is None:
                current_note = CommentaryNote(heading=normalized)
            else:
                current_note.body_parts.append(normalized)
            continue

        if normalized.startswith("NASB (UPDATED) TEXT:"):
            store_note()
            current_targets = []
            current_note = None
            continue

        if current_note is not None:
            current_note.body_parts.append(normalized)

    store_note()
    return commentary


def _normalize_commentary_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.replace("\u2003", " ")).strip()
    cleaned = re.sub(r"\[\s+", "[", cleaned)
    cleaned = re.sub(r"\s+\]", "]", cleaned)
    return cleaned


def _verse_in_scope(reference: Reference, verse_num: int) -> bool:
    if reference.start_verse is None:
        return True
    end_verse = reference.end_verse or reference.start_verse
    return reference.start_verse <= verse_num <= end_verse


def parse_requested_commentary_sources(raw: str) -> list[str]:
    if not raw:
        return ["fbc"]
    requested = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not requested:
        return ["fbc"]
    if "all" in requested:
        return list(COMMENTARY_SOURCE_METADATA)
    invalid = [item for item in requested if item not in COMMENTARY_SOURCE_METADATA]
    if invalid:
        raise DiagramError(
            "Unknown commentary source(s): "
            + ", ".join(sorted(invalid))
            + ". Use fbc, net, keener, or all."
        )
    seen: set[str] = set()
    ordered: list[str] = []
    for item in requested:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def fetch_net_bible_notes(reference: Reference) -> CommentarySource:
    params = {
        "passage": reference.verse_range_label,
        "type": "json",
        "formatting": "full",
        "notes": "1",
        "footnotes": "1",
    }
    url = f"{DEFAULT_NET_BIBLE_NOTES_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CCF Bible Study Diagram Generator/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DiagramError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise DiagramError(f"Network error for {url}: {exc}") from exc

    notes: dict[int, list[str]] = {}
    for item in payload:
        verse_num = int(item.get("verse", 0) or 0)
        if not verse_num or not _verse_in_scope(reference, verse_num):
            continue
        rendered = _extract_net_notes_from_payload(item)
        if rendered:
            notes[verse_num] = rendered

    meta = COMMENTARY_SOURCE_METADATA["net"]
    return CommentarySource(
        key="net",
        label=meta["label"],
        emoji=meta["emoji"],
        notes=notes,
    )


def _extract_net_notes_from_payload(item: dict[str, Any]) -> list[str]:
    structured_notes = item.get("notes")
    if isinstance(structured_notes, list):
        rendered = [_normalize_commentary_text(_flatten_note_value(note)) for note in structured_notes]
        return [note for note in rendered if note]

    structured_footnotes = item.get("footnotes")
    if isinstance(structured_footnotes, list):
        rendered = [
            _normalize_commentary_text(_flatten_note_value(note))
            for note in structured_footnotes
        ]
        return [note for note in rendered if note]

    text = html.unescape(str(item.get("text", "")))
    note_blocks = re.findall(r"(?is)<(?:note|sn|tn|tc)\b[^>]*>(.*?)</(?:note|sn|tn|tc)>", text)
    cleaned_blocks = [_normalize_net_note_html(block) for block in note_blocks]
    cleaned_blocks = [block for block in cleaned_blocks if block]
    if cleaned_blocks:
        return cleaned_blocks

    marker_matches = list(re.finditer(r'<n\s+id="([^"]+)"\s*/?>', text))
    if not marker_matches:
        return []

    plain_text = _normalize_net_note_html(text)
    snippets: list[str] = []
    for index, match in enumerate(marker_matches, start=1):
        note_id = match.group(1) or str(index)
        prefix = _normalize_net_note_html(text[: match.start()])
        suffix = _normalize_net_note_html(text[match.end() :])
        context_bits = [part for part in (prefix[-80:].strip(), suffix[:80].strip()) if part]
        context = " ... ".join(context_bits).strip()
        if context:
            snippets.append(f"Note {note_id} attached to: {context}")
        elif plain_text:
            snippets.append(f"Note {note_id} attached to: {plain_text[:120]}")
    return snippets


def _flatten_note_value(value: Any) -> str:
    if isinstance(value, str):
        return _normalize_net_note_html(value)
    if isinstance(value, dict):
        pieces = []
        for key in ("text", "body", "note", "content", "value", "type"):
            if value.get(key):
                pieces.append(_flatten_note_value(value[key]))
        return " ".join(piece for piece in pieces if piece)
    if isinstance(value, list):
        return " ".join(_flatten_note_value(item) for item in value)
    return str(value)


def _normalize_net_note_html(text: str) -> str:
    text = re.sub(r"(?is)<st\b[^>]*>(.*?)</st>", r"\1", text)
    text = re.sub(r"(?is)<n\b[^>]*/?>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return _normalize_commentary_text(html.unescape(text))


def load_pdf_commentary(reference: Reference, key: str, cache_dir: Path) -> CommentarySource:
    if key not in COMMENTARY_SOURCE_METADATA:
        raise DiagramError(f"Unknown commentary source: {key}")
    index_path = cache_dir / f"{key}_{reference.book_slug}.json"
    if not index_path.exists():
        raise DiagramError(
            f"Missing commentary index for {key}: {index_path}. "
            "Run: python3 index_commentary_pdf.py "
            f"--pdf /path/to/{key}.pdf --book {reference.book_slug} --key {key}"
        )
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    notes: dict[int, list[str]] = {}
    for verse_key, entries in payload.items():
        match = re.fullmatch(r"(\d+):(\d+)", verse_key.strip())
        if not match:
            continue
        chapter_num = int(match.group(1))
        verse_num = int(match.group(2))
        if chapter_num != reference.chapter or not _verse_in_scope(reference, verse_num):
            continue
        if isinstance(entries, str):
            rendered = [_normalize_commentary_text(entries)]
        else:
            rendered = [_normalize_commentary_text(str(entry)) for entry in entries]
        rendered = [entry for entry in rendered if entry]
        if rendered:
            notes[verse_num] = rendered
    meta = COMMENTARY_SOURCE_METADATA[key]
    return CommentarySource(key=key, label=meta["label"], emoji=meta["emoji"], notes=notes)


def load_bdag_index(cache_dir: Path) -> dict[str, str]:
    index_path = cache_dir / "bdag_index.json"
    if not index_path.exists():
        raise DiagramError(f"Missing BDAG index: {index_path}. Run index_bdag.py first.")
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    return {
        _normalize_lemma_lookup(str(lemma)): str(definition).strip()
        for lemma, definition in payload.items()
        if str(lemma).strip() and str(definition).strip()
    }


def identify_bold_words(
    verse_words: dict[int, list[WordEntry]],
    bdag_index: dict[str, str],
) -> dict[int, list[BoldWord]]:
    bold_map: dict[int, list[BoldWord]] = {}
    for verse_num, words in verse_words.items():
        seen: set[tuple[str, str]] = set()
        for word in words:
            lemma = _normalize_lemma_lookup(word.lemma)
            if not lemma or lemma not in bdag_index:
                continue
            if _is_common_function_word(word, lemma):
                continue
            surface = _choose_bold_surface(word)
            if not surface:
                continue
            normalized_surface = normalize_marker_text(surface)
            if not normalized_surface or normalized_surface in COMMON_FUNCTION_SURFACES:
                continue
            key = (normalized_surface, lemma)
            if key in seen:
                continue
            seen.add(key)
            bold_map.setdefault(verse_num, []).append(
                BoldWord(
                    verse=verse_num,
                    surface=surface,
                    lemma=lemma,
                    gloss=_trim_definition_snippet(bdag_index[lemma]),
                )
            )
    return bold_map


def _normalize_lemma_lookup(lemma: str) -> str:
    cleaned = html.unescape(lemma or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"/\d+$", "", cleaned)
    cleaned = re.sub(r"[0-9]+$", "", cleaned)
    return cleaned


def _is_common_function_word(word: WordEntry, lemma: str) -> bool:
    if lemma in COMMON_FUNCTION_LEMMAS:
        return True
    if word.word_class.lower() in {"det", "article", "prep", "conj", "ptcl", "pron"}:
        return True
    english = normalize_marker_text(word.english or word.gloss or "")
    return english in COMMON_FUNCTION_SURFACES


def _choose_bold_surface(word: WordEntry) -> str:
    candidates = [word.english, word.gloss, word.text]
    for candidate in candidates:
        text = _normalize_candidate_surface(candidate)
        if text:
            return text
    return ""


def _normalize_candidate_surface(value: str) -> str:
    text = html.unescape((value or "").strip())
    if not text:
        return ""
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.split(r"[;/]", text, maxsplit=1)[0]
    text = re.sub(r"\s+", " ", text).strip(" ,.;:!?()[]{}\"'“”‘’")
    return text


def _trim_definition_snippet(definition: str, limit: int = 200) -> str:
    cleaned = re.sub(r"\s+", " ", definition).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def apply_bold_words(body: str, bold_words: dict[int, list[BoldWord]]) -> str:
    if not bold_words:
        return body

    lines = body.splitlines()
    output: list[str] = []
    verse_buffer: list[str] = []
    current_verse: int | None = None

    def flush() -> None:
        if not verse_buffer:
            return
        verse_text = "\n".join(verse_buffer)
        if current_verse is not None and bold_words.get(current_verse):
            verse_text = _apply_bold_words_to_verse_block(verse_text, bold_words[current_verse])
        output.append(verse_text)
        verse_buffer.clear()

    for line in lines:
        verse_match = re.match(r"^\s*<strong>(\d+)</strong>", line)
        if verse_match:
            flush()
            current_verse = int(verse_match.group(1))
        verse_buffer.append(line)

    flush()
    return "\n".join(output).strip()


def _apply_bold_words_to_verse_block(block: str, bold_words: list[BoldWord]) -> str:
    updated = block
    for bold_word in sorted(bold_words, key=lambda item: (-len(item.surface), item.surface.lower())):
        updated = _wrap_surface_in_bold(updated, bold_word.surface)
    return updated


def _wrap_surface_in_bold(block: str, surface: str) -> str:
    if not surface:
        return block
    phrase_pattern = _build_surface_pattern(surface)
    if not phrase_pattern:
        return block

    for tag in ("u", "mark", "span", "em", "i"):
        tag_pattern = re.compile(
            rf"(?<!<b>)(<{tag}\b[^>]*>\s*{phrase_pattern}\s*</{tag}>)",
            re.IGNORECASE,
        )
        wrapped, count = tag_pattern.subn(r"<b>\1</b>", block, count=1)
        if count:
            return wrapped

    plain_pattern = re.compile(
        rf"(?<![A-Za-z])({phrase_pattern})(?![A-Za-z])",
        re.IGNORECASE,
    )
    wrapped, count = plain_pattern.subn(r"<b>\1</b>", block, count=1)
    return wrapped if count else block


def _build_surface_pattern(surface: str) -> str:
    parts = [part for part in re.split(r"\s+", surface.strip()) if part]
    if not parts:
        return ""
    return r"(?:\s|\u00A0|&nbsp;)+".join(re.escape(part) for part in parts)


def add_commentary_footnotes(
    body: str,
    reference: Reference,
    sources: list[CommentarySource],
    style: str,
    bold_words: dict[int, list[BoldWord]] | None = None,
) -> str:
    if not sources and not bold_words:
        return body

    bold_words = bold_words or {}

    lines = body.splitlines()
    output: list[str] = []
    verse_buffer: list[str] = []
    current_verse: int | None = None

    def flush() -> None:
        if not verse_buffer:
            return
        output.extend(verse_buffer)
        if current_verse is not None:
            verse_notes = [
                CommentarySource(
                    key=source.key,
                    label=source.label,
                    emoji=source.emoji,
                    notes={current_verse: source.notes.get(current_verse, [])},
                )
                for source in sources
                if source.notes.get(current_verse)
            ]
            if verse_notes:
                output.extend(
                    [
                        "",
                        format_verse_commentary(
                            reference,
                            current_verse,
                            verse_notes,
                            style,
                            bold_words.get(current_verse, []),
                        ),
                        "",
                    ]
                )
        verse_buffer.clear()

    for line in lines:
        verse_match = re.match(r"^\s*<strong>(\d+)</strong>", line)
        if verse_match:
            flush()
            current_verse = int(verse_match.group(1))
        verse_buffer.append(line)

    flush()
    return "\n".join(output).strip()


def format_commentary_notes(
    source: CommentarySource,
    verse_num: int,
    style: str,
) -> str:
    notes = source.notes.get(verse_num, [])
    count = len(notes)
    summary = f"{source.emoji} {source.label} ({count} note{'s' if count != 1 else ''})"
    bullet_lines = [f"- {note}" for note in notes]
    if style == "inline":
        return "\n".join([f"**{summary}**", *bullet_lines])
    return "\n".join(["<details>", f"<summary>{summary}</summary>", "", *bullet_lines, "</details>"])


def format_lexicon_block(bold_words: list[BoldWord], style: str) -> str:
    if not bold_words:
        return ""

    count = len(bold_words)
    summary = f"📘 Lexicon — BDAG ({count} entr{'y' if count == 1 else 'ies'})"
    bullet_lines = [
        f"- **{word.surface}** ({word.lemma}) — {word.gloss}"
        for word in bold_words
    ]
    if style == "inline":
        return "\n".join([f"**{summary}**", *bullet_lines])
    return "\n".join(["<details>", f"<summary>{summary}</summary>", "", *bullet_lines, "</details>"])


def format_verse_commentary(
    reference: Reference,
    verse_num: int,
    sources: list[CommentarySource],
    style: str,
    bold_words: list[BoldWord] | None = None,
) -> str:
    header = f"Commentary — {reference.book_label} {reference.chapter}:{verse_num}"
    lexicon_block = format_lexicon_block(bold_words or [], style)
    if style == "inline":
        parts = [f"**{header}**"]
        for source in sources:
            rendered = format_commentary_notes(source, verse_num, style)
            if rendered:
                parts.extend(["", rendered])
        if lexicon_block:
            parts.extend(["", lexicon_block])
        return "\n".join(parts)

    inner_blocks = [format_commentary_notes(source, verse_num, style) for source in sources]
    inner_blocks = [block for block in inner_blocks if block]
    if lexicon_block:
        inner_blocks.append(lexicon_block)
    return "\n".join(
        [
            "<details>",
            f"<summary><strong>{header}</strong></summary>",
            "",
            *inner_blocks,
            "</details>",
        ]
    )


def ensure_macula_xml(reference: Reference, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    xml_filename = BOOK_XML_FILENAMES.get(reference.book_slug, f"{reference.book_slug}.xml")
    xml_path = cache_dir / xml_filename
    if xml_path.exists():
        return xml_path
    url = f"{os.getenv('MACULA_BASE_URL', DEFAULT_MACULA_BASE_URL)}/{xml_filename}"
    xml_path.write_text(http_get_text(url), encoding="utf-8")
    return xml_path


def extract_macula_words(xml_path: Path, reference: Reference) -> dict[int, list[WordEntry]]:
    book_code = SLUG_TO_CODE.get(reference.book_slug)
    if not book_code:
        raise DiagramError(f"No MACULA book code mapping for {reference.book_slug}")

    tree = ET.parse(xml_path)
    verse_map: dict[int, list[WordEntry]] = {}

    def visit(element: ET.Element, depth: int, groups: list[dict[str, str]]) -> None:
        tag = _strip_ns(element.tag)
        if tag == "wg":
            group_attrs = {
                key: value
                for key, value in element.attrib.items()
                if key in {"class", "role", "rule", "type"}
            }
            for child in element:
                visit(child, depth + 1, groups + [group_attrs])
            return

        if tag != "w":
            for child in element:
                visit(child, depth, groups)
            return

        ref_value = element.attrib.get("ref", "")
        ref_match = re.search(rf"{book_code}\s+{reference.chapter}:(\d+)", ref_value)
        if not ref_match:
            return

        verse_num = int(ref_match.group(1))
        if reference.start_verse is not None:
            if verse_num < reference.start_verse or verse_num > (reference.end_verse or verse_num):
                return

        entry = WordEntry(
            text=(element.text or "").strip(),
            ref=ref_value,
            lemma=element.attrib.get("lemma", ""),
            morph=element.attrib.get("morph", ""),
            word_class=element.attrib.get("class", ""),
            role=element.attrib.get("role", ""),
            gloss=element.attrib.get("gloss", ""),
            english=element.attrib.get("English", "") or element.attrib.get("english", ""),
            after=element.attrib.get("after", " "),
            depth=depth,
            groups=groups,
        )
        verse_map.setdefault(verse_num, []).append(entry)

    visit(tree.getroot(), 0, [])
    if not verse_map:
        raise DiagramError(f"No MACULA data found for {reference.verse_range_label}")
    return dict(sorted(verse_map.items()))


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def resolve_bible_id(api_key: str, endpoint: str) -> str:
    explicit = os.getenv("BIBLE_ID")
    if explicit:
        return explicit

    payload = http_get_json(
        f"{endpoint}/bibles",
        headers={"api-key": api_key, "accept": "application/json"},
    )
    for bible in payload.get("data", []):
        label = " ".join(
            str(bible.get(field, ""))
            for field in ("abbreviation", "abbreviationLocal", "name", "nameLocal")
        ).upper()
        if "NASB" in label:
            return str(bible["id"])
    raise DiagramError("Could not auto-detect a NASB Bible ID. Set BIBLE_ID in .env.")


def fetch_bible_text(reference: Reference) -> dict[int, str]:
    api_key = os.getenv("BIBLE_API_KEY")
    if not api_key:
        raise DiagramError("BIBLE_API_KEY is required in .env or the environment.")

    endpoint = os.getenv("BIBLE_API_ENDPOINT", DEFAULT_BIBLE_API_ENDPOINT).rstrip("/")
    bible_id = resolve_bible_id(api_key, endpoint)
    book_code = SLUG_TO_CODE.get(reference.book_slug, reference.book_slug)
    if reference.start_verse is not None:
        if reference.end_verse is not None and reference.end_verse != reference.start_verse:
            passage_id = f"{book_code}.{reference.chapter}.{reference.start_verse}-{book_code}.{reference.chapter}.{reference.end_verse}"
        else:
            passage_id = f"{book_code}.{reference.chapter}.{reference.start_verse}"
    else:
        passage_id = f"{book_code}.{reference.chapter}"
    url = (
        f"{endpoint}/bibles/{bible_id}/passages/{passage_id}"
        "?content-type=text&include-notes=false&include-titles=false&include-chapter-numbers=false"
        "&include-verse-numbers=true&include-verse-spans=false"
    )
    payload = http_get_json(
        url,
        headers={"api-key": api_key, "accept": "application/json"},
    )
    content = str(payload.get("data", {}).get("content", "")).strip()
    verses = split_bible_text(reference, content)
    if not verses:
        raise DiagramError("API.Bible returned empty passage content.")
    return verses


def build_gloss_fallback(verse_words: dict[int, list[WordEntry]]) -> dict[int, str]:
    verses: dict[int, str] = {}
    for verse_num, words in verse_words.items():
        tokens = []
        for word in words:
            english = (word.english or word.gloss or word.text).strip()
            if not english:
                continue
            after = word.after if word.after.strip() else " "
            tokens.append(english + after)
        verses[verse_num] = re.sub(r"\s+", " ", "".join(tokens)).strip()
    return verses


def split_bible_text(reference: Reference, content: str) -> dict[int, str]:
    # Strip section headings that appear before verse markers
    content = re.sub(r"^[A-Z][^\[]*?(?=\[?\d+\]?\s)", "", content.strip())
    cleaned = re.sub(r"\s+", " ", content).strip()
    if reference.start_verse is not None and reference.end_verse is not None:
        verse_numbers = range(reference.start_verse, reference.end_verse + 1)
    else:
        verse_numbers = range(1, 177)

    matches = list(re.finditer(r"\[?(\d+)\]?\s", cleaned))
    verse_text: dict[int, str] = {}
    for index, match in enumerate(matches):
        verse_num = int(match.group(1))
        if verse_num not in verse_numbers:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        verse_text[verse_num] = cleaned[start:end].strip()

    if verse_text:
        return verse_text

    if reference.start_verse is not None and reference.start_verse == reference.end_verse:
        return {reference.start_verse: cleaned}
    return {}


def sanitize_english_text(verses: dict[int, str]) -> dict[int, str]:
    cleaned: dict[int, str] = {}
    for verse_num, text in verses.items():
        normalized = text.replace("*", "").replace("_", "")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        cleaned[verse_num] = normalized
    return cleaned


def simplify_macula(reference: Reference, verse_words: dict[int, list[WordEntry]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for verse_num, words in verse_words.items():
        payload.append(
            {
                "verse": verse_num,
                "greek_surface": "".join(word.text + (word.after or "") for word in words).strip(),
                "words": [
                    {
                        "text": word.text,
                        "gloss": word.gloss,
                        "lemma": word.lemma,
                        "morph": word.morph,
                        "class": word.word_class,
                        "role": word.role,
                        "english": word.english,
                        "depth": word.depth,
                    }
                    for word in words
                ],
            }
        )
    return payload


def load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise DiagramError(f"Missing prompt file: {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_user_prompt(
    reference: Reference,
    verse_words: dict[int, list[WordEntry]],
    english_text: dict[int, str],
) -> str:
    syntax_payload = simplify_macula(reference, verse_words)
    english_payload = [
        {"verse": verse_num, "text": english_text.get(verse_num, "")}
        for verse_num in verse_words
    ]
    return (
        f"Reference: {reference.verse_range_label}\n\n"
        "English verses:\n"
        f"{json.dumps(english_payload, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "Greek syntax payload:\n"
        f"{json.dumps(syntax_payload, ensure_ascii=False, separators=(',', ':'))}\n"
    )


def call_openrouter_messages(messages: list[dict[str, str]], model: str) -> tuple[str, dict[str, Any]]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise DiagramError("OPENROUTER_API_KEY is required in .env or the environment.")

    payload = {
        "model": model,
        "messages": messages,
    }
    request = urllib.request.Request(
        os.getenv("OPENROUTER_API_ENDPOINT", DEFAULT_OPENROUTER_ENDPOINT),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.ccf-bible-study",
            "X-Title": "CCF Bible Study Diagram Generator",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise DiagramError(f"OpenRouter request failed: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise DiagramError(f"OpenRouter network error: {exc}") from exc

    choices = raw.get("choices") or []
    if not choices:
        raise DiagramError(f"OpenRouter returned no choices: {raw}")
    content = choices[0].get("message", {}).get("content", "").strip()
    if not content:
        raise DiagramError(f"OpenRouter returned empty content: {raw}")
    usage = raw.get("usage", {})
    return content, usage


def call_openrouter(prompt: str, model: str) -> tuple[str, dict[str, Any]]:
    system_prompt = load_system_prompt()
    return call_openrouter_messages(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        model,
    )


def normalize_marker_text(text: str) -> str:
    normalized = text.strip().strip("\"'“”‘’.,;:!?()[]{}")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.lower()


def validate_diagram_body(body: str) -> list[str]:
    errors: list[str] = []
    stripped = body.lstrip()
    if not stripped.startswith("<strong>1</strong>"):
        errors.append("Output must begin directly with the first verse number and contain no explanatory preamble.")
    if re.search(r"<mark(?![^>]*background:)", body):
        errors.append("Every <mark> tag must include an explicit allowed background.")
    if "background: red" in body:
        errors.append("Do not use background: red.")
    if '<mark style="color: red;">' in body:
        errors.append("Do not use <mark style=\"color: red;\">; use a red <span> for prepositions.")

    mark_pattern = re.compile(r'<mark\s+style="([^"]*)">(.*?)</mark>', re.DOTALL)
    for style, content in mark_pattern.findall(body):
        background_match = re.search(r"background:\s*([^;]+)", style)
        if not background_match:
            errors.append(f"Invalid <mark> style without background: {style}")
            continue
        background = background_match.group(1).strip()
        if background not in ALLOWED_MARK_BACKGROUNDS:
            errors.append(f"Invalid <mark> background: {background}")
        marker_text = normalize_marker_text(re.sub(r"<[^>]+>", "", content))
        if marker_text and marker_text not in ALLOWED_MARK_TEXT:
            errors.append(f"Invalid highlighted marker text: {marker_text}")

    span_pattern = re.compile(r'<span\s+style="color: red;">(.*?)</span>', re.DOTALL)
    for content in span_pattern.findall(body):
        preposition_text = normalize_marker_text(re.sub(r"<[^>]+>", "", content))
        if preposition_text and preposition_text not in ALLOWED_PREPOSITION_TEXT:
            errors.append(f"Invalid red preposition text: {preposition_text}")

    if re.search(r'<u>([^<]*\bto\b[^<]*)</u>', body):
        errors.append("Infinitive phrases with 'to + verb' must use wavy underline, not single underline.")
    if re.search(r'\bto\s+<u>([^<]+)</u>', body):
        errors.append("Do not split English infinitives across plain text and single underline; use one wavy underline span.")

    seen: set[str] = set()
    unique_errors: list[str] = []
    for error in errors:
        if error not in seen:
            seen.add(error)
            unique_errors.append(error)
    return unique_errors


def autofix_diagram_body(body: str) -> str:
    """Fix common mechanical validation issues without an LLM round-trip."""
    # Strip preamble before first verse number
    match = re.search(r"<strong>\d+</strong>", body)
    if match and match.start() > 0:
        body = body[match.start():]

    # Fix bare <mark> tags (no style) → default to yellow background
    body = re.sub(r"<mark>", '<mark style="background: yellow;">', body)

    # Fix <mark style="color: red;"> → convert to <span>
    body = re.sub(
        r'<mark\s+style="color:\s*red;">(.*?)</mark>',
        r'<span style="color: red;">\1</span>',
        body,
        flags=re.DOTALL,
    )

    # Fix background: red → background: salmon
    body = body.replace("background: red", "background: salmon")

    # Fix disallowed background colors → salmon fallback
    def _fix_mark_bg(m: re.Match[str]) -> str:
        style = m.group(1)
        bg_match = re.search(r"background:\s*([^;\"]+)", style)
        if bg_match:
            bg = bg_match.group(1).strip()
            if bg not in ALLOWED_MARK_BACKGROUNDS:
                style = style.replace(f"background: {bg}", "background: salmon")
        return f'<mark style="{style}">'
    body = re.sub(r'<mark\s+style="([^"]*)">', _fix_mark_bg, body)

    # Strip trailing markdown code fences the LLM sometimes wraps output in
    body = re.sub(r"^```[a-z]*\s*\n?", "", body)
    body = re.sub(r"\n?```\s*$", "", body)

    return body


def build_repair_prompt(original_prompt: str, draft_body: str, errors: list[str]) -> str:
    repair_lines = "\n".join(f"- {error}" for error in errors)
    return (
        "Revise the following draft diagram so it fully obeys the formatting rules.\n"
        "Keep the same verse order and the same English verse text.\n"
        "Return only corrected HTML-in-Markdown body content with no explanation.\n\n"
        "Validation errors to fix:\n"
        f"{repair_lines}\n\n"
        "Original source data:\n"
        f"{original_prompt}\n"
        "Draft output to repair:\n"
        f"{draft_body}\n"
    )


def generate_validated_diagram(prompt: str, model: str, max_attempts: int = 3) -> tuple[str, dict[str, Any]]:
    body, usage = call_openrouter(prompt, model)
    body = autofix_diagram_body(body)
    errors = validate_diagram_body(body)
    if not errors:
        return body, usage

    total_usage = dict(usage)
    for _ in range(max_attempts - 1):
        repair_prompt = build_repair_prompt(prompt, body, errors)
        body, repair_usage = call_openrouter(repair_prompt, model)
        body = autofix_diagram_body(body)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            total_usage[key] = total_usage.get(key, 0) + repair_usage.get(key, 0)
        errors = validate_diagram_body(body)
        if not errors:
            return body, total_usage

    fallback_model = os.getenv("DIAGRAM_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL).strip()
    if fallback_model and fallback_model != model:
        print(
            f"Warning: {model} failed diagram validation; retrying with fallback model {fallback_model}.",
            file=sys.stderr,
        )
        body, fallback_usage = call_openrouter(prompt, fallback_model)
        body = autofix_diagram_body(body)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            total_usage[key] = total_usage.get(key, 0) + fallback_usage.get(key, 0)
        errors = validate_diagram_body(body)
        if not errors:
            return body, total_usage

        for _ in range(max_attempts - 1):
            repair_prompt = build_repair_prompt(prompt, body, errors)
            body, repair_usage = call_openrouter(repair_prompt, fallback_model)
            body = autofix_diagram_body(body)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                total_usage[key] = total_usage.get(key, 0) + repair_usage.get(key, 0)
            errors = validate_diagram_body(body)
            if not errors:
                return body, total_usage

    raise DiagramError("Model output failed validation after repair attempts:\n- " + "\n- ".join(errors))


def write_output(reference: Reference, body: str, usage: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{reference.output_stem}.md"
    usage_lines = []
    if usage:
        usage_lines.extend(
            [
                f"- prompt_tokens: {usage.get('prompt_tokens', 'n/a')}",
                f"- completion_tokens: {usage.get('completion_tokens', 'n/a')}",
                f"- total_tokens: {usage.get('total_tokens', 'n/a')}",
            ]
        )

    output = [
        "---",
        "cssclasses:",
        "  - ccf-diagram",
        "---",
        "",
        f"# {reference.verse_range_label}",
        "",
        body.strip(),
    ]
    if usage_lines:
        output.extend(["", "## OpenRouter Usage", ""])
        output.extend(usage_lines)
    output_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    return output_path


def resolve_publish_dir(args: argparse.Namespace) -> Path | None:
    if args.no_publish:
        return None
    raw_publish_dir = args.publish_dir or os.getenv(
        "OBSIDIAN_BIBLE_STUDY_DIR",
        DEFAULT_OBSIDIAN_BIBLE_STUDY_DIR,
    )
    expanded = os.path.expandvars(os.path.expanduser(raw_publish_dir))
    return Path(expanded)


def publish_output(src: Path, publish_dir: Path, mode: str) -> Path:
    publish_dir.mkdir(parents=True, exist_ok=True)
    destination = publish_dir / src.name
    fd, temp_name = tempfile.mkstemp(prefix=f".{src.stem}.", suffix=src.suffix, dir=publish_dir)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        shutil.copy2(src, temp_path)
        os.replace(temp_path, destination)
        if mode == "move":
            src.unlink()
        return destination
    except Exception:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass
        raise


DIAGRAM_CACHE_DIR = Path("data/diagram_cache")


def _cache_key(reference: Reference, model: str) -> Path:
    slug = f"{reference.book_slug}_{reference.chapter}"
    v_start = reference.start_verse or 1
    v_end = reference.end_verse or v_start
    safe_model = re.sub(r"[^a-zA-Z0-9._-]", "_", model)
    return DIAGRAM_CACHE_DIR / slug / f"v{v_start}-{v_end}_{safe_model}.json"


def load_cached_diagram(reference: Reference, model: str) -> tuple[str, dict[str, Any]] | None:
    path = _cache_key(reference, model)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["body"], data.get("usage", {})
    except (json.JSONDecodeError, KeyError):
        return None


def save_cached_diagram(reference: Reference, model: str, body: str, usage: dict[str, Any]) -> None:
    path = _cache_key(reference, model)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"body": body, "usage": usage}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate English sentence diagrams from MACULA Greek syntax and API.Bible text."
    )
    parser.add_argument("reference_arg", nargs="?", help='Example: "John 6" or "John 6:1-21"')
    parser.add_argument("--reference", help='Example: "John 6" or "John 6:1-21"')
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model name")
    parser.add_argument("--data-dir", default="data", help="Local cache directory for MACULA XML")
    parser.add_argument("--output-dir", default="output", help="Directory for rendered Markdown")
    parser.add_argument(
        "--publish-dir",
        help="Directory for the published Markdown copy (defaults to OBSIDIAN_BIBLE_STUDY_DIR)",
    )
    parser.add_argument(
        "--publish-mode",
        choices=("copy", "move"),
        default="copy",
        help="Publish behavior after local write",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Skip publishing to the Obsidian vault",
    )
    parser.add_argument(
        "--english-source",
        choices=("auto", "api-bible", "macula-gloss"),
        default="auto",
        help="Choose the English verse source",
    )
    parser.add_argument(
        "--dump-prompt",
        action="store_true",
        help="Write the assembled LLM prompt to stdout instead of calling OpenRouter",
    )
    parser.add_argument(
        "--footnotes",
        action="store_true",
        help="Append commentary notes after each verse block",
    )
    parser.add_argument(
        "--footnotes-style",
        choices=("inline", "collapse"),
        default="collapse",
        help="Render commentary footnotes inline or inside HTML details blocks",
    )
    parser.add_argument(
        "--commentary-sources",
        default="fbc",
        help="Comma-separated commentary sources: fbc, net, keener, or all",
    )
    parser.add_argument(
        "--bold-words",
        action="store_true",
        help="Bold lexically significant Greek-linked words in the diagram output",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Skip the diagram cache and always call the LLM",
    )
    args = parser.parse_args()
    args.reference = args.reference or args.reference_arg
    if not args.reference:
        parser.error("reference is required")
    return args


def main() -> int:
    load_dotenv()
    args = parse_args()
    reference = parse_reference(args.reference)
    data_dir = Path(args.data_dir)
    xml_path = ensure_macula_xml(reference, data_dir)
    verse_words = extract_macula_words(xml_path, reference)
    # --- Parallelize independent I/O: Bible text, commentary sources, BDAG index ---
    bdag_index: dict[str, str] = {}
    commentary_sources: list[CommentarySource] = []
    english_text = ""

    requested_sources: list[str] = []
    if args.footnotes:
        requested_sources = parse_requested_commentary_sources(args.commentary_sources)

    def _fetch_english() -> str:
        if args.english_source == "macula-gloss":
            return build_gloss_fallback(verse_words)
        try:
            return fetch_bible_text(reference)
        except DiagramError as exc:
            if args.english_source == "api-bible":
                raise
            print(f"Warning: API.Bible failed ({exc}), falling back to MACULA glosses.", file=sys.stderr)
            return build_gloss_fallback(verse_words)

    def _fetch_commentary(key: str) -> CommentarySource:
        if key == "fbc":
            return fetch_fbc_commentary_source(reference)
        if key == "net":
            return fetch_net_bible_notes(reference)
        return load_pdf_commentary(reference, key, data_dir)

    with ThreadPoolExecutor(max_workers=6) as pool:
        english_future = pool.submit(_fetch_english)
        commentary_futures = {key: pool.submit(_fetch_commentary, key) for key in requested_sources}
        bdag_future = pool.submit(load_bdag_index, data_dir) if args.bold_words else None

        english_text = sanitize_english_text(english_future.result())
        if bdag_future is not None:
            bdag_index = bdag_future.result()
        for key in requested_sources:
            try:
                commentary_sources.append(commentary_futures[key].result())
            except Exception as exc:
                print(f"Warning: {key} commentary failed ({exc}), skipping.", file=sys.stderr)
    prompt = build_user_prompt(reference, verse_words, english_text)

    if args.dump_prompt:
        print(prompt)
        return 0

    cached = None if args.no_cache else load_cached_diagram(reference, args.model)
    if cached is not None:
        body, usage = cached
        print("Using cached diagram", file=sys.stderr)
    else:
        body, usage = generate_validated_diagram(prompt, args.model)
        save_cached_diagram(reference, args.model, body, usage)
    bold_words = identify_bold_words(verse_words, bdag_index) if bdag_index else {}
    if bold_words:
        body = apply_bold_words(body, bold_words)
    # Obsidian Live Preview does not consistently render HTML entities like `&nbsp;`.
    # Convert them to real NBSP characters so indentation displays correctly while editing.
    body = body.replace("&nbsp;", "\u00A0").replace("&nbsp", "\u00A0")
    if commentary_sources:
        body = add_commentary_footnotes(
            body,
            reference,
            commentary_sources,
            args.footnotes_style,
            bold_words,
        )
    output_path = write_output(reference, body, usage, Path(args.output_dir))
    publish_dir = resolve_publish_dir(args)
    print(output_path)
    if publish_dir is not None:
        try:
            published_path = publish_output(output_path, publish_dir, args.publish_mode)
            print(published_path)
        except OSError as exc:
            print(
                f"Warning: could not publish {output_path.name} to {publish_dir} ({exc}).",
                file=sys.stderr,
            )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DiagramError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
