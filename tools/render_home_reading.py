from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent.parent
HOME_LOC = "https://lincolndevotional.com/"
CENTRAL = ZoneInfo("America/Chicago")
REQUIRED_FIELDS = ("display_date", "title", "bible_verse", "verse_ref", "poem")

HOME_LASTMOD_RE = re.compile(
    r"(<loc>https://lincolndevotional.com/</loc><lastmod>)\d{4}-\d{2}-\d{2}(</lastmod>)"
)
MAIN_RE = re.compile(
    r'<main class="main-content" id="devotionalContent"(?: data-entry-mmdd="\d{4}")?>'
)
DATE_INPUT_RE = re.compile(
    r'<input type="date" id="datePicker" class="nav-date-input"(?: value="\d{4}-\d{2}-\d{2}")? />'
)
ESV_BLOCK_RE = re.compile(r'<div class="verse-block(?: hidden)?" id="esvBlock">')
ASIDE_RE = re.compile(
    r'<aside class="entry-permalink(?: hidden)?" id="devotionLinkArea"'
)
LINK_RE = re.compile(
    r'<a id="devotionLink" class="entry-permalink-link" href="[^"]*"(?: data-link-title="[^"]*")?>'
)


@dataclass(frozen=True)
class HomeReading:
    mmdd: str
    display_date: str
    title: str
    bible_verse: str
    verse_ref: str
    poem_html: str
    esv_text: str
    href: str
    iso_date: str
    link_title: str


def central_today(now: datetime | None = None) -> date:
    current = now if now is not None else datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now must include a timezone")
    return current.astimezone(CENTRAL).date()


def parse_iso_date(value: str) -> date:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("date must be YYYY-MM-DD") from error
    return parsed


def render_poem_html(poem_text: str) -> str:
    lines = []
    for line in re.split(r"\r?\n", poem_text):
        cleaned = line.replace("\r", "")
        class_name = "poem-line poem-line--blank" if not cleaned.strip() else "poem-line"
        lines.append(f'<div class="{class_name}">{escape(cleaned)}</div>')
    return "".join(lines)


def build_reading(entries, esv_cache, routes, when: date) -> HomeReading:
    if not isinstance(entries, list):
        raise ValueError("entries must be a list")
    if not isinstance(routes, dict):
        raise ValueError("routes must be an object")
    mmdd = f"{when.month:02d}{when.day:02d}"
    matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("mmdd") == mmdd]
    if len(matches) != 1:
        raise ValueError(f"expected one entry for {mmdd}, found {len(matches)}")
    entry = matches[0]
    missing = [
        field for field in REQUIRED_FIELDS
        if not isinstance(entry.get(field), str) or entry[field] == ""
    ]
    if missing:
        raise ValueError(f"entry {mmdd} missing {', '.join(missing)}")
    href = routes.get(mmdd)
    if not isinstance(href, str) or not href.startswith("/entries/") or not href.endswith("/"):
        raise ValueError(f"entry {mmdd} has no entry page route")
    esv_text = ""
    if isinstance(esv_cache, dict):
        cached = esv_cache.get(mmdd)
        if isinstance(cached, dict) and isinstance(cached.get("text"), str):
            esv_text = cached["text"]
    return HomeReading(
        mmdd=mmdd,
        display_date=entry["display_date"],
        title=entry["title"],
        bible_verse=entry["bible_verse"],
        verse_ref=entry["verse_ref"],
        poem_html=render_poem_html(entry["poem"]),
        esv_text=esv_text,
        href=href,
        iso_date=when.isoformat(),
        link_title=(
            f"The Believer's Daily Treasure — {entry['display_date']}: {entry['title']}"
        ),
    )


def fill_slot(html: str, name: str, content: str) -> str:
    pattern = re.compile(
        rf"<!--home-slot:{re.escape(name)}-->.*?<!--/home-slot:{re.escape(name)}-->",
        re.DOTALL,
    )
    replacement = f"<!--home-slot:{name}-->{content}<!--/home-slot:{name}-->"

    def substitute(match):
        return replacement

    updated, count = pattern.subn(substitute, html, count=1)
    if count != 1:
        raise ValueError(f"home page is missing the {name} slot")
    return updated


def replace_once(html: str, pattern: re.Pattern, replacement: str, label: str) -> str:
    updated, count = pattern.subn(lambda _match: replacement, html, count=1)
    if count != 1:
        raise ValueError(f"home page is missing the {label}")
    return updated


def apply_home_reading(html: str, sitemap: str, reading: HomeReading) -> tuple[str, str]:
    esv_class = "verse-block" if reading.esv_text else "verse-block hidden"
    link = (
        '<a id="devotionLink" class="entry-permalink-link" '
        f'href="{escape(reading.href, quote=True)}" '
        f'data-link-title="{escape(reading.link_title, quote=True)}">'
    )
    stamped = replace_once(
        html,
        MAIN_RE,
        f'<main class="main-content" id="devotionalContent" data-entry-mmdd="{reading.mmdd}">',
        "devotional content",
    )
    stamped = replace_once(
        stamped,
        DATE_INPUT_RE,
        f'<input type="date" id="datePicker" class="nav-date-input" value="{reading.iso_date}" />',
        "date picker",
    )
    stamped = replace_once(stamped, ESV_BLOCK_RE, f'<div class="{esv_class}" id="esvBlock">', "ESV block")
    stamped = replace_once(
        stamped,
        ASIDE_RE,
        '<aside class="entry-permalink" id="devotionLinkArea"',
        "permalink",
    )
    stamped = replace_once(stamped, LINK_RE, link, "permalink link")
    stamped = fill_slot(stamped, "nav-date", escape(reading.display_date))
    stamped = fill_slot(stamped, "entry-date", escape(reading.display_date))
    stamped = fill_slot(stamped, "title", escape(reading.title))
    stamped = fill_slot(stamped, "kjv", escape(reading.bible_verse))
    stamped = fill_slot(stamped, "esv", escape(reading.esv_text))
    stamped = fill_slot(stamped, "verse-ref", escape(reading.verse_ref))
    stamped = fill_slot(stamped, "poem", reading.poem_html)
    sitemap_stamped, count = HOME_LASTMOD_RE.subn(
        lambda _match: f"<loc>{HOME_LOC}</loc><lastmod>{reading.iso_date}</lastmod>",
        sitemap,
        count=1,
    )
    if count != 1:
        raise ValueError("sitemap is missing the home page lastmod")
    return stamped, sitemap_stamped


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read {path.name}") from error


def write_text(path: Path, content: str) -> None:
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def render_root(root: Path, when: date) -> HomeReading:
    data = root / "data"
    reading = build_reading(
        load_json(data / "entries.json"),
        load_json(data / "esv_cache.json"),
        load_json(data / "routes.json"),
        when,
    )
    home_path = root / "index.html"
    sitemap_path = root / "sitemap.xml"
    try:
        html = home_path.read_text(encoding="utf-8")
        sitemap = sitemap_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("could not read the home page or sitemap") from error
    stamped, stamped_sitemap = apply_home_reading(html, sitemap, reading)
    write_text(home_path, stamped)
    write_text(sitemap_path, stamped_sitemap)
    return reading


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Write one day's reading into the home page HTML and set that "
            "page's sitemap lastmod. The date defaults to today in Central time."
        )
    )
    parser.add_argument("--date", help="Calendar date as YYYY-MM-DD. Defaults to today in Central time.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        when = central_today() if not args.date else parse_iso_date(args.date)
        reading = render_root(args.root, when)
    except ValueError as error:
        print(f"render_home_reading: {error}", file=sys.stderr)
        return 1
    print(f"{reading.iso_date} {reading.display_date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
