from __future__ import annotations

from html import escape
import json
from pathlib import Path
from xml.etree import ElementTree as ET


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


def build_description(entry):
    title = entry["title"].strip()
    date_text = entry["display_date"].strip()
    verse_ref = entry["verse_ref"].strip()
    bible_verse = entry["bible_verse"].strip()
    excerpt = bible_verse if len(bible_verse) <= 80 else f"{bible_verse[:77].rstrip()}..."
    return f"{date_text}: {title}. {verse_ref}. {excerpt}"


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


def render_entry_page(entry, previous_entry, next_entry, esv_text, site_url):
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
    {prev_head_link}
    {next_head_link}
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;500;600&family=Newsreader:wght@400;500;600&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="../../style.css?v=20260519b" />
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
          <nav class="site-nav" aria-label="Primary">
            <a href="../../index.html">Devotional</a>
            <a href="../../about.html">About</a>
          </nav>
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


def write_sitemap(entries, output_root, site_url):
    root = ET.Element("urlset", attrib={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"})
    static_paths = ["/", "/about.html", "/copyright.html"]

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


def generate_site(entries, esv_cache, output_root, site_url):
    validate_entries(entries)
    output_root.mkdir(parents=True, exist_ok=True)
    entries_dir = output_root / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)

    for index, entry in enumerate(entries):
        slug = slugify_entry(entry)
        entry_dir = entries_dir / slug
        entry_dir.mkdir(parents=True, exist_ok=True)
        previous_entry = entries[index - 1] if index > 0 else entries[-1]
        next_entry = entries[index + 1] if index + 1 < len(entries) else entries[0]
        esv_text = esv_cache.get(entry["mmdd"], {}).get("text", "")
        html = render_entry_page(entry, previous_entry, next_entry, esv_text, site_url)
        (entry_dir / "index.html").write_text(html, encoding="utf-8")

    write_sitemap(entries, output_root, site_url)
    write_robots_txt(output_root, site_url)
    write_routes_manifest(entries, output_root)


def main():
    entries = load_json(ENTRIES_PATH)
    esv_cache = load_json(ESV_CACHE_PATH)
    generate_site(entries, esv_cache, OUTPUT_ROOT, SITE_URL)


if __name__ == "__main__":
    main()
