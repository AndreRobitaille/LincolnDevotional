import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.tag_entries_openai import (
    build_allowed_reader_needs_map,
    build_allowed_topic_map,
    build_prompt,
    fetch_assignment,
    main,
    normalize_assignment,
    parse_assignment_response,
    write_assignments,
)


class TagEntriesOpenAITests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = {
            "topics": [
                {"slug": "comfort", "name": "Comfort", "group": "need", "description": "desc", "related": ["peace"]},
                {"slug": "peace", "name": "Peace", "group": "need", "description": "desc", "related": ["comfort"]},
                {"slug": "love-of-neighbor", "name": "Love of Neighbor", "group": "christian-life", "description": "desc", "related": []},
                {"slug": "prayer", "name": "Prayer", "group": "christian-life", "description": "desc", "related": []},
            ],
            "reader_needs": [
                {"slug": "comfort", "name": "Comfort", "description": "desc"},
                {"slug": "hope", "name": "Hope", "description": "desc"},
                {"slug": "strength", "name": "Strength", "description": "desc"},
            ],
        }
        self.allowed_topics = build_allowed_topic_map(self.taxonomy)
        self.allowed_reader_needs = build_allowed_reader_needs_map(self.taxonomy)

    def test_build_allowed_topic_map_indexes_topics_by_slug(self):
        allowed = build_allowed_topic_map(self.taxonomy)

        self.assertEqual(sorted(allowed.keys()), ["comfort", "love-of-neighbor", "peace", "prayer"])
        self.assertEqual(allowed["comfort"]["group"], "need")

    def test_normalize_assignment_filters_duplicates_and_requires_allowed_topics(self):
        normalized = normalize_assignment(
            {
                "primary_topic": "comfort",
                "topics": ["comfort", "peace", "comfort"],
                "reader_needs": ["comfort", "hope", "comfort"],
            },
            self.allowed_topics,
            self.allowed_reader_needs,
        )

        self.assertEqual(normalized["primary_topic"], "comfort")
        self.assertEqual(normalized["topics"], ["comfort", "peace"])
        self.assertEqual(normalized["reader_needs"], ["comfort", "hope"])

    def test_normalize_assignment_rejects_unknown_primary_topic(self):
        with self.assertRaises(ValueError):
            normalize_assignment(
                {
                    "primary_topic": "unknown",
                    "topics": ["comfort"],
                    "reader_needs": [],
                },
                build_allowed_topic_map(self.taxonomy),
            )

    def test_normalize_assignment_rejects_unknown_secondary_topics(self):
        with self.assertRaises(ValueError):
            normalize_assignment(
                {
                    "primary_topic": "comfort",
                    "topics": ["comfort", "unknown"],
                    "reader_needs": [],
                },
                build_allowed_topic_map(self.taxonomy),
            )

    def test_normalize_assignment_rejects_unknown_reader_needs(self):
        with self.assertRaises(ValueError):
            normalize_assignment(
                {
                    "primary_topic": "comfort",
                    "topics": ["comfort"],
                    "reader_needs": ["unknown"],
                },
                build_allowed_topic_map(self.taxonomy),
            )

    def test_normalize_assignment_coerces_display_names_to_slugs(self):
        normalized = normalize_assignment(
            {
                "primary_topic": "  love of neighbor  ",
                "topics": [{"name": " Comfort "}, "Love of Neighbor"],
                "reader_needs": [{"name": " Hope "}],
            },
            self.allowed_topics,
            self.allowed_reader_needs,
        )

        self.assertEqual(normalized["primary_topic"], "love-of-neighbor")
        self.assertEqual(normalized["topics"], ["love-of-neighbor", "comfort"])
        self.assertEqual(normalized["reader_needs"], ["hope"])

    def test_normalize_assignment_handles_scalar_topics_without_iterating_characters(self):
        normalized = normalize_assignment(
            {
                "primary_topic": "comfort",
                "topics": "peace",
                "reader_needs": [],
            },
            self.allowed_topics,
            self.allowed_reader_needs,
        )

        self.assertEqual(normalized["topics"], ["comfort", "peace"])

    def test_normalize_assignment_handles_scalar_reader_needs_without_iterating_characters(self):
        normalized = normalize_assignment(
            {
                "primary_topic": "comfort",
                "topics": ["peace"],
                "reader_needs": "hope",
            },
            self.allowed_topics,
            self.allowed_reader_needs,
        )

        self.assertEqual(normalized["reader_needs"], ["hope"])

    def test_main_coerces_display_name_responses_end_to_end(self):
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            entries_path = tmp_path / "entries.json"
            taxonomy_path = tmp_path / "topic_taxonomy.json"
            entry_topics_path = tmp_path / "entry_topics.json"
            cache_path = tmp_path / "entry_topics_cache.json"

            entries_path.write_text(json.dumps([
                {"mmdd": "0101", "title": "A", "display_date": "Jan 1", "verse_ref": "V", "bible_verse": "B", "poem": "P"}
            ]), encoding="utf-8")
            taxonomy_path.write_text(json.dumps(self.taxonomy), encoding="utf-8")

            sample_response = {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"primary_topic":" Love of Neighbor ","topics":[{"name":" Prayer "}],"reader_needs":[{"name":" Comfort "}]}' }]
                    }
                ]
            }

            with patch("tools.tag_entries_openai.ROOT", tmp_path), \
                patch("tools.tag_entries_openai.ENTRIES_PATH", entries_path), \
                patch("tools.tag_entries_openai.TOPIC_TAXONOMY_PATH", taxonomy_path), \
                patch("tools.tag_entries_openai.ENTRY_TOPICS_PATH", entry_topics_path), \
                patch("tools.tag_entries_openai.CACHE_PATH", cache_path), \
                patch("tools.tag_entries_openai.fetch_assignment", return_value=sample_response), \
                patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True):
                main(["--entry", "0101"])

            payload = json.loads(entry_topics_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["0101"]["primary_topic"], "love-of-neighbor")
            self.assertEqual(payload["0101"]["topics"], ["love-of-neighbor", "prayer"])
            self.assertEqual(payload["0101"]["reader_needs"], ["comfort"])

    def test_main_coerces_scalar_reader_needs_responses_end_to_end(self):
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            entries_path = tmp_path / "entries.json"
            taxonomy_path = tmp_path / "topic_taxonomy.json"
            entry_topics_path = tmp_path / "entry_topics.json"
            cache_path = tmp_path / "entry_topics_cache.json"

            entries_path.write_text(json.dumps([
                {"mmdd": "0101", "title": "A", "display_date": "Jan 1", "verse_ref": "V", "bible_verse": "B", "poem": "P"}
            ]), encoding="utf-8")
            taxonomy_path.write_text(json.dumps(self.taxonomy), encoding="utf-8")

            sample_response = {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"primary_topic":"comfort","topics":["peace"],"reader_needs":"hope"}' }]
                    }
                ]
            }

            with patch("tools.tag_entries_openai.ROOT", tmp_path), \
                patch("tools.tag_entries_openai.ENTRIES_PATH", entries_path), \
                patch("tools.tag_entries_openai.TOPIC_TAXONOMY_PATH", taxonomy_path), \
                patch("tools.tag_entries_openai.ENTRY_TOPICS_PATH", entry_topics_path), \
                patch("tools.tag_entries_openai.CACHE_PATH", cache_path), \
                patch("tools.tag_entries_openai.fetch_assignment", return_value=sample_response), \
                patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True):
                main(["--entry", "0101"])

            payload = json.loads(entry_topics_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["0101"]["primary_topic"], "comfort")
            self.assertEqual(payload["0101"]["topics"], ["comfort", "peace"])
            self.assertEqual(payload["0101"]["reader_needs"], ["hope"])

    def test_main_discards_invalid_reader_needs_prose_but_keeps_valid_topics(self):
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            entries_path = tmp_path / "entries.json"
            taxonomy_path = tmp_path / "topic_taxonomy.json"
            entry_topics_path = tmp_path / "entry_topics.json"
            cache_path = tmp_path / "entry_topics_cache.json"

            entries_path.write_text(json.dumps([
                {"mmdd": "0101", "title": "A", "display_date": "Jan 1", "verse_ref": "V", "bible_verse": "B", "poem": "P"}
            ]), encoding="utf-8")
            taxonomy_path.write_text(json.dumps(self.taxonomy), encoding="utf-8")

            sample_response = {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"primary_topic":"Love of Neighbor","topics":["Prayer"],"reader_needs":["Assurance of Christ’s victory over Satan and death (Hebrews 2:14)"]}'}]
                    }
                ]
            }

            with patch("tools.tag_entries_openai.ROOT", tmp_path), \
                patch("tools.tag_entries_openai.ENTRIES_PATH", entries_path), \
                patch("tools.tag_entries_openai.TOPIC_TAXONOMY_PATH", taxonomy_path), \
                patch("tools.tag_entries_openai.ENTRY_TOPICS_PATH", entry_topics_path), \
                patch("tools.tag_entries_openai.CACHE_PATH", cache_path), \
                patch("tools.tag_entries_openai.fetch_assignment", return_value=sample_response), \
                patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True):
                main(["--entry", "0101"])

            payload = json.loads(entry_topics_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["0101"]["primary_topic"], "love-of-neighbor")
            self.assertEqual(payload["0101"]["topics"], ["love-of-neighbor", "prayer"])
            self.assertEqual(payload["0101"]["reader_needs"], [])

    def test_write_assignments_writes_sorted_json_with_trailing_newline(self):
        with TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "entry_topics.json"
            write_assignments(
                output_path,
                {
                    "0102": {"primary_topic": "prayer", "topics": ["prayer"], "reader_needs": []},
                    "0101": {"primary_topic": "comfort", "topics": ["comfort"], "reader_needs": ["comfort"]},
                },
            )

            written = output_path.read_text(encoding="utf-8")
            self.assertTrue(written.endswith("\n"))

            payload = json.loads(written)
            self.assertEqual(list(payload.keys()), ["0101", "0102"])

    def test_parse_assignment_response_extracts_json_from_responses_envelope(self):
        payload = {
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": '{"primary_topic":"comfort","topics":["comfort"],"reader_needs":[]}'}]}
            ]
        }

        parsed = parse_assignment_response(payload)

        self.assertEqual(parsed["primary_topic"], "comfort")

    def test_fetch_assignment_requests_json_object_output(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"output": []}'

        entry = {"mmdd": "0101", "title": "A", "display_date": "Jan 1", "verse_ref": "V", "bible_verse": "B", "poem": "P"}
        captured = {}

        def fake_urlopen(req, timeout=60):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            captured["headers"] = dict(req.headers)
            return FakeResponse()

        with patch("tools.tag_entries_openai.request.urlopen", side_effect=fake_urlopen):
            fetch_assignment(entry, self.taxonomy, "test-key")

        self.assertEqual(captured["body"]["model"], "gpt-5-mini")
        self.assertEqual(captured["body"]["text"]["format"]["type"], "json_object")
        self.assertIn("Return only a valid JSON object", captured["body"]["input"])
        self.assertIn("application/json", captured["headers"].get("Content-type", captured["headers"].get("Content-Type", "")))

    def test_main_merges_existing_assignments_when_processing_subset(self):
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            entries_path = tmp_path / "entries.json"
            taxonomy_path = tmp_path / "topic_taxonomy.json"
            entry_topics_path = tmp_path / "entry_topics.json"
            cache_path = tmp_path / "entry_topics_cache.json"

            entries_path.write_text(json.dumps([
                {"mmdd": "0101", "title": "A", "display_date": "Jan 1", "verse_ref": "V", "bible_verse": "B", "poem": "P"},
                {"mmdd": "0102", "title": "B", "display_date": "Jan 2", "verse_ref": "V", "bible_verse": "B", "poem": "P"},
            ]), encoding="utf-8")
            taxonomy_path.write_text(json.dumps(self.taxonomy), encoding="utf-8")
            entry_topics_path.write_text(json.dumps({"0102": {"primary_topic": "prayer", "topics": ["prayer"], "reader_needs": []}}), encoding="utf-8")
            cache_path.write_text(json.dumps({"0102": {"primary_topic": "prayer", "topics": ["prayer"], "reader_needs": []}}), encoding="utf-8")

            sample_response = {
                "output": [
                    {"type": "message", "content": [{"type": "output_text", "text": '{"primary_topic":"comfort","topics":["comfort"],"reader_needs":[]}'}]}
                ]
            }

            with patch("tools.tag_entries_openai.ROOT", tmp_path), \
                patch("tools.tag_entries_openai.ENTRIES_PATH", entries_path), \
                patch("tools.tag_entries_openai.TOPIC_TAXONOMY_PATH", taxonomy_path), \
                patch("tools.tag_entries_openai.ENTRY_TOPICS_PATH", entry_topics_path), \
                patch("tools.tag_entries_openai.CACHE_PATH", cache_path), \
                patch("tools.tag_entries_openai.fetch_assignment", return_value=sample_response), \
                patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True):
                main(["--entry", "0101"])

            payload = json.loads(entry_topics_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["0101"]["primary_topic"], "comfort")
            self.assertEqual(payload["0102"]["primary_topic"], "prayer")

    def test_normalize_assignment_rejects_topic_used_as_reader_need(self):
        # "prayer" is a topic in this taxonomy but NOT in the reader_needs vocabulary —
        # the model must not smuggle topic slugs into reader_needs.
        with self.assertRaises(ValueError):
            normalize_assignment(
                {
                    "primary_topic": "comfort",
                    "topics": ["comfort"],
                    "reader_needs": ["prayer"],
                },
                self.allowed_topics,
                self.allowed_reader_needs,
            )

    def test_build_prompt_includes_discrimination_rules_and_vocab(self):
        entry = {
            "mmdd": "0101",
            "title": "A",
            "display_date": "Jan 1",
            "verse_ref": "V",
            "bible_verse": "B",
            "poem": "P",
        }
        prompt = build_prompt(entry, self.taxonomy)
        # The prompt must explicitly cap topic counts and enumerate both vocabularies.
        self.assertIn("AT MOST", prompt)
        self.assertIn("primary_topic", prompt)
        self.assertIn("reader_needs", prompt)
        # Topic and reader-need slugs appear so the model has a closed vocabulary.
        self.assertIn("comfort", prompt)
        self.assertIn("hope", prompt)
        self.assertIn("strength", prompt)
        # The "do not default to grace/faith" guidance prevents overbroad tagging.
        self.assertIn("grace", prompt.lower())


if __name__ == "__main__":
    unittest.main()
