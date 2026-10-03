from html.parser import HTMLParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.generate_entry_pages import (
    ROOT,
    build_description,
    build_entry_href,
    build_search_index,
    generate_site,
    slugify_entry,
)
from tools.esv_limits import expand_reference, load_kjv_verse_counts, validate_esv_cache


def assert_in_order(test_case, html, fragments):
    current_index = -1
    for fragment in fragments:
        next_index = html.index(fragment)
        test_case.assertGreater(next_index, current_index)
        current_index = next_index


class ExploreLinksParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.months = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href", "").startswith("/entries/"):
            self.links.append(attrs["href"])
        if tag == "section" and attrs.get("class") == "explore-month":
            self.months += 1


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
            "0101": {"ref": "1 John 4:9", "text": "In this the love of God was made manifest among us."}
        }
        self.topic_taxonomy = {
            "topics": [
                {
                    "slug": "comfort",
                    "name": "Comfort",
                    "group": "need",
                    "description": "For seasons of sorrow, inward distress, and the need for consolation.",
                    "related": ["peace", "prayer"],
                },
                {
                    "slug": "peace",
                    "name": "Peace",
                    "group": "need",
                    "description": "For resting in God when the mind is troubled.",
                    "related": ["comfort", "prayer"],
                },
                {
                    "slug": "prayer",
                    "name": "Prayer",
                    "group": "christian-life",
                    "description": "For communion with God through asking, thanksgiving, and dependence.",
                    "related": ["comfort", "peace"],
                },
            ],
            "reader_needs": [
                {"slug": "comfort", "name": "Comfort", "description": "For grief and loss."},
                {"slug": "hope", "name": "Hope", "description": "For discouragement."},
            ],
        }
        self.entry_topics = {
            "0101": {
                "primary_topic": "comfort",
                "topics": ["comfort", "peace"],
                "reader_needs": ["comfort"],
            },
            "0102": {
                "primary_topic": "prayer",
                "topics": ["prayer"],
                "reader_needs": [],
            },
        }

    def test_slugify_entry_uses_human_readable_month_day(self):
        self.assertEqual(slugify_entry(self.entries[0]), "january-1")

    def test_build_entry_href_uses_entries_directory(self):
        self.assertEqual(build_entry_href(self.entries[0]), "/entries/january-1/")

    def test_search_index_contains_source_text_and_uses_only_cached_esv(self):
        entries = [dict(self.entries[0], esv="Untrusted translation"), self.entries[1]]
        index = build_search_index(entries, self.esv_cache)
        self.assertEqual(index[0], {
            "mmdd": "0101",
            "display_date": "January 1",
            "title": self.entries[0]["title"],
            "href": "/entries/january-1/",
            "verse_ref": "1 John 4:9",
            "devotional": self.entries[0]["poem"],
            "kjv": self.entries[0]["bible_verse"],
            "esv": self.esv_cache["0101"]["text"],
        })
        self.assertEqual(index[1]["esv"], "")

    def test_generate_site_writes_search_index_under_deployed_data_directory(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(self.entries, self.esv_cache, output_root, "https://example.test")
            index = json.loads((output_root / "data" / "search-index.json").read_text())
            self.assertEqual(index, build_search_index(self.entries, self.esv_cache))

    def test_generate_site_rejects_unsafe_cache_before_writing_any_files(self):
        cache = {"0101": {"ref": "Jude 1-13", "text": "Too much of one book"}}
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir) / "site"
            with self.assertRaisesRegex(ValueError, "maximum is half"):
                generate_site(self.entries, cache, output_root, "https://example.test")
            self.assertFalse(output_root.exists())

    def test_committed_search_index_is_current_and_static_links_cover_all_366_entries(self):
        entries = json.loads((ROOT / "data" / "entries.json").read_text())
        cache = json.loads((ROOT / "data" / "esv_cache.json").read_text())
        index = json.loads((ROOT / "data" / "search-index.json").read_text())
        self.assertEqual(index, build_search_index(entries, cache))
        self.assertEqual(len(index), 366)
        self.assertEqual(len({record["mmdd"] for record in index}), 366)
        self.assertIn("0229", {record["mmdd"] for record in index})
        parser = ExploreLinksParser()
        parser.feed((ROOT / "explore" / "index.html").read_text())
        self.assertEqual(parser.links, [entry["href"] for entry in index])

    def test_build_description_prefers_title_and_reference(self):
        description = build_description(self.entries[0])
        self.assertIn("January 1", description)
        self.assertIn("The Believer the Object of Divine Love", description)
        self.assertIn("1 John 4:9", description)
        self.assertIn("In this was manifested the love of God toward us.", description)

    def test_build_description_differs_between_entries(self):
        self.assertNotEqual(build_description(self.entries[0]), build_description(self.entries[1]))

    def test_build_description_truncates_at_word_boundary(self):
        entry = dict(self.entries[0])
        entry["bible_verse"] = (
            "This verse contains many carefully chosen words to push the excerpt "
            "near the truncation point while preserving a word boundary stewardship "
            "boundarybreakingword plus enough additional language to ensure "
            "the full generated description exceeds the maximum length limit."
        )

        description = build_description(entry)

        self.assertLessEqual(len(description), 160)
        self.assertTrue(description.endswith("..."))
        self.assertNotIn("....", description)
        self.assertNotIn("boundarybreakingword", description)
        self.assertEqual(description[:-3].split()[-1], "point")

    def test_build_description_trims_trailing_punctuation_before_ellipsis(self):
        entry = dict(self.entries[0])
        entry["bible_verse"] = (
            "This verse ends with punctuation that should not become awkward when the "
            "description is truncated at the boundary before the generated ellipsis."
        )

        description = build_description(entry)

        self.assertTrue(description.endswith("..."))
        self.assertNotIn("....", description)
        self.assertNotRegex(description, r"[.,;:-]\.{3}$")

    def test_build_description_truncates_long_prefix_to_160_chars(self):
        entry = dict(self.entries[0])
        entry["title"] = "A" * 120
        entry["verse_ref"] = "B" * 60
        entry["bible_verse"] = "Short verse text."

        description = build_description(entry)

        self.assertLessEqual(len(description), 160)
        self.assertTrue(description.endswith("..."))
        self.assertNotIn("....", description)

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
            self.assertIn('aria-current="page"', html)
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

    def test_generate_site_writes_explore_browse_page_with_inlined_data(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(
                self.entries,
                self.esv_cache,
                output_root,
                "https://lincolndevotional.com",
                topic_taxonomy=self.topic_taxonomy,
                entry_topics=self.entry_topics,
            )

            explore_page = output_root / "explore" / "index.html"
            entry_page = output_root / "entries" / "january-1" / "index.html"

            self.assertTrue(explore_page.exists())
            # Topic drill-down subpages no longer exist — browse is single-page.
            self.assertFalse((output_root / "explore" / "comfort").exists())

            explore_html = explore_page.read_text()
            entry_html = entry_page.read_text()

            # Page chrome
            self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1" />', explore_html)
            self.assertIn('<nav class="site-nav" aria-label="Primary">', explore_html)
            self.assertIn('Dark mode', explore_html)
            self.assertIn('<footer class="site-footer">', explore_html)
            self.assertNotIn('static-entry-nav.js', explore_html)
            self.assertNotIn('permalink.js', explore_html)
            self.assertIn('<script src="../theme.js?v=20260123"></script>', explore_html)
            self.assertIn('<script src="../explore.js', explore_html)

            # New browse UI elements
            self.assertIn("Find a devotion for today’s need", explore_html)
            self.assertIn('class="explore-filters"', explore_html)
            self.assertIn('data-facet-group="topic"', explore_html)
            self.assertIn('data-facet-group="need"', explore_html)
            self.assertIn('data-explore-results', explore_html)
            self.assertIn('data-result-count', explore_html)
            self.assertIn('id="explore-data"', explore_html)

            # Topic and need chips render
            self.assertIn('data-facet="topic"', explore_html)
            self.assertIn('data-slug="comfort"', explore_html)
            self.assertIn('data-facet="need"', explore_html)

            # Entry-page chips link to the canonical filtered URL
            self.assertIn('class="entry-topic-chips"', entry_html)
            self.assertIn('href="/explore/?topic=comfort"', entry_html)
            self.assertIn('href="/explore/?topic=peace"', entry_html)
            # Primary topic chip has the primary modifier
            self.assertIn('class="topic-chip topic-chip--primary" href="/explore/?topic=comfort"', entry_html)

    def test_explore_contains_static_entry_links_by_month_including_leap_day(self):
        leap_day = dict(
            self.entries[0],
            mmdd="0229", month=2, day=29, display_date="February 29",
            title='Faith < hope & "love"',
        )
        entries = self.entries + [leap_day]
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(entries, self.esv_cache, output_root, "https://lincolndevotional.com")
            html = (output_root / "explore" / "index.html").read_text()

        parser = ExploreLinksParser()
        parser.feed(html)
        self.assertEqual(parser.links, [build_entry_href(entry) for entry in entries])
        self.assertEqual(len(set(parser.links)), len(entries))
        self.assertEqual(parser.months, 2)
        self.assertIn('Faith &lt; hope &amp; &quot;love&quot;', html)
        self.assertIn('2 devotions</span>', html)
        self.assertIn('1 devotion</span>', html)
        self.assertNotIn('Loading devotions', html)
        assert_in_order(self, html, ['January</h3>', 'February</h3>'])

    def test_generate_site_adds_common_social_metadata_to_entries_and_explore(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(
                self.entries,
                self.esv_cache,
                output_root,
                "https://lincolndevotional.com",
                topic_taxonomy=self.topic_taxonomy,
                entry_topics=self.entry_topics,
            )

            entry_html = (output_root / "entries" / "january-1" / "index.html").read_text()
            explore_html = (output_root / "explore" / "index.html").read_text()

            for html in (entry_html, explore_html):
                self.assertIn('<meta property="og:type" content="website" />', html)
                self.assertIn('<meta property="og:site_name" content="The Believer\'s Daily Treasure" />', html)
                self.assertIn('<meta name="twitter:card" content="summary" />', html)
                self.assertNotIn('twitter:site', html)

    def test_generate_site_normalizes_trailing_slash_site_url_for_canonical_urls(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            custom_site_url = "https://example.test"
            generate_site(
                self.entries,
                self.esv_cache,
                output_root,
                custom_site_url,
                topic_taxonomy=self.topic_taxonomy,
                entry_topics=self.entry_topics,
            )

            entry_html = (output_root / "entries" / "january-1" / "index.html").read_text()
            explore_html = (output_root / "explore" / "index.html").read_text()

            for html in (entry_html, explore_html):
                self.assertNotIn('https://example.test//', html)

            self.assertIn('<link rel="canonical" href="https://example.test/entries/january-1/" />', entry_html)
            self.assertIn('<link rel="canonical" href="https://example.test/explore/" />', explore_html)

    def test_generate_site_normalizes_trailing_slash_site_url(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            custom_site_url = "https://example.test/"
            generate_site(
                self.entries,
                self.esv_cache,
                output_root,
                custom_site_url,
                topic_taxonomy=self.topic_taxonomy,
                entry_topics=self.entry_topics,
            )

            entry_html = (output_root / "entries" / "january-1" / "index.html").read_text()
            explore_html = (output_root / "explore" / "index.html").read_text()
            sitemap_xml = (output_root / "sitemap.xml").read_text()
            robots_txt = (output_root / "robots.txt").read_text()

            for html in (entry_html, explore_html):
                self.assertIn('<meta property="og:url" content="https://example.test', html)
                self.assertNotIn('https://example.test//', html)

            self.assertNotIn('https://example.test//', sitemap_xml)
            self.assertIn('Sitemap: https://example.test/sitemap.xml', robots_txt)

    def test_generate_site_omits_topic_subpages_from_sitemap(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(
                self.entries,
                self.esv_cache,
                output_root,
                "https://lincolndevotional.com",
                topic_taxonomy=self.topic_taxonomy,
                entry_topics=self.entry_topics,
            )

            sitemap_xml = (output_root / "sitemap.xml").read_text()

            self.assertIn("https://lincolndevotional.com/explore/", sitemap_xml)
            self.assertNotIn("https://lincolndevotional.com/explore/comfort/", sitemap_xml)
            self.assertNotIn("https://lincolndevotional.com/explore/prayer/", sitemap_xml)

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

    def test_static_entry_permalink_avoids_share_filter_terms(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(self.entries, self.esv_cache, output_root, "https://lincolndevotional.com")

            html = (output_root / "entries" / "january-1" / "index.html").read_text()

            self.assertIn('class="entry-permalink"', html)
            self.assertIn('id="devotionLinkArea"', html)
            self.assertIn('id="devotionLink"', html)
            self.assertIn('Share this devotion', html)
            self.assertIn('<script src="../../permalink.js?v=20260519a"></script>', html)
            self.assertNotIn('entry-share', html)
            self.assertNotIn('share.js', html)

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


class EsvLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verse_counts = load_kjv_verse_counts()

    def test_kjv_reader_counts_verse_records_including_chapter_and_book_ends(self):
        self.assertEqual(len(self.verse_counts), 66)
        self.assertEqual(sum(sum(chapters.values()) for chapters in self.verse_counts.values()), 31102)
        self.assertEqual(self.verse_counts["Gen"][1], 31)
        self.assertEqual(self.verse_counts["Ps"][119], 176)
        self.assertEqual(sum(self.verse_counts["1John"].values()), 105)
        self.assertEqual(self.verse_counts["Jude"], {1: 25})

    def test_reference_expansion_handles_ranges_lists_and_single_chapter_books(self):
        examples = {
            "1 Peter 1:18-19": [("1Pet", 1, 18), ("1Pet", 1, 19)],
            "1 John 3:19, 21": [("1John", 3, 19), ("1John", 3, 21)],
            "2 Corinthians 5:6,8": [("2Cor", 5, 6), ("2Cor", 5, 8)],
            "Jude 21": [("Jude", 1, 21)],
            "Jude 3–4": [("Jude", 1, 3), ("Jude", 1, 4)],
            "Genesis 1:31-2:2": [("Gen", 1, 31), ("Gen", 2, 1), ("Gen", 2, 2)],
            "Romans 8:1; 8:5": [("Rom", 8, 1), ("Rom", 8, 5)],
        }
        for reference, expected in examples.items():
            with self.subTest(reference=reference):
                self.assertEqual(expand_reference(reference, self.verse_counts), expected)

    def test_rejects_missing_unknown_and_invalid_references_instead_of_undercounting(self):
        for reference in (None, "", "Unknown 1:1", "Romans 8", "Romans 99:1", "Jude 26", "Jude 0", "Jude 4-2", "John 3:1,", "John 3:1, 3:99"):
            with self.subTest(reference=reference):
                with self.assertRaises(ValueError):
                    validate_esv_cache({"entry": {"ref": reference}}, self.verse_counts)

    def test_accepts_500_occurrences_and_rejects_501_even_when_verses_repeat(self):
        cache = {str(i): {"ref": "Genesis 1:1"} for i in range(500)}
        self.assertEqual(validate_esv_cache(cache, self.verse_counts), 500)
        cache["extra"] = {"ref": "Genesis 1:2"}
        with self.assertRaisesRegex(ValueError, "501 verses; maximum is 500"):
            validate_esv_cache(cache, self.verse_counts)

    def test_accepts_exactly_half_a_book_and_rejects_more_than_half(self):
        self.assertEqual(validate_esv_cache({"entry": {"ref": "3 John 1-7"}}, self.verse_counts), 7)
        for reference in ("3 John 1-8", "2 John 1-7", "Jude 1-13"):
            with self.subTest(reference=reference):
                with self.assertRaisesRegex(ValueError, "maximum is half"):
                    validate_esv_cache({"entry": {"ref": reference}}, self.verse_counts)

    def test_cache_limits_cover_records_outside_the_devotional_index(self):
        cache = {"unused": {"ref": "2 John 1-7"}}
        with self.assertRaisesRegex(ValueError, "maximum is half"):
            build_search_index([], cache)

    def test_real_committed_esv_cache_stays_within_both_limits(self):
        cache = json.loads((ROOT / "data" / "esv_cache.json").read_text())
        self.assertGreater(validate_esv_cache(cache, self.verse_counts), 0)

    def test_deploy_runs_the_test_command_before_ftps_and_requires_success(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
        command = "run: python3 -m unittest tests.test_generate_entry_pages tests.test_tag_entries_openai"
        self.assertLess(workflow.index(command), workflow.index("uses: SamKirkland/FTP-Deploy-Action"))
        self.assertIn("if: ${{ success() && github.event_name != 'pull_request' }}", workflow)
        self.assertNotIn("continue-on-error", workflow)


if __name__ == "__main__":
    unittest.main()
