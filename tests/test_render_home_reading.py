from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from tools.generate_entry_pages import ROOT
from tools.render_home_reading import apply_home_reading, build_reading, main


FIXTURE_HTML = """<!doctype html>
<html lang="en">
  <head>
    <title>Lincoln's Daily Devotional: The Believer's Daily Treasure</title>
    <meta name="description" content="Keep this description." />
    <script src="script.js?v=20260519b"></script>
  </head>
  <body>
    <main class="main-content" id="devotionalContent">
      <label id="currentDisplayDate" class="current-date-display" for="datePicker"><!--home-slot:nav-date-->Loading...<!--/home-slot:nav-date--></label>
      <input type="date" id="datePicker" class="nav-date-input" />
      <p id="entryDisplayDate" class="entry-date"><!--home-slot:entry-date--><!--/home-slot:entry-date--></p>
      <h2 id="entryTitle" class="entry-title"><!--home-slot:title--><!--/home-slot:title--></h2>
      <p id="entryDevotional" class="entry-text"><!--home-slot:kjv--><!--/home-slot:kjv--></p>
      <div class="verse-block hidden" id="esvBlock">
        <p id="entryEsv" class="entry-text"><!--home-slot:esv--><!--/home-slot:esv--></p>
      </div>
      <p id="entryVerseRef" class="entry-verse-ref"><!--home-slot:verse-ref--><!--/home-slot:verse-ref--></p>
      <div id="entryPoem" class="entry-text"><!--home-slot:poem--><!--/home-slot:poem--></div>
    </main>
    <aside class="entry-permalink hidden" id="devotionLinkArea" aria-label="Share this devotion">
      <a id="devotionLink" class="entry-permalink-link" href="#">Share this devotion</a>
    </aside>
  </body>
</html>
"""

FIXTURE_SITEMAP = (
    "<urlset>"
    "<url><loc>https://lincolndevotional.com/</loc><lastmod>2026-10-03</lastmod></url>"
    "<url><loc>https://lincolndevotional.com/about.html</loc><lastmod>2026-10-07</lastmod></url>"
    "</urlset>"
)


class NodeCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = {}
        self._stack = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        element_id = attr.get("id")
        if element_id:
            self.nodes[element_id] = {"attrs": attr, "text": []}
        self._stack.append(element_id)

    def handle_endtag(self, tag):
        if self._stack:
            self._stack.pop()

    def handle_data(self, data):
        for element_id in self._stack:
            if element_id:
                self.nodes[element_id]["text"].append(data)

    def text(self, element_id):
        return "".join(self.nodes[element_id]["text"])


def fixture_data():
    entries = [
        {
            "mmdd": "1119",
            "display_date": "November 19",
            "title": 'Grace & Truth',
            "bible_verse": "Keep <the> word.",
            "verse_ref": "Jude 24",
            "poem": "Line one,\r\n\r\nLine three.",
        },
        {
            "mmdd": "0229",
            "display_date": "February 29",
            "title": "Leap Day",
            "bible_verse": "A leap verse.",
            "verse_ref": "Psalm 1:1",
            "poem": "Leap line.",
        },
    ]
    esv_cache = {"1119": {"text": 'Now "blameless" & glad.'}}
    routes = {"1119": "/entries/november-19/", "0229": "/entries/february-29/"}
    return entries, esv_cache, routes


def lastmods(sitemap):
    return re.findall(r"<loc>(.*?)</loc><lastmod>(.*?)</lastmod>", sitemap)


class RenderHomeReadingTests(unittest.TestCase):
    def test_stamp_copies_entry_text_and_only_the_home_lastmod(self):
        entries, esv_cache, routes = fixture_data()
        reading = build_reading(entries, esv_cache, routes, date(2026, 11, 19))
        stamped, sitemap = apply_home_reading(FIXTURE_HTML, FIXTURE_SITEMAP, reading)
        page = NodeCollector()
        page.feed(stamped)

        self.assertEqual(page.text("entryTitle"), entries[0]["title"])
        self.assertEqual(page.text("entryDevotional"), entries[0]["bible_verse"])
        self.assertEqual(page.text("entryEsv"), esv_cache["1119"]["text"])
        self.assertEqual(page.text("entryVerseRef"), entries[0]["verse_ref"])
        self.assertEqual(page.text("currentDisplayDate"), entries[0]["display_date"])
        self.assertEqual(page.text("entryDisplayDate"), entries[0]["display_date"])
        self.assertEqual(page.text("entryPoem"), "Line one,Line three.")
        self.assertIn('<div class="poem-line">Line one,</div>', stamped)
        self.assertIn('<div class="poem-line poem-line--blank"></div>', stamped)
        self.assertIn('<div class="poem-line">Line three.</div>', stamped)
        self.assertNotIn("hidden", page.nodes["esvBlock"]["attrs"]["class"])
        self.assertEqual(page.nodes["devotionLink"]["attrs"]["href"], "/entries/november-19/")
        self.assertEqual(page.nodes["devotionalContent"]["attrs"]["data-entry-mmdd"], "1119")
        self.assertEqual(page.nodes["datePicker"]["attrs"]["value"], "2026-11-19")
        self.assertNotIn("hidden", page.nodes["devotionLinkArea"]["attrs"]["class"])
        self.assertIn("Keep this description.", stamped)
        self.assertIn('src="script.js?v=20260519b"', stamped)
        self.assertEqual(stamped.split("</head>", 1)[0], FIXTURE_HTML.split("</head>", 1)[0])

        before = lastmods(FIXTURE_SITEMAP)
        after = lastmods(sitemap)
        self.assertEqual([loc for loc, _mod in before], [loc for loc, _mod in after])
        self.assertEqual(after[0], ("https://lincolndevotional.com/", "2026-11-19"))
        self.assertEqual(after[1], before[1])

        restamped, resitemap = apply_home_reading(stamped, sitemap, reading)
        self.assertEqual(restamped, stamped)
        self.assertEqual(resitemap, sitemap)

    def test_missing_esv_hides_the_esv_block(self):
        entries, _esv_cache, routes = fixture_data()
        reading = build_reading(entries, {}, routes, date(2026, 11, 19))
        stamped, _sitemap = apply_home_reading(FIXTURE_HTML, FIXTURE_SITEMAP, reading)
        page = NodeCollector()
        page.feed(stamped)
        self.assertIn("hidden", page.nodes["esvBlock"]["attrs"]["class"].split())
        self.assertEqual(page.text("entryEsv"), "")

    def test_leap_day_uses_the_february_29_entry(self):
        entries, esv_cache, routes = fixture_data()
        reading = build_reading(entries, esv_cache, routes, date(2024, 2, 29))
        self.assertEqual(reading.mmdd, "0229")
        self.assertEqual(reading.href, "/entries/february-29/")
        self.assertEqual(reading.bible_verse, "A leap verse.")

    def test_cli_writes_the_home_page_and_leaves_entry_pages(self):
        entries, esv_cache, routes = fixture_data()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            (data / "entries.json").write_text(json.dumps(entries), encoding="utf-8")
            (data / "esv_cache.json").write_text(json.dumps(esv_cache), encoding="utf-8")
            (data / "routes.json").write_text(json.dumps(routes), encoding="utf-8")
            (root / "index.html").write_text(FIXTURE_HTML, encoding="utf-8")
            (root / "sitemap.xml").write_text(FIXTURE_SITEMAP, encoding="utf-8")
            entry_page = root / "entries" / "january-1" / "index.html"
            entry_page.parent.mkdir(parents=True)
            entry_page.write_text("sentinel", encoding="utf-8")
            entries_bytes = (data / "entries.json").read_bytes()

            self.assertEqual(main(["--date", "2026-11-19", "--root", str(root)]), 0)
            html = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("Keep &lt;the&gt; word.", html)
            self.assertIn("/entries/november-19/", html)
            self.assertEqual(entry_page.read_text(encoding="utf-8"), "sentinel")
            self.assertEqual((data / "entries.json").read_bytes(), entries_bytes)
            self.assertIn(
                "<loc>https://lincolndevotional.com/about.html</loc><lastmod>2026-10-07</lastmod>",
                (root / "sitemap.xml").read_text(encoding="utf-8"),
            )

            self.assertEqual(main(["--date", "2026-11-19", "--root", str(root)]), 0)
            self.assertEqual((root / "index.html").read_text(encoding="utf-8"), html)

    def test_cli_rejects_a_bad_date_and_a_missing_entry(self):
        self.assertEqual(main(["--date", "2026-02-31"]), 1)
        entries, esv_cache, routes = fixture_data()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            (data / "entries.json").write_text(json.dumps(entries), encoding="utf-8")
            (data / "esv_cache.json").write_text(json.dumps(esv_cache), encoding="utf-8")
            (data / "routes.json").write_text(json.dumps(routes), encoding="utf-8")
            (root / "index.html").write_text(FIXTURE_HTML, encoding="utf-8")
            (root / "sitemap.xml").write_text(FIXTURE_SITEMAP, encoding="utf-8")
            before = (root / "index.html").read_text(encoding="utf-8")
            self.assertEqual(main(["--date", "2026-03-01", "--root", str(root)]), 1)
            self.assertEqual((root / "index.html").read_text(encoding="utf-8"), before)

    def test_repository_home_page_keeps_its_head_and_other_lastmods(self):
        entries = json.loads((ROOT / "data" / "entries.json").read_text(encoding="utf-8"))
        esv_cache = json.loads((ROOT / "data" / "esv_cache.json").read_text(encoding="utf-8"))
        routes = json.loads((ROOT / "data" / "routes.json").read_text(encoding="utf-8"))
        entry = next(item for item in entries if item["mmdd"] == "1119")
        reading = build_reading(entries, esv_cache, routes, date(2026, 11, 19))
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        stamped, stamped_sitemap = apply_home_reading(html, sitemap, reading)

        self.assertEqual(html.split("</head>", 1)[0], stamped.split("</head>", 1)[0])
        self.assertIn(entry["bible_verse"], stamped)
        self.assertIn(entry["title"], stamped)
        self.assertIn(entry["verse_ref"], stamped)
        self.assertIn(esv_cache["1119"]["text"], stamped)
        self.assertIn(routes["1119"], stamped)
        for line in entry["poem"].replace("\r\n", "\n").split("\n"):
            self.assertIn(f'<div class="poem-line">{line}</div>', stamped)

        before = lastmods(sitemap)
        after = lastmods(stamped_sitemap)
        self.assertEqual([loc for loc, _mod in before], [loc for loc, _mod in after])
        for (loc, old), (_same, new) in zip(before, after):
            if loc == "https://lincolndevotional.com/":
                self.assertEqual(new, "2026-11-19")
            else:
                self.assertEqual(old, new)

        restamped, resitemap = apply_home_reading(stamped, stamped_sitemap, reading)
        self.assertEqual(restamped, stamped)
        self.assertEqual(resitemap, stamped_sitemap)


if __name__ == "__main__":
    unittest.main()
