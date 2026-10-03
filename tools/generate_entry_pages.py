from __future__ import annotations

from html import escape
import json
from pathlib import Path
from xml.etree import ElementTree as ET

if __package__:
    from .esv_limits import validate_esv_cache
else:
    from esv_limits import validate_esv_cache


MONTH_NAMES = {
    1: "january",
    2: "february",
    3: "march",
    4: "april",
    5: "may",
    6: "june",
    7: "july",
    8: "august",
    9: "september",
    10: "october",
    11: "november",
    12: "december",
}

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_PATH = ROOT / "data" / "entries.json"
ESV_CACHE_PATH = ROOT / "data" / "esv_cache.json"
OUTPUT_ROOT = ROOT
SITE_URL = "https://lincolndevotional.com"
SITE_NAME = "The Believer's Daily Treasure"
HOMEPAGE_DESCRIPTION = (
    "A short daily Christian devotional with Scripture for every day, drawn from "
    "The Believer’s Daily Treasure, the devotional Abraham Lincoln carried."
)
EXPLORE_DESCRIPTION = "Browse 366 daily Christian devotions by topic and by today’s need."
ROUTES_PATH = ROOT / "data" / "routes.json"
REQUIRED_FIELDS = ("mmdd", "month", "day", "display_date", "title", "bible_verse", "verse_ref", "poem")


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def slugify_entry(entry):
    month_name = MONTH_NAMES[entry["month"]]
    return f"{month_name}-{entry['day']}"


def build_entry_href(entry):
    return f"/entries/{slugify_entry(entry)}/"


def build_topic_href(topic_slug):
    return f"/explore/?topic={topic_slug}"


def build_topic_map(topic_taxonomy):
    return {topic["slug"]: topic for topic in topic_taxonomy.get("topics", [])}


def build_description(entry):
    title = entry["title"].strip()
    date_text = entry["display_date"].strip()
    verse_ref = entry["verse_ref"].strip()
    bible_verse = entry["bible_verse"].strip()
    prefix = f"{date_text}: {title}. {verse_ref}. "
    excerpt = truncate_at_word_boundary(bible_verse, max(40, 160 - len(prefix)))
    description = f"{prefix}{excerpt}"
    if len(description) > 160:
        description = truncate_at_word_boundary(description, 160)
    return description


def truncate_at_word_boundary(text, max_length):
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    cutoff = max_length - 3
    truncated = normalized[:cutoff].rsplit(" ", 1)[0].rstrip(".,;:- ")
    if not truncated:
        truncated = normalized[:cutoff].rstrip(".,;:- ")
    truncated = truncated.rstrip(".,;:- ")
    return f"{truncated}..."


def normalize_site_url(site_url):
    return site_url.rstrip("/")


def render_common_social_meta(site_url):
    return f'''<meta property="og:type" content="website" />
    <meta property="og:site_name" content="{SITE_NAME}" />
    <meta name="twitter:card" content="summary" />
    <link rel="icon" href="/favicon.ico" sizes="any" />
    <link rel="icon" href="/icon.svg" type="image/svg+xml" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />'''


def build_static_asset_version():
    return "20260519a"


def render_static_date_picker(entry):
    return f"""
            <div
              class="date-picker-wrap"
              data-entry-mmdd="{entry['mmdd']}"
              data-routes-path="../../data/routes.json"
            >
              <span class="date-picker-label">Jump to</span>
              <span class="current-date-display">{escape(entry['display_date'])}</span>
              <input type="date" class="nav-date-input" aria-label="Jump to another date" />
            </div>"""


def normalize_poem_lines(poem_text):
    return [line.replace("\r", "") for line in poem_text.splitlines()]


def validate_entries(entries):
    seen_slugs = set()
    for entry in entries:
        missing = [field for field in REQUIRED_FIELDS if not entry.get(field)]
        if missing:
            raise ValueError(f"Entry {entry.get('mmdd', '<unknown>')} missing required fields: {', '.join(missing)}")

        slug = slugify_entry(entry)
        if slug in seen_slugs:
            raise ValueError(f"Duplicate slug generated: {slug}")
        seen_slugs.add(slug)


def render_poem_html(poem_text):
    poem_lines = []
    for line in normalize_poem_lines(poem_text):
        class_name = "poem-line poem-line--blank" if not line.strip() else "poem-line"
        poem_lines.append(f'<div class="{class_name}">{escape(line)}</div>')
    return "\n".join(poem_lines)


def render_esv_block(esv_text):
    if not esv_text:
        return ""
    return f"""
              <div class="verse-block">
                <span class="version-label">ESV</span>
                <p class="entry-text">{escape(esv_text)}</p>
              </div>"""


def render_primary_nav(prefix, current_page=None):
    links = [
        ("Devotional", f"{prefix}index.html", current_page == "devotional"),
        ("By Topic", f"{prefix}explore/", current_page == "explore"),
        ("About", f"{prefix}about.html", current_page == "about"),
    ]
    items = []
    for label, href, active in links:
        active_attr = ' aria-current="page"' if active else ""
        items.append(f'<a{active_attr} href="{href}">{label}</a>')
    return f'<nav class="site-nav" aria-label="Primary">{"".join(items)}</nav>'


def render_topic_chips(assignment, topic_map):
    if not assignment:
        return ""
    primary_slug = assignment.get("primary_topic")
    ordered_slugs = []
    if primary_slug:
        ordered_slugs.append(primary_slug)
    for topic_slug in assignment.get("topics", []):
        if topic_slug not in ordered_slugs:
            ordered_slugs.append(topic_slug)
    chips = []
    for topic_slug in ordered_slugs:
        topic = topic_map.get(topic_slug)
        if not topic:
            continue
        is_primary = topic_slug == primary_slug
        cls = "topic-chip topic-chip--primary" if is_primary else "topic-chip"
        chips.append(f'<a class="{cls}" href="{build_topic_href(topic_slug)}">{escape(topic["name"])}</a>')
    if not chips:
        return ""
    return f'<div class="entry-topic-chips">{"".join(chips)}</div>'


def build_explore_payload(entries, entry_topics, topic_taxonomy):
    topic_list = topic_taxonomy.get("topics", [])
    need_list = topic_taxonomy.get("reader_needs", [])

    topic_counts = {topic["slug"]: 0 for topic in topic_list}
    primary_counts = {topic["slug"]: 0 for topic in topic_list}
    need_counts = {need["slug"]: 0 for need in need_list}

    entry_records = []
    for entry in entries:
        assignment = entry_topics.get(entry["mmdd"], {})
        primary = assignment.get("primary_topic") or ""
        topics = list(assignment.get("topics", []))
        needs = list(assignment.get("reader_needs", []))
        if primary and primary in primary_counts:
            primary_counts[primary] += 1
        for slug in topics:
            if slug in topic_counts:
                topic_counts[slug] += 1
        for slug in needs:
            if slug in need_counts:
                need_counts[slug] += 1
        entry_records.append({
            "mmdd": entry["mmdd"],
            "month": entry["month"],
            "display_date": entry["display_date"],
            "title": entry["title"],
            "href": build_entry_href(entry),
            "primary": primary,
            "topics": topics,
            "needs": needs,
        })

    topics_payload = [
        {
            "slug": topic["slug"],
            "name": topic["name"],
            "description": topic.get("description", ""),
            "count": topic_counts.get(topic["slug"], 0),
            "primary_count": primary_counts.get(topic["slug"], 0),
        }
        for topic in topic_list
    ]
    needs_payload = [
        {
            "slug": need["slug"],
            "name": need["name"],
            "description": need.get("description", ""),
            "count": need_counts.get(need["slug"], 0),
        }
        for need in need_list
    ]
    months_payload = [
        {"number": number, "name": name.capitalize()}
        for number, name in MONTH_NAMES.items()
    ]
    return {
        "entries": entry_records,
        "topics": topics_payload,
        "needs": needs_payload,
        "months": months_payload,
        "total": len(entry_records),
    }


def build_search_index(entries, esv_cache):
    validate_esv_cache(esv_cache)
    return [
        {
            "mmdd": entry["mmdd"],
            "display_date": entry["display_date"],
            "title": entry["title"],
            "href": build_entry_href(entry),
            "verse_ref": entry["verse_ref"],
            "devotional": entry["poem"],
            "kjv": entry["bible_verse"],
            "esv": esv_cache.get(entry["mmdd"], {}).get("text", ""),
        }
        for entry in entries
    ]


def render_facet_chip(slug, label, count, facet):
    disabled = ' data-disabled="true"' if count == 0 else ""
    count_html = f'<span class="facet-chip-count">{count}</span>' if count else '<span class="facet-chip-count facet-chip-count--zero">0</span>'
    return (
        f'<button class="facet-chip" type="button" data-facet="{facet}" '
        f'data-slug="{escape(slug)}"{disabled} aria-pressed="false">'
        f'<span class="facet-chip-label">{escape(label)}</span>{count_html}</button>'
    )


def render_explore_results(payload):
    sections = []
    for month in payload["months"]:
        entries = [entry for entry in payload["entries"] if entry["month"] == month["number"]]
        if not entries:
            continue
        count = len(entries)
        count_label = "1 devotion" if count == 1 else f"{count} devotions"
        items = "".join(
            f'<li><a class="explore-entry" href="{escape(entry["href"])}">'
            f'<span class="explore-entry-date">{escape(entry["display_date"])}</span>'
            f'<span class="explore-entry-title">{escape(entry["title"])}</span>'
            '</a></li>'
            for entry in entries
        )
        sections.append(
            '<section class="explore-month"><header class="explore-month-header">'
            f'<h3 class="explore-month-title">{escape(month["name"])}</h3>'
            f'<span class="explore-month-count">{count_label}</span></header>'
            f'<ul class="explore-entries-list">{items}</ul></section>'
        )
    return "\n".join(sections)


def render_explore_page(topic_taxonomy, payload, site_url):
    topic_chips = "".join(
        render_facet_chip(topic["slug"], topic["name"], topic["count"], "topic")
        for topic in payload["topics"]
    )
    need_chips_html = "".join(
        render_facet_chip(need["slug"], need["name"], need["count"], "need")
        for need in payload["needs"]
    )

    needs_have_any = any(need["count"] > 0 for need in payload["needs"])
    needs_note = "" if needs_have_any else (
        '<p class="facet-empty-note">Reader-need tagging is in progress — these filters will populate as entries are tagged.</p>'
    )

    inline_payload = escape(json.dumps(payload, ensure_ascii=False), quote=False)

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="canonical" href="{site_url}/explore/" />
    <title>Explore - The Believer's Daily Treasure</title>
    <meta name="description" content="{escape(EXPLORE_DESCRIPTION)}" />
    <meta property="og:title" content="Explore - The Believer's Daily Treasure" />
    <meta property="og:description" content="{escape(EXPLORE_DESCRIPTION)}" />
    <meta property="og:url" content="{site_url}/explore/" />
    {render_common_social_meta(site_url)}
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500;600&family=Newsreader:wght@400;500;600&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="../style.css?v=20261003a" />
    <script src="../analytics.js?v=20260509e"></script>
  </head>
  <body>
    <div class="page">
      <header class="site-header">
        <div class="brand">
          <p class="site-eyebrow">Abraham Lincoln's Daily Devotional</p>
          <h1 class="site-title">The Believer's Daily Treasure</h1>
          <p class="site-tagline">Texts of scripture, arranged for every day in the year.</p>
        </div>
        <div class="site-actions">
          {render_primary_nav("../", current_page="explore")}
          <button class="theme-toggle" id="themeToggle" type="button">Dark mode</button>
        </div>
      </header>
      <main class="main-content explore-main">
        <article class="entry-card explore-hero" aria-live="polite">
          <header class="entry-header">
            <p class="entry-date">By Topic</p>
            <h2 class="entry-title">Find a devotion for today’s need</h2>
          </header>
        </article>

        <section class="explore-filters" aria-label="Filter devotions">
          <div class="explore-search" hidden>
            <label class="facet-legend" for="devotion-search">Search devotions</label>
            <input id="devotion-search" type="search" placeholder="Word, phrase, or scripture reference" aria-describedby="search-status" />
            <p id="search-status" class="explore-search-status" role="status"></p>
          </div>
          <fieldset class="facet-group" data-facet-group="topic">
            <legend class="facet-legend">By topic</legend>
            <div class="facet-chips" role="group" aria-label="Topic filters">{topic_chips}</div>
          </fieldset>
          <fieldset class="facet-group" data-facet-group="need">
            <legend class="facet-legend">By need</legend>
            <div class="facet-chips" role="group" aria-label="Reader-need filters">{need_chips_html}</div>
            {needs_note}
          </fieldset>
          <div class="explore-summary">
            <span class="explore-count" data-result-count>{payload['total']} devotions</span>
            <button class="explore-clear" type="button" hidden>Clear filters</button>
          </div>
        </section>

        <section class="explore-results" data-explore-results aria-live="polite" aria-label="Devotions">
          {render_explore_results(payload)}
        </section>
      </main>

      <footer class="site-footer">
        <p class="footer-sites"><a href="https://lincolndevotional.com/">LincolnDevotional.com</a>, the daily devotional Abraham Lincoln carried.</p>
        <p class="footer-sites"><a href="https://tworiversmatters.com/">TwoRiversMatters.com</a>, covering Two Rivers, Wisconsin city government, meetings, and civic news.</p>
        <p class="footer-legal"><a href="../copyright.html">Copyright</a></p>
      </footer>
    </div>
    <script type="application/json" id="explore-data">{inline_payload}</script>
    <script src="../theme.js?v=20260123"></script>
    <script src="../explore.js?v=20261003a"></script>
  </body>
</html>"""




def render_entry_page(entry, previous_entry, next_entry, esv_text, site_url, topic_map=None, assignment=None):
    href = build_entry_href(entry)
    canonical_url = f"{site_url}{href}"
    title = f"{entry['display_date']} - {entry['title']}"
    description = build_description(entry)
    prev_link = f'<a href="../{slugify_entry(previous_entry)}/">&larr; Previous</a>'
    next_link = f'<a href="../{slugify_entry(next_entry)}/">Next &rarr;</a>'
    date_picker = render_static_date_picker(entry)
    navigation = f"""
          <nav class="entry-nav" aria-label="Entry navigation">
            {prev_link}
            {date_picker}
            {next_link}
          </nav>"""

    prev_head_link = f'<link rel="prev" href="{build_entry_href(previous_entry)}" />' if previous_entry else ""
    next_head_link = f'<link rel="next" href="{build_entry_href(next_entry)}" />' if next_entry else ""

    esv_block = render_esv_block(esv_text)
    poem_html = render_poem_html(entry["poem"])
    topic_chips = render_topic_chips(assignment, topic_map or {})
    link_title = f"The Believer's Daily Treasure — {entry['display_date']}: {entry['title']}"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="canonical" href="{canonical_url}" />
    <title>{escape(title)}</title>
    <meta name="description" content="{escape(description)}" />
    <meta property="og:title" content="{escape(title)}" />
    <meta property="og:description" content="{escape(description)}" />
    <meta property="og:url" content="{canonical_url}" />
    {render_common_social_meta(site_url)}
    {prev_head_link}
    {next_head_link}
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500;600&family=Newsreader:wght@400;500;600&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="../../style.css?v=20260519c" />
    <script src="../../analytics.js?v=20260509e"></script>
  </head>
  <body>
    <div class="page">
      <header class="site-header">
        <div class="brand">
          <p class="site-eyebrow">Abraham Lincoln's Daily Devotional</p>
          <h1 class="site-title">The Believer's Daily Treasure</h1>
          <p class="site-tagline">Texts of scripture, arranged for every day in the year.</p>
        </div>
        <div class="site-actions">
          {render_primary_nav("../../", current_page="devotional")}
          <button class="theme-toggle" id="themeToggle" type="button">Dark mode</button>
        </div>
      </header>

      <main class="main-content">
        {navigation}
        <article class="entry-card" aria-live="polite">
          <header class="entry-header">
            <p class="entry-date">{escape(entry['display_date'])}</p>
            <h2 class="entry-title">{escape(entry['title'])}</h2>
          </header>
          <section class="entry-section entry-section--scripture">
            <h3 class="entry-section-title">Scripture</h3>
            <div class="verse-columns">
              <div class="verse-block">
                <span class="version-label">KJV</span>
                <p class="entry-text">{escape(entry['bible_verse'])}</p>
              </div>
              {esv_block}
            </div>
            <p class="entry-verse-ref">{escape(entry['verse_ref'])}</p>
          </section>
          <section class="entry-section entry-poem">
            <h3 class="entry-section-title">Poem</h3>
            <div class="entry-text">{poem_html}</div>
          </section>
          {topic_chips}
        </article>
      </main>

      <aside class="entry-permalink" id="devotionLinkArea" aria-label="Share this devotion">
        <a id="devotionLink" class="entry-permalink-link" href="{href}" data-link-title="{escape(link_title)}">
          <span class="entry-permalink-flourish entry-permalink-flourish--left" aria-hidden="true">&#10086;</span>
          <span class="entry-permalink-text">Share this devotion</span>
          <span class="entry-permalink-flourish entry-permalink-flourish--right" aria-hidden="true">&#10086;</span>
        </a>
      </aside>

      <footer class="site-footer">
        <p class="footer-sites"><a href="https://lincolndevotional.com/">LincolnDevotional.com</a>, the daily devotional Abraham Lincoln carried.</p>
        <p class="footer-sites"><a href="https://tworiversmatters.com/">TwoRiversMatters.com</a>, covering Two Rivers, Wisconsin city government, meetings, and civic news.</p>
        <p class="footer-legal"><a href="../../copyright.html">Copyright</a></p>
      </footer>
    </div>
    <script src="../../static-entry-nav.js?v={build_static_asset_version()}"></script>
    <script src="../../theme.js?v=20260123"></script>
    <script src="../../permalink.js?v=20260519a"></script>
  </body>
</html>
"""


def write_sitemap(entries, output_root, site_url, topic_taxonomy=None):
    root = ET.Element("urlset", attrib={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"})
    static_paths = ["/", "/about.html", "/copyright.html", "/explore/"]

    for path in static_paths:
        url = ET.SubElement(root, "url")
        loc = ET.SubElement(url, "loc")
        loc.text = f"{site_url}{path}"

    for entry in entries:
        url = ET.SubElement(root, "url")
        loc = ET.SubElement(url, "loc")
        loc.text = f"{site_url}{build_entry_href(entry)}"
    sitemap_path = output_root / "sitemap.xml"
    sitemap_path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")


def write_robots_txt(output_root, site_url):
    robots_path = output_root / "robots.txt"
    robots_path.write_text(f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")


def write_routes_manifest(entries, output_root):
    routes = {
        entry["mmdd"]: build_entry_href(entry)
        for entry in entries
    }
    (output_root / "data").mkdir(parents=True, exist_ok=True)
    routes_path = output_root / "data" / "routes.json"
    routes_path.write_text(json.dumps(routes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_site(entries, esv_cache, output_root, site_url, topic_taxonomy=None, entry_topics=None):
    site_url = normalize_site_url(site_url)
    validate_entries(entries)
    search_index = build_search_index(entries, esv_cache)
    output_root.mkdir(parents=True, exist_ok=True)
    entries_dir = output_root / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)
    topic_taxonomy = topic_taxonomy or {"topics": []}
    entry_topics = entry_topics or {}
    topic_map = build_topic_map(topic_taxonomy)

    for index, entry in enumerate(entries):
        slug = slugify_entry(entry)
        entry_dir = entries_dir / slug
        entry_dir.mkdir(parents=True, exist_ok=True)
        previous_entry = entries[index - 1] if index > 0 else entries[-1]
        next_entry = entries[index + 1] if index + 1 < len(entries) else entries[0]
        esv_text = esv_cache.get(entry["mmdd"], {}).get("text", "")
        html = render_entry_page(entry, previous_entry, next_entry, esv_text, site_url, topic_map=topic_map, assignment=entry_topics.get(entry["mmdd"]))
        (entry_dir / "index.html").write_text(html, encoding="utf-8")

    explore_dir = output_root / "explore"
    explore_dir.mkdir(parents=True, exist_ok=True)
    payload = build_explore_payload(entries, entry_topics, topic_taxonomy)
    (explore_dir / "index.html").write_text(render_explore_page(topic_taxonomy, payload, site_url), encoding="utf-8")

    write_sitemap(entries, output_root, site_url, topic_taxonomy=topic_taxonomy)
    write_robots_txt(output_root, site_url)
    write_routes_manifest(entries, output_root)
    (output_root / "data" / "search-index.json").write_text(
        json.dumps(search_index, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def main():
    entries = load_json(ENTRIES_PATH)
    esv_cache = load_json(ESV_CACHE_PATH)
    topic_taxonomy = load_json(ROOT / "data" / "topic_taxonomy.json")
    entry_topics = load_json(ROOT / "data" / "entry_topics.json")
    generate_site(entries, esv_cache, OUTPUT_ROOT, SITE_URL, topic_taxonomy=topic_taxonomy, entry_topics=entry_topics)


if __name__ == "__main__":
    main()
