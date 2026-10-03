from collections import Counter
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import urlparse

from PIL import Image

from tools.generate_entry_pages import SITE_URL, build_description, build_entry_href
from tools.generate_share_images import (
    INKS, MIN_FONT_SIZE, PAPER, TEXT_BOTTOM, TEXT_LEFT, TEXT_RIGHT, TEXT_TOP,
    choose_layout, digest, generate, image_jobs, inputs_fingerprint,
)
from tools.social_meta import (
    HEIGHT, IMAGE_DIRECTORY, ROOT, WIDTH, build_share_title, image_filename,
    load_headlines, refresh_static_share_meta, validate_headlines,
)


class HeadParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.meta = {}
        self.counts = Counter()
        self.canonical = None
        self.feed(html.split("</head>", 1)[0])

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = attrs.get("property", attrs.get("name"))
            self.meta[key] = attrs.get("content", "")
            self.counts[key] += 1
        elif tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs["href"]


def luminance(hex_color):
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in channels]
    return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))


class ShareImagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = json.loads((ROOT / "data/entries.json").read_text())
        cls.headlines = load_headlines()
        cls.manifest = json.loads((ROOT / IMAGE_DIRECTORY / "manifest.json").read_text())

    def test_reviewed_headlines_cover_every_date_including_leap_day(self):
        self.assertEqual(len(self.entries), 366)
        self.assertEqual(len(self.headlines), 366)
        self.assertIn("0229", self.headlines)
        validate_headlines(self.entries, self.headlines)

    def test_source_edits_require_editorial_review_before_generation(self):
        for field in ("title", "verse_ref", "bible_verse", "poem"):
            with self.subTest(field=field):
                entries = deepcopy(self.entries)
                entries[0][field] += " changed"
                with self.assertRaisesRegex(ValueError, "Review the share headline"):
                    validate_headlines(entries, self.headlines)

    def test_missing_extra_and_blank_headlines_fail(self):
        for change in ("missing", "extra", "blank"):
            with self.subTest(change=change):
                headlines = deepcopy(self.headlines)
                if change == "missing":
                    del headlines["0229"]
                elif change == "extra":
                    headlines["0230"] = headlines["0229"]
                else:
                    headlines["0229"]["headline"] = " "
                with self.assertRaises(ValueError):
                    validate_headlines(self.entries, headlines)

    def test_headlines_preserve_negation_and_theological_distinctions(self):
        labels = {key: record["headline"] for key, record in self.headlines.items()}
        self.assertIn("Does Not Tempt to Sin", labels["0902"])
        self.assertIn("from Temptation", labels["0923"])
        self.assertIn("in Temptation", labels["0924"])
        self.assertIn("Ever", labels["1123"])
        self.assertNotIn("Ever", labels["1122"])
        self.assertIn("Prays for", labels["0928"])
        self.assertIn("Judge the World", labels["1118"])
        for key, qualification in (("0402", "Glory"), ("0403", "Like Christ"),
                                   ("0404", "Grace"), ("0405", "Name")):
            self.assertIn(qualification, labels[key])
        self.assertIn("Past Mercies", labels["0830"])
        self.assertIn("Affliction", labels["0830"])

    def test_all_headlines_fit_at_large_type_without_square_crop_loss(self):
        for key, _, headline, _, _ in image_jobs(self.entries, self.headlines):
            with self.subTest(date=key, headline=headline):
                size, lines, boxes, advance, height = choose_layout(headline)
                self.assertGreaterEqual(size, MIN_FONT_SIZE)
                self.assertLessEqual(len(lines), 3)
                self.assertLessEqual(height, TEXT_BOTTOM - TEXT_TOP)
                for index, box in enumerate(boxes):
                    self.assertLessEqual(box[2] - box[0], TEXT_RIGHT - TEXT_LEFT)
                    self.assertLessEqual(index * advance + box[3] - box[1], height)
                # All title text stays inside a centered 630px square crop.
                self.assertGreaterEqual(TEXT_LEFT, (WIDTH - HEIGHT) // 2)
                self.assertLessEqual(TEXT_RIGHT, (WIDTH + HEIGHT) // 2)

    def test_palette_has_strong_text_contrast(self):
        for ink in INKS:
            contrast = (luminance(PAPER) + .05) / (luminance(ink) + .05)
            self.assertGreater(contrast, 11)

    def test_manifest_and_every_committed_png_are_complete_and_intact(self):
        directory = ROOT / IMAGE_DIRECTORY
        self.assertEqual(self.manifest["inputs_sha256"], inputs_fingerprint())
        jobs = list(image_jobs(self.entries, self.headlines))
        self.assertEqual(len(jobs), 367)
        expected_files = set()
        for key, entry, headline, caption, _ in jobs:
            with self.subTest(date=key):
                record = self.manifest["images"][key]
                expected_files.add(image_filename(entry))
                self.assertEqual(record["file"], image_filename(entry))
                self.assertEqual(record["headline"], headline)
                self.assertEqual(record["caption"], caption)
                path = directory / record["file"]
                self.assertLess(path.stat().st_size, 5_000_000)
                self.assertEqual(digest(path.read_bytes()), record["png_sha256"])
                with Image.open(path) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertEqual(image.size, (WIDTH, HEIGHT))
                    self.assertEqual(digest(image.convert("RGB").tobytes()), record["pixels_sha256"])
                bounds = record["text_bounds"]
                for left, top, right, bottom in bounds:
                    self.assertGreaterEqual(left, TEXT_LEFT)
                    self.assertLessEqual(right, TEXT_RIGHT)
                    self.assertGreaterEqual(top, TEXT_TOP)
                    self.assertLess(bottom, HEIGHT)
                self.assertLessEqual(max(box[3] for box in bounds[:-1]), TEXT_BOTTOM)
                self.assertEqual(bounds[-1][1], 552)
        self.assertEqual(set(self.manifest["images"]), {job[0] for job in jobs})
        self.assertEqual({path.name for path in directory.glob("*.png")}, expected_files)

    def test_checker_rejects_missing_changed_and_stale_images(self):
        entries = self.entries[:1]
        headlines = {entries[0]["mmdd"]: self.headlines[entries[0]["mmdd"]]}
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            generate(entries, headlines, root)
            generate(entries, headlines, root, check=True)
            path = root / IMAGE_DIRECTORY / "january-1.png"
            original = path.read_bytes()
            path.unlink()
            with self.assertRaisesRegex(ValueError, "Missing sharing image"):
                generate(entries, headlines, root, check=True)
            path.write_bytes(original)
            with Image.open(path) as image:
                changed = image.convert("RGB")
            changed.putpixel((0, 0), (255, 0, 0))
            changed.save(path)
            with self.assertRaisesRegex(ValueError, "does not match"):
                generate(entries, headlines, root, check=True)
            path.write_bytes(original)
            with patch("tools.generate_share_images.inputs_fingerprint", return_value="changed"):
                with self.assertRaisesRegex(ValueError, "missing or stale"):
                    generate(entries, headlines, root, check=True)

    def test_every_public_page_has_consistent_crawler_visible_metadata(self):
        pages = [(ROOT / "entries" / image_filename(entry).removesuffix(".png") / "index.html", entry)
                 for entry in self.entries]
        pages += [(ROOT / name, None) for name in ("index.html", "about.html", "copyright.html", "explore/index.html")]
        for path, entry in pages:
            with self.subTest(page=str(path.relative_to(ROOT))):
                head = HeadParser(path.read_text())
                meta = head.meta
                for key in ("og:title", "og:description", "og:url", "og:type", "og:site_name", "og:locale",
                            "og:image", "og:image:type", "og:image:width", "og:image:height", "og:image:alt",
                            "twitter:card", "twitter:title", "twitter:description", "twitter:image", "twitter:image:alt"):
                    self.assertEqual(head.counts[key], 1, key)
                    self.assertTrue(meta[key], key)
                self.assertEqual(meta["og:url"], head.canonical)
                self.assertEqual(meta["og:locale"], "en_US")
                self.assertEqual(meta["og:type"], "website")
                self.assertEqual(meta["twitter:card"], "summary_large_image")
                self.assertEqual(meta["twitter:title"], meta["og:title"])
                self.assertEqual(meta["twitter:description"], meta["og:description"])
                self.assertEqual(meta["description"], meta["og:description"])
                self.assertEqual(meta["twitter:image"], meta["og:image"])
                self.assertEqual(meta["twitter:image:alt"], meta["og:image:alt"])
                self.assertIn("stovepipe hat", meta["og:image:alt"])
                self.assertEqual(meta["og:image:type"], "image/png")
                self.assertEqual(meta["og:image:width"], str(WIDTH))
                self.assertEqual(meta["og:image:height"], str(HEIGHT))
                url = urlparse(meta["og:image"])
                self.assertEqual(url.scheme, "https")
                self.assertEqual(url.netloc, "lincolndevotional.com")
                self.assertEqual(url.path, f"/{IMAGE_DIRECTORY}/{image_filename(entry)}")
                self.assertTrue((ROOT / url.path.lstrip("/")).is_file())
                if entry:
                    self.assertEqual(meta["og:title"], build_share_title(entry))
                    self.assertEqual(meta["og:description"], build_description(entry))
                    self.assertLessEqual(len(meta["og:description"]), 160)
                    self.assertEqual(head.canonical, SITE_URL + build_entry_href(entry))

    def test_general_page_metadata_refresh_is_idempotent_and_escapes_copy(self):
        with TemporaryDirectory() as temporary:
            page = Path(temporary) / "index.html"
            page.write_text((ROOT / "index.html").read_text())
            refresh_static_share_meta(page, "https://example.test/")
            first = page.read_text()
            refresh_static_share_meta(page, "https://example.test/")
            self.assertEqual(page.read_text(), first)
            self.assertEqual(HeadParser(first).meta["og:image"], f"https://example.test/{IMAGE_DIRECTORY}/site.png")
            self.assertIn("&#x27;", first)


if __name__ == "__main__":
    unittest.main()
