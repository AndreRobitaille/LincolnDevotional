from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.generate_entry_pages import (
    build_description,
    build_entry_href,
    generate_site,
    slugify_entry,
)


def assert_in_order(test_case, html, fragments):
    current_index = -1
    for fragment in fragments:
        next_index = html.index(fragment)
        test_case.assertGreater(next_index, current_index)
        current_index = next_index


class GenerateEntryPagesTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            {
                "mmdd": "0101",
                "month": 1,
                "day": 1,
                "display_date": "January 1",
                "title": "The Believer the Object of Divine Love",
                "bible_verse": "In this was manifested the love of God toward us.",
                "verse_ref": "1 John 4:9",
                "poem": "Pause, my soul, adore and wonder,\nThanks, eternal thanks to thee.",
            },
            {
                "mmdd": "0102",
                "month": 1,
                "day": 2,
                "display_date": "January 2",
                "title": "Redeemed by the Blood of Christ",
                "bible_verse": "Forasmuch as ye know that ye were not redeemed.",
                "verse_ref": "1 Peter 1:18-19",
                "poem": "Our sins and griefs on him were laid;",
            },
        ]
        self.esv_cache = {
            "0101": {"text": "In this the love of God was made manifest among us."}
        }

    def test_slugify_entry_uses_human_readable_month_day(self):
        self.assertEqual(slugify_entry(self.entries[0]), "january-1")

    def test_build_entry_href_uses_entries_directory(self):
        self.assertEqual(build_entry_href(self.entries[0]), "/entries/january-1/")

    def test_build_description_prefers_title_and_reference(self):
        description = build_description(self.entries[0])
        self.assertIn("January 1", description)
        self.assertIn("The Believer the Object of Divine Love", description)
        self.assertIn("1 John 4:9", description)
        self.assertIn("In this was manifested the love of God toward us.", description)

    def test_build_description_differs_between_entries(self):
        self.assertNotEqual(build_description(self.entries[0]), build_description(self.entries[1]))

    def test_generate_site_writes_entry_pages_sitemap_and_robots(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(self.entries, self.esv_cache, output_root, "https://lincolndevotional.com")

            january_page = output_root / "entries" / "january-1" / "index.html"
            sitemap = output_root / "sitemap.xml"
            robots = output_root / "robots.txt"

            self.assertTrue(january_page.exists())
            self.assertTrue(sitemap.exists())
            self.assertTrue(robots.exists())

            html = january_page.read_text()
            self.assertIn('<link rel="canonical" href="https://lincolndevotional.com/entries/january-1/" />', html)
            self.assertIn("The Believer the Object of Divine Love", html)
            self.assertIn("In this the love of God was made manifest among us.", html)
            self.assertIn('href="/entries/january-2/"', html)
            self.assertIn('<nav class="entry-nav" aria-label="Entry navigation">', html)
            self.assertLess(html.index('<nav class="entry-nav" aria-label="Entry navigation">'), html.index('<article class="entry-card" aria-live="polite">'))
            self.assertIn('href="/entries/january-2/"', html)
            assert_in_order(
                self,
                html,
                [
                    '&larr; Previous</a>',
                    'class="date-picker-wrap"',
                    'Next &rarr;</a>',
                ],
            )

            sitemap_xml = sitemap.read_text()
            self.assertIn("https://lincolndevotional.com/", sitemap_xml)
            self.assertIn("https://lincolndevotional.com/about.html", sitemap_xml)
            self.assertIn("https://lincolndevotional.com/copyright.html", sitemap_xml)

    def test_generate_site_omits_esv_block_when_cache_missing(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(self.entries, {}, output_root, "https://lincolndevotional.com")

            html = (output_root / "entries" / "january-2" / "index.html").read_text()
            self.assertNotIn("<span class=\"version-label\">ESV</span>", html)

    def test_generate_site_adds_date_picker_to_static_navigation(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(self.entries, self.esv_cache, output_root, "https://lincolndevotional.com")

            html = (output_root / "entries" / "january-1" / "index.html").read_text()

            self.assertIn('<nav class="entry-nav" aria-label="Entry navigation">', html)
            self.assertIn('class="date-picker-wrap"', html)
            self.assertIn('class="date-picker-label">Jump to</span>', html)
            self.assertIn('class="current-date-display">January 1</span>', html)
            self.assertIn('type="date"', html)
            self.assertIn('data-entry-mmdd="0101"', html)
            self.assertIn('data-routes-path="../../data/routes.json"', html)
            self.assertIn('<script src="../../static-entry-nav.js?v=20260519a"></script>', html)

    def test_static_entry_nav_uses_canonical_leap_year_and_display_title(self):
        script = Path("static-entry-nav.js").read_text()
        self.assertIn("const year = 2024;", script)
        self.assertIn('currentDateDisplay.title = `Current page date: ${currentDateDisplay.textContent}`;', script)

    def test_generate_site_raises_for_duplicate_slug(self):
        duplicate_entries = [
            dict(self.entries[0]),
            dict(self.entries[0], mmdd="0201"),
        ]
        with TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                generate_site(duplicate_entries, self.esv_cache, Path(tmp_dir), "https://lincolndevotional.com")

    def test_generate_site_wraps_navigation_on_ends(self):
        wrap_entries = [
            {
                "mmdd": "0101",
                "month": 1,
                "day": 1,
                "display_date": "January 1",
                "title": "First",
                "bible_verse": "Verse one.",
                "verse_ref": "Ref 1",
                "poem": "Poem one.",
            },
            {
                "mmdd": "1231",
                "month": 12,
                "day": 31,
                "display_date": "December 31",
                "title": "Last",
                "bible_verse": "Verse last.",
                "verse_ref": "Ref 2",
                "poem": "Poem two.",
            },
        ]
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(wrap_entries, {}, output_root, "https://lincolndevotional.com")

            first_html = (output_root / "entries" / "january-1" / "index.html").read_text()
            last_html = (output_root / "entries" / "december-31" / "index.html").read_text()

            self.assertIn('href="/entries/december-31/"', first_html)
            self.assertIn('href="/entries/january-1/"', last_html)
            self.assertIn('href="/entries/january-1/"', last_html)


if __name__ == "__main__":
    unittest.main()
