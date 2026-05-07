#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

DEFAULT_FOLDER_LINK = (
    "https://drive.google.com/drive/mobile/folders/"
    "1g_1yAlDiOFy46OKpEJFbECHdbXDDdLME?usp=sharing"
)

DEFAULT_DATE = "2026-05-07"
DEFAULT_WEEKDAY = "周四"
DEFAULT_TIME = "晚上7:30-8:30"
DEFAULT_TZ = "CT"

CATEGORY_FOLDER_IDS = {
    "Note": "1KbMiNMSpa7F-pJvOGoROGcrTsimQGBzA",
    "Lecture": "1oCGTuTt3Nk7jbC0m7y20eP3sdUghtOgj",
    "Questions": "1dHTAz44u3miHJPL-1LVzqeh9YIx7Et2m",
    "Answers": "1bTrcBWB4vTVflTmcLKm8aMCfNfjpkJ1-",
}

BOOK_ALIASES = {
    "genesis": "创世记",
    "gen": "创世记",
    "ge": "创世记",
    "gn": "创世记",
    "exodus": "出埃及记",
    "exod": "出埃及记",
    "exo": "出埃及记",
    "ex": "出埃及记",
    "leviticus": "利未记",
    "lev": "利未记",
    "le": "利未记",
    "numbers": "民数记",
    "num": "民数记",
    "nu": "民数记",
    "deuteronomy": "申命记",
    "deut": "申命记",
    "dt": "申命记",
    "joshua": "约书亚记",
    "josh": "约书亚记",
    "judges": "士师记",
    "judg": "士师记",
    "jdg": "士师记",
    "ruth": "路得记",
    "1samuel": "撒母耳记上",
    "1sam": "撒母耳记上",
    "1sa": "撒母耳记上",
    "2samuel": "撒母耳记下",
    "2sam": "撒母耳记下",
    "2sa": "撒母耳记下",
    "1kings": "列王纪上",
    "1kgs": "列王纪上",
    "2kings": "列王纪下",
    "2kgs": "列王纪下",
    "1chronicles": "历代志上",
    "1chron": "历代志上",
    "1chr": "历代志上",
    "2chronicles": "历代志下",
    "2chron": "历代志下",
    "2chr": "历代志下",
    "ezra": "以斯拉记",
    "nehemiah": "尼希米记",
    "neh": "尼希米记",
    "esther": "以斯帖记",
    "esth": "以斯帖记",
    "job": "约伯记",
    "psalms": "诗篇",
    "psalm": "诗篇",
    "ps": "诗篇",
    "proverbs": "箴言",
    "prov": "箴言",
    "prv": "箴言",
    "ecclesiastes": "传道书",
    "eccl": "传道书",
    "songofsolomon": "雅歌",
    "songofsongs": "雅歌",
    "song": "雅歌",
    "isaiah": "以赛亚书",
    "isa": "以赛亚书",
    "jeremiah": "耶利米书",
    "jer": "耶利米书",
    "lamentations": "耶利米哀歌",
    "lam": "耶利米哀歌",
    "ezekiel": "以西结书",
    "ezek": "以西结书",
    "eze": "以西结书",
    "daniel": "但以理书",
    "dan": "但以理书",
    "hosea": "何西阿书",
    "hos": "何西阿书",
    "joel": "约珥书",
    "amos": "阿摩司书",
    "obadiah": "俄巴底亚书",
    "obad": "俄巴底亚书",
    "jonah": "约拿书",
    "jon": "约拿书",
    "micah": "弥迦书",
    "mic": "弥迦书",
    "nahum": "那鸿书",
    "nah": "那鸿书",
    "habakkuk": "哈巴谷书",
    "hab": "哈巴谷书",
    "zephaniah": "西番雅书",
    "zeph": "西番雅书",
    "haggai": "哈该书",
    "hag": "哈该书",
    "zechariah": "撒迦利亚书",
    "zech": "撒迦利亚书",
    "malachi": "玛拉基书",
    "mal": "玛拉基书",
    "matthew": "马太福音",
    "matt": "马太福音",
    "mt": "马太福音",
    "mark": "马可福音",
    "mrk": "马可福音",
    "mk": "马可福音",
    "luke": "路加福音",
    "luk": "路加福音",
    "lk": "路加福音",
    "john": "约翰福音",
    "jhn": "约翰福音",
    "jn": "约翰福音",
    "acts": "使徒行传",
    "act": "使徒行传",
    "romans": "罗马书",
    "rom": "罗马书",
    "1corinthians": "哥林多前书",
    "1cor": "哥林多前书",
    "2corinthians": "哥林多后书",
    "2cor": "哥林多后书",
    "galatians": "加拉太书",
    "gal": "加拉太书",
    "ephesians": "以弗所书",
    "eph": "以弗所书",
    "philippians": "腓立比书",
    "phil": "腓立比书",
    "phlp": "腓立比书",
    "colossians": "歌罗西书",
    "col": "歌罗西书",
    "1thessalonians": "帖撒罗尼迦前书",
    "1thess": "帖撒罗尼迦前书",
    "2thessalonians": "帖撒罗尼迦后书",
    "2thess": "帖撒罗尼迦后书",
    "1timothy": "提摩太前书",
    "1tim": "提摩太前书",
    "2timothy": "提摩太后书",
    "2tim": "提摩太后书",
    "titus": "提多书",
    "philemon": "腓利门书",
    "phlm": "腓利门书",
    "hebrews": "希伯来书",
    "heb": "希伯来书",
    "james": "雅各书",
    "jas": "雅各书",
    "1peter": "彼得前书",
    "1pet": "彼得前书",
    "2peter": "彼得后书",
    "2pet": "彼得后书",
    "1john": "约翰一书",
    "1jn": "约翰一书",
    "2john": "约翰二书",
    "2jn": "约翰二书",
    "3john": "约翰三书",
    "3jn": "约翰三书",
    "jude": "犹大书",
    "revelation": "启示录",
    "rev": "启示录",
}

CHINESE_BOOK_ALIASES = {
    "创": "创世记",
    "创世记": "创世记",
    "出": "出埃及记",
    "出埃及记": "出埃及记",
    "利": "利未记",
    "利未记": "利未记",
    "民": "民数记",
    "民数记": "民数记",
    "申": "申命记",
    "申命记": "申命记",
    "书": "约书亚记",
    "约书亚记": "约书亚记",
    "士": "士师记",
    "士师记": "士师记",
    "得": "路得记",
    "路得记": "路得记",
    "撒上": "撒母耳记上",
    "撒母耳记上": "撒母耳记上",
    "撒下": "撒母耳记下",
    "撒母耳记下": "撒母耳记下",
    "王上": "列王纪上",
    "列王纪上": "列王纪上",
    "王下": "列王纪下",
    "列王纪下": "列王纪下",
    "代上": "历代志上",
    "历代志上": "历代志上",
    "代下": "历代志下",
    "历代志下": "历代志下",
    "拉": "以斯拉记",
    "以斯拉记": "以斯拉记",
    "尼": "尼希米记",
    "尼希米记": "尼希米记",
    "斯": "以斯帖记",
    "以斯帖记": "以斯帖记",
    "伯": "约伯记",
    "约伯记": "约伯记",
    "诗": "诗篇",
    "诗篇": "诗篇",
    "箴": "箴言",
    "箴言": "箴言",
    "传": "传道书",
    "传道书": "传道书",
    "歌": "雅歌",
    "雅歌": "雅歌",
    "赛": "以赛亚书",
    "以赛亚书": "以赛亚书",
    "耶": "耶利米书",
    "耶利米书": "耶利米书",
    "哀": "耶利米哀歌",
    "耶利米哀歌": "耶利米哀歌",
    "结": "以西结书",
    "以西结书": "以西结书",
    "但": "但以理书",
    "但以理书": "但以理书",
    "何": "何西阿书",
    "何西阿书": "何西阿书",
    "珥": "约珥书",
    "约珥书": "约珥书",
    "摩": "阿摩司书",
    "阿摩司书": "阿摩司书",
    "俄": "俄巴底亚书",
    "俄巴底亚书": "俄巴底亚书",
    "拿": "约拿书",
    "约拿书": "约拿书",
    "弥": "弥迦书",
    "弥迦书": "弥迦书",
    "鸿": "那鸿书",
    "那鸿书": "那鸿书",
    "哈": "哈巴谷书",
    "哈巴谷书": "哈巴谷书",
    "番": "西番雅书",
    "西番雅书": "西番雅书",
    "该": "哈该书",
    "哈该书": "哈该书",
    "亚": "撒迦利亚书",
    "撒迦利亚书": "撒迦利亚书",
    "玛": "玛拉基书",
    "玛拉基书": "玛拉基书",
    "太": "马太福音",
    "马太福音": "马太福音",
    "可": "马可福音",
    "马可福音": "马可福音",
    "路": "路加福音",
    "路加福音": "路加福音",
    "约": "约翰福音",
    "约翰福音": "约翰福音",
    "徒": "使徒行传",
    "使徒行传": "使徒行传",
    "罗": "罗马书",
    "罗马书": "罗马书",
    "林前": "哥林多前书",
    "哥林多前书": "哥林多前书",
    "林后": "哥林多后书",
    "哥林多后书": "哥林多后书",
    "加": "加拉太书",
    "加拉太书": "加拉太书",
    "弗": "以弗所书",
    "以弗所书": "以弗所书",
    "腓": "腓立比书",
    "腓立比书": "腓立比书",
    "西": "歌罗西书",
    "歌罗西书": "歌罗西书",
    "帖前": "帖撒罗尼迦前书",
    "帖撒罗尼迦前书": "帖撒罗尼迦前书",
    "帖后": "帖撒罗尼迦后书",
    "帖撒罗尼迦后书": "帖撒罗尼迦后书",
    "提前": "提摩太前书",
    "提摩太前书": "提摩太前书",
    "提后": "提摩太后书",
    "提摩太后书": "提摩太后书",
    "多": "提多书",
    "提多书": "提多书",
    "门": "腓利门书",
    "腓利门书": "腓利门书",
    "来": "希伯来书",
    "希伯来书": "希伯来书",
    "雅": "雅各书",
    "雅各书": "雅各书",
    "彼前": "彼得前书",
    "彼得前书": "彼得前书",
    "彼后": "彼得后书",
    "彼得后书": "彼得后书",
    "约一": "约翰一书",
    "约翰一书": "约翰一书",
    "约二": "约翰二书",
    "约翰二书": "约翰二书",
    "约三": "约翰三书",
    "约翰三书": "约翰三书",
    "犹": "犹大书",
    "犹大书": "犹大书",
    "启": "启示录",
    "启示录": "启示录",
}

TRAD_TO_SIMP_BOOK = {
    "創世記": "创世记",
    "出埃及記": "出埃及记",
    "利未記": "利未记",
    "民數記": "民数记",
    "申命記": "申命记",
    "約書亞記": "约书亚记",
    "士師記": "士师记",
    "撒母耳記上": "撒母耳记上",
    "撒母耳記下": "撒母耳记下",
    "列王紀上": "列王纪上",
    "列王紀下": "列王纪下",
    "歷代志上": "历代志上",
    "歷代志下": "历代志下",
    "約伯記": "约伯记",
    "詩篇": "诗篇",
    "箴言": "箴言",
    "傳道書": "传道书",
    "耶利米哀歌": "耶利米哀歌",
    "以西結書": "以西结书",
    "約珥書": "约珥书",
    "哈巴谷書": "哈巴谷书",
    "瑪拉基書": "玛拉基书",
    "馬太福音": "马太福音",
    "馬可福音": "马可福音",
    "路加福音": "路加福音",
    "約翰福音": "约翰福音",
    "羅馬書": "罗马书",
    "哥林多前書": "哥林多前书",
    "哥林多後書": "哥林多后书",
    "加拉太書": "加拉太书",
    "以弗所書": "以弗所书",
    "腓立比書": "腓立比书",
    "歌羅西書": "歌罗西书",
    "帖撒羅尼迦前書": "帖撒罗尼迦前书",
    "帖撒羅尼迦後書": "帖撒罗尼迦后书",
    "提摩太前書": "提摩太前书",
    "提摩太後書": "提摩太后书",
    "腓利門書": "腓利门书",
    "希伯來書": "希伯来书",
    "雅各書": "雅各书",
    "彼得前書": "彼得前书",
    "彼得後書": "彼得后书",
    "約翰一書": "约翰一书",
    "約翰二書": "约翰二书",
    "約翰三書": "约翰三书",
    "猶大書": "犹大书",
    "啟示錄": "启示录",
}

FILE_ID_RE = re.compile(r"/d/([A-Za-z0-9_-]+)|[?&]id=([A-Za-z0-9_-]+)")
LESSON_RE = re.compile(r"L(\d{2})", re.IGNORECASE)
FOLDER_ENTRY_RE = re.compile(
    r'<a href="(?P<href>https://drive\.google\.com/file/d/[^"]+)"[^>]*>.*?'
    r'<div class="flip-entry-title">(?P<title>.*?)</div>',
    re.S,
)
REFERENCE_RE = re.compile(
    r"^\s*(?P<book>.+?)\s*(?P<chapter>\d+)\s*:\s*"
    r"(?P<start>\d+)(?:\s*-\s*(?P<end>\d+))?\s*$"
)
TITLE_REF_RE = re.compile(
    r"(?P<book>\S+)\s+"
    r"第(?P<ch1>[一二三四五六七八九十百零〇兩两]+)章"
    r"(?:第)?(?P<v1>[一二三四五六七八九十百零〇兩两]+)節"
    r"至"
    r"(?:第(?P<ch2>[一二三四五六七八九十百零〇兩两]+)章)?"
    r"(?:第)?(?P<v2>[一二三四五六七八九十百零〇兩两]+)節"
)


@dataclass(frozen=True)
class ResourceLink:
    label: str
    lesson_code: str
    title: str
    url: str


def _http_get(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _format_md(date_iso: str) -> str:
    parsed = dt.date.fromisoformat(date_iso)
    return f"{parsed.month}/{parsed.day}"


def _extract_file_id(raw: str) -> str | None:
    match = FILE_ID_RE.search(raw)
    if not match:
        return None
    return match.group(1) or match.group(2)


def _normalize_drive_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view?usp=drivesdk"


def _next_lesson_code(lesson_code: str) -> str:
    lesson_number = int(lesson_code[1:])
    next_number = lesson_number + 1
    if next_number > 99:
        raise ValueError(f"Next lesson after {lesson_code} is out of supported range.")
    return f"L{next_number:02d}"


def _list_folder_entries(folder_id: str) -> list[tuple[str, str]]:
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    page = _http_get(url)
    entries: list[tuple[str, str]] = []
    for match in FOLDER_ENTRY_RE.finditer(page):
        href = html.unescape(match.group("href"))
        title = html.unescape(match.group("title")).strip()
        file_id = _extract_file_id(href)
        if file_id is None:
            continue
        entries.append((title, _normalize_drive_url(file_id)))
    if not entries:
        raise ValueError(f"No file entries found in folder {folder_id}.")
    return entries


def _find_resource_link(label: str, lesson_code: str) -> ResourceLink:
    folder_id = CATEGORY_FOLDER_IDS[label]
    expected = f"_{lesson_code}_"
    for title, url in _list_folder_entries(folder_id):
        if expected in title:
            return ResourceLink(
                label=label,
                lesson_code=lesson_code,
                title=title,
                url=url,
            )
    raise ValueError(f"Could not find {label} file for {lesson_code}.")


def _validate_previous_lesson_code(previous_lesson: str) -> str:
    lesson_code = previous_lesson.strip().upper()
    if not LESSON_RE.fullmatch(lesson_code):
        raise ValueError("--previous-lesson must look like L15.")
    return lesson_code


def _chinese_number_to_int(text: str) -> int:
    numerals = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "兩": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    compact = text.strip()
    if not compact:
        raise ValueError("Chinese numeral cannot be empty.")
    if compact == "十":
        return 10

    total = 0
    if "百" in compact:
        hundreds_text, compact = compact.split("百", 1)
        total += (numerals.get(hundreds_text, 1) if hundreds_text else 1) * 100
        compact = compact.lstrip("零〇")

    if "十" in compact:
        tens_text, ones_text = compact.split("十", 1)
        total += (numerals.get(tens_text, 1) if tens_text else 1) * 10
        if ones_text:
            if ones_text not in numerals:
                raise ValueError(f"Unsupported Chinese numeral: {text}")
            total += numerals[ones_text]
        return total

    if compact not in numerals:
        raise ValueError(f"Unsupported Chinese numeral: {text}")
    return total + numerals[compact]


def _normalize_reference(reference: str) -> str:
    compact = reference.strip()
    match = REFERENCE_RE.match(compact)
    if not match:
        raise ValueError(
            "Reference must look like 'John 13:1-30' or '约13:1-30'."
        )

    book = match.group("book").strip()
    chapter = match.group("chapter")
    start = match.group("start")
    end = match.group("end")

    if re.search(r"[\u4e00-\u9fff]", book):
        normalized_book = CHINESE_BOOK_ALIASES.get(book.replace(" ", ""))
        if normalized_book is None:
            normalized_book = book.replace(" ", "")
    else:
        normalized_key = re.sub(r"[^A-Za-z0-9]", "", book).lower()
        normalized_book = BOOK_ALIASES.get(normalized_key)
        if normalized_book is None:
            raise ValueError(f"Unsupported book alias: {book}")

    verse_part = f"{chapter}:{start}"
    if end:
        verse_part += f"-{end}"
    return f"{normalized_book}{verse_part}"


def _extract_reference_from_title(title: str) -> str:
    match = TITLE_REF_RE.search(title)
    if not match:
        raise ValueError(
            f"Could not extract Bible reference from title: {title}"
        )

    book = match.group("book").strip()
    normalized_book = TRAD_TO_SIMP_BOOK.get(book, book)
    ch1 = _chinese_number_to_int(match.group("ch1"))
    v1 = _chinese_number_to_int(match.group("v1"))
    ch2_text = match.group("ch2")
    v2 = _chinese_number_to_int(match.group("v2"))

    if ch2_text is None:
        return f"{normalized_book}{ch1}:{v1}-{v2}"

    ch2 = _chinese_number_to_int(ch2_text)
    return f"{normalized_book}{ch1}:{v1}-{ch2}:{v2}"


def build_message(
    *,
    mentions: list[str],
    normalized_reference: str,
    date_iso: str,
    weekday_zh: str,
    time_range: str,
    tz_label: str,
    resource_links: list[ResourceLink],
    folder_link: str,
) -> str:
    mention_prefix = ""
    cleaned_mentions = [mention.strip() for mention in mentions if mention.strip()]
    if cleaned_mentions:
        mention_prefix = " ".join(cleaned_mentions) + " "

    md_date = _format_md(date_iso)
    first_line = (
        f"{mention_prefix}这周我们会查考{normalized_reference}节的内容，"
        f"预查时间是{weekday_zh}（{md_date}）{time_range}（{tz_label}），"
        "请预留时间，谢谢！"
    )

    lines = [first_line, "", "以下是CCF 资料：", ""]
    for resource in resource_links:
        lines.extend([resource.label, resource.url, ""])
    lines.extend(["The google drive for these resources are:", folder_link])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a Chinese CCF Bible-study reminder message using a Bible "
            "reference plus a previous lesson code."
        )
    )
    parser.add_argument(
        "--reference",
        "--passage",
        dest="reference",
        help="Bible reference in English or Chinese, e.g. John 13:1-30 or 约13:1-30.",
    )
    parser.add_argument(
        "--mentions",
        nargs="*",
        default=[],
        help="Optional mentions like @Amber @mouxiaoyu.",
    )
    parser.add_argument("--date", default=DEFAULT_DATE, help="Date in YYYY-MM-DD.")
    parser.add_argument("--weekday", default=DEFAULT_WEEKDAY, help="Chinese weekday label.")
    parser.add_argument("--time", default=DEFAULT_TIME, help="Time range in Chinese.")
    parser.add_argument("--tz", default=DEFAULT_TZ, help="Timezone label shown in parentheses.")
    parser.add_argument(
        "--folder-link",
        default=DEFAULT_FOLDER_LINK,
        help="Shared Google Drive folder link.",
    )
    parser.add_argument(
        "--previous-lesson",
        required=True,
        help="Previous lesson code like L15.",
    )
    args = parser.parse_args()

    try:
        previous_lesson_code = _validate_previous_lesson_code(args.previous_lesson)
        current_lesson_code = _next_lesson_code(previous_lesson_code)
        resource_links = [
            _find_resource_link(label, current_lesson_code)
            for label in ("Note", "Lecture", "Questions", "Answers")
        ]
        if args.reference:
            normalized_reference = _normalize_reference(args.reference)
        else:
            normalized_reference = _extract_reference_from_title(resource_links[0].title)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        build_message(
            mentions=args.mentions,
            normalized_reference=normalized_reference,
            date_iso=args.date,
            weekday_zh=args.weekday,
            time_range=args.time,
            tz_label=args.tz,
            resource_links=resource_links,
            folder_link=args.folder_link,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
