from copy import deepcopy
from html import escape
from pathlib import Path
import json
import os
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.audit_topics import validate
from tools.generate_entry_pages import ROOT, build_explore_payload, generate_site
from tools import tag_entries_openai as tagger


class TopicPolicyTests(unittest.TestCase):
    def test_committed_explore_matches_approved_assignments(self):
        entries = json.loads((ROOT / "data/entries.json").read_text())
        taxonomy = json.loads((ROOT / "data/topic_taxonomy.json").read_text())
        assignments = json.loads((ROOT / "data/entry_topics.json").read_text())
        validate(taxonomy, assignments, entries)
        html = (ROOT / "explore/index.html").read_text()
        payload = re.search(r'<script type="application/json" id="explore-data">(.*?)</script>', html, re.S)
        self.assertIsNotNone(payload)
        self.assertEqual(json.loads(payload.group(1)), build_explore_payload(entries, assignments, taxonomy))
        names = {record["slug"]: record["name"] for record in taxonomy["topics"]}
        for entry in entries:
            path = ROOT / "entries" / f"{entry['display_date'].lower().replace(' ', '-')}/index.html"
            chips = re.findall(r'href="/explore/\?topic=([^"]+)">([^<]+)</a>', path.read_text())
            expected = [(slug, escape(names[slug])) for slug in assignments[entry["mmdd"]]["topics"]]
            self.assertEqual(chips, expected, entry["mmdd"])
        slugs = {record["slug"] for records in taxonomy.values() for record in records}
        legacy = json.loads((ROOT / "data/legacy_tag_suggestions.json").read_text())
        for choices in legacy.values():
            self.assertTrue(choices)
            self.assertTrue(set(choices) <= slugs)

    def setUp(self):
        self.taxonomy = {
            "topics": [{"slug": "a", "name": "Adoption"}, {"slug": "b", "name": "Prayer"}],
            "reader_needs": [{"slug": "fear", "name": "Fearing Death"}],
        }
        self.entries = [
            {"mmdd": f"01{day:02}", "month": 1, "day": day,
             "display_date": f"January {day}", "title": "Reading", "bible_verse": "Verse",
             "verse_ref": "John 3:16", "poem": "Poem"}
            for day in range(1, 31)
        ]
        self.assignments = {
            entry["mmdd"]: {
                "primary_topic": "a" if index < 15 else "b",
                "topics": ["a" if index < 15 else "b"],
                "reader_needs": ["fear"] if index == 0 else [],
            }
            for index, entry in enumerate(self.entries)
        }

    def test_secondary_members_count_toward_25_reading_limit(self):
        for day in range(16, 26):
            self.assignments[f"01{day:02}"]["topics"].append("a")
        self.assertEqual(validate(self.taxonomy, self.assignments, self.entries)["topic_counts"]["a"], 25)
        self.assignments["0126"]["topics"].append("a")
        with self.assertRaisesRegex(ValueError, "a has 26 passages"):
            validate(self.taxonomy, self.assignments, self.entries)

    def test_reader_needs_have_the_same_limit(self):
        for entry in self.entries[:25]:
            self.assignments[entry["mmdd"]]["reader_needs"] = ["fear"]
        validate(self.taxonomy, self.assignments, self.entries)
        self.assignments["0126"]["reader_needs"] = ["fear"]
        with self.assertRaisesRegex(ValueError, "fear has 26 passages"):
            validate(self.taxonomy, self.assignments, self.entries)

    def test_long_names_fail_in_either_facet(self):
        for facet in ("topics", "reader_needs"):
            with self.subTest(facet=facet):
                taxonomy = deepcopy(self.taxonomy)
                taxonomy[facet][0]["name"] = "A Four Word Name"
                with self.assertRaisesRegex(ValueError, "3-word maximum"):
                    validate(taxonomy, self.assignments, self.entries)

    def test_generation_rejects_overbroad_primary_before_writing(self):
        for entry in self.entries[:26]:
            self.assignments[entry["mmdd"]]["primary_topic"] = "a"
            self.assignments[entry["mmdd"]]["topics"] = ["a"]
        with TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            with self.assertRaisesRegex(ValueError, "a has 26 passages"):
                generate_site(self.entries, {}, output, "https://example.test",
                              self.taxonomy, self.assignments)
            self.assertFalse(output.exists())

    def test_missing_and_unknown_assignments_fail(self):
        missing = deepcopy(self.assignments)
        del missing["0101"]
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            validate(self.taxonomy, missing, self.entries)
        self.assignments["0101"]["topics"].append("unknown")
        with self.assertRaisesRegex(ValueError, "unknown or misplaced"):
            validate(self.taxonomy, self.assignments, self.entries)

    def test_rejected_tagging_batch_preserves_approved_file(self):
        for entry in self.entries[:25]:
            self.assignments[entry["mmdd"]].update(primary_topic="a", topics=["a"])
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                "ENTRIES_PATH": root / "entries.json",
                "TOPIC_TAXONOMY_PATH": root / "taxonomy.json",
                "ENTRY_TOPICS_PATH": root / "approved.json",
                "CACHE_PATH": root / "cache.json",
            }
            paths["ENTRIES_PATH"].write_text(json.dumps(self.entries))
            paths["TOPIC_TAXONOMY_PATH"].write_text(json.dumps(self.taxonomy))
            approved = json.dumps(self.assignments)
            paths["ENTRY_TOPICS_PATH"].write_text(approved)
            response = {"primary_topic": "a", "topics": ["a"], "reader_needs": []}
            with patch.multiple(tagger, **paths), \
                    patch.object(tagger, "fetch_assignment", return_value={}), \
                    patch.object(tagger, "parse_assignment_response", return_value=response), \
                    patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
                with self.assertRaisesRegex(ValueError, "a has 26 passages"):
                    tagger.main(["--entry", "0130"])
            self.assertEqual(paths["ENTRY_TOPICS_PATH"].read_text(), approved)
            self.assertEqual(json.loads(paths["CACHE_PATH"].read_text())["0130"]["primary_topic"], "a")
