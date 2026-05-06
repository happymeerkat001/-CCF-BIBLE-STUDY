#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
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
DEFAULT_MODEL = "openai/gpt-4.1-mini"

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
                        "groups": word.groups,
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
        f"{json.dumps(english_payload, ensure_ascii=False, indent=2)}\n\n"
        "Greek syntax payload:\n"
        f"{json.dumps(syntax_payload, ensure_ascii=False, indent=2)}\n"
    )


def call_openrouter(prompt: str, model: str) -> tuple[str, dict[str, Any]]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise DiagramError("OPENROUTER_API_KEY is required in .env or the environment.")

    system_prompt = load_system_prompt()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
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
        f"# {reference.verse_range_label}",
        "",
        body.strip(),
    ]
    if usage_lines:
        output.extend(["", "## OpenRouter Usage", ""])
        output.extend(usage_lines)
    output_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate English sentence diagrams from MACULA Greek syntax and API.Bible text."
    )
    parser.add_argument("--reference", required=True, help='Example: "John 6" or "John 6:1-21"')
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model name")
    parser.add_argument("--data-dir", default="data", help="Local cache directory for MACULA XML")
    parser.add_argument("--output-dir", default="output", help="Directory for rendered Markdown")
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
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    reference = parse_reference(args.reference)
    xml_path = ensure_macula_xml(reference, Path(args.data_dir))
    verse_words = extract_macula_words(xml_path, reference)
    if args.english_source == "macula-gloss":
        english_text = build_gloss_fallback(verse_words)
    else:
        try:
            english_text = fetch_bible_text(reference)
        except DiagramError as exc:
            if args.english_source == "api-bible":
                raise
            print(f"Warning: API.Bible failed ({exc}), falling back to MACULA glosses.", file=sys.stderr)
            english_text = build_gloss_fallback(verse_words)
    prompt = build_user_prompt(reference, verse_words, english_text)

    if args.dump_prompt:
        print(prompt)
        return 0

    body, usage = call_openrouter(prompt, args.model)
    output_path = write_output(reference, body, usage, Path(args.output_dir))
    print(output_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DiagramError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
