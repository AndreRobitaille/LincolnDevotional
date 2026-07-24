# Explore Topics and Reader Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a browse-first Explore system with curated taxonomy data, AI-assisted topic assignment tooling, static explore/topic pages, and linked topic chips on devotional entries.

**Architecture:** Keep `data/entries.json` as the devotional source of truth. Add a curated taxonomy file plus an approved entry-topic assignment file, then extend the existing Python static-site generator to emit Explore pages and topic chips from those files. Keep AI usage in a separate editorial tool so deploys remain deterministic and reviewable.

**Tech Stack:** Static HTML/CSS/JavaScript, Python 3 standard library, Python `unittest`, OpenAI Responses API over `urllib.request`

---

## File Structure

- Create: `data/topic_taxonomy.json`
  - Stores the approved browse taxonomy, topic grouping, descriptions, and related-topic links.
- Create: `data/entry_topics.json`
  - Stores the approved per-entry `primary_topic`, `topics`, and `reader_needs` assignments keyed by `mmdd`.
- Create: `tools/tag_entries_openai.py`
  - CLI editorial tool that reads entries plus taxonomy, calls OpenAI with constrained output, validates results, caches responses, and writes `data/entry_topics.json`.
- Create: `tests/test_tag_entries_openai.py`
  - Covers taxonomy validation, response normalization, and CLI write behavior without hitting the network.
- Modify: `tools/generate_entry_pages.py`
  - Load taxonomy and topic assignments, generate `/explore/index.html`, generate one page per topic, render topic chips on entry pages, and add Explore/topic URLs to the sitemap.
- Modify: `style.css`
  - Add presentation for Explore cards, topic lists, and topic chips while reusing the current design language.
- Modify: `tests/test_generate_entry_pages.py`
  - Add failing coverage for explore hub generation, topic page generation, topic chips, and sitemap inclusion.
- Modify: `index.html`
  - Add `Explore` to the primary nav and a simple Explore CTA near the daily-reading flow.
- Modify: `about.html`
  - Add `Explore` to the primary nav.
- Modify: `copyright.html`
  - Add `Explore` to the primary nav if the page already renders the shared site header.

## Task 1: Lock down Explore generation with failing tests

**Files:**
- Modify: `tests/test_generate_entry_pages.py`
- Test: `tests/test_generate_entry_pages.py`

- [ ] **Step 1: Expand the fixture data with taxonomy and topic assignments**

Add these fixtures to `GenerateEntryPagesTests.setUp` in `tests/test_generate_entry_pages.py` after `self.esv_cache`:

```python
        self.topic_taxonomy = {
            "topics": [
                {
                    "slug": "comfort",
                    "name": "Comfort",
                    "group": "need",
                    "description": "For seasons of sorrow, inward distress, and the need for consolation.",
                    "related": ["peace", "hope"],
                },
                {
                    "slug": "peace",
                    "name": "Peace",
                    "group": "need",
                    "description": "For resting in God when the mind is troubled.",
                    "related": ["comfort", "assurance"],
                },
                {
                    "slug": "prayer",
                    "name": "Prayer",
                    "group": "christian-life",
                    "description": "For communion with God through asking, thanksgiving, and dependence.",
                    "related": ["faith", "guidance"],
                },
            ]
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
```

- [ ] **Step 2: Add a failing test for the Explore hub, topic pages, and entry chips**

Add this test method inside `GenerateEntryPagesTests` in `tests/test_generate_entry_pages.py`:

```python
    def test_generate_site_writes_explore_pages_and_entry_topic_chips(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(
                self.entries,
                self.esv_cache,
                output_root,
                "https://lincolndevotional.com",
                self.topic_taxonomy,
                self.entry_topics,
            )

            explore_page = output_root / "explore" / "index.html"
            comfort_page = output_root / "explore" / "comfort" / "index.html"
            entry_page = output_root / "entries" / "january-1" / "index.html"

            self.assertTrue(explore_page.exists())
            self.assertTrue(comfort_page.exists())

            explore_html = explore_page.read_text()
            comfort_html = comfort_page.read_text()
            entry_html = entry_page.read_text()

            self.assertIn("Find a devotion for today’s need", explore_html)
            self.assertIn('href="/explore/comfort/"', explore_html)
            self.assertIn("For seasons of sorrow, inward distress, and the need for consolation.", explore_html)

            self.assertIn("Comfort", comfort_html)
            self.assertIn("January 1", comfort_html)
            self.assertIn("The Believer the Object of Divine Love", comfort_html)
            self.assertIn('href="/entries/january-1/"', comfort_html)
            self.assertIn('href="/explore/peace/"', comfort_html)

            self.assertIn('class="entry-topic-chips"', entry_html)
            self.assertIn('href="/explore/comfort/"', entry_html)
            self.assertIn('href="/explore/peace/"', entry_html)
```

- [ ] **Step 3: Add a failing sitemap test for Explore URLs**

Add this test method inside `GenerateEntryPagesTests` in `tests/test_generate_entry_pages.py`:

```python
    def test_generate_site_adds_explore_pages_to_sitemap(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(
                self.entries,
                self.esv_cache,
                output_root,
                "https://lincolndevotional.com",
                self.topic_taxonomy,
                self.entry_topics,
            )

            sitemap_xml = (output_root / "sitemap.xml").read_text()

            self.assertIn("https://lincolndevotional.com/explore/", sitemap_xml)
            self.assertIn("https://lincolndevotional.com/explore/comfort/", sitemap_xml)
            self.assertIn("https://lincolndevotional.com/explore/prayer/", sitemap_xml)
```

- [ ] **Step 4: Run the generator tests and confirm the new expectations fail**

Run: `python3 -m unittest tests.test_generate_entry_pages -v`

Expected: FAIL because `generate_site()` does not yet accept taxonomy/topic arguments or emit Explore/topic HTML.

- [ ] **Step 5: Commit the failing generator-test checkpoint**

```bash
git add tests/test_generate_entry_pages.py
git commit -m "test: cover explore topic generation"
```

## Task 2: Lock down the OpenAI tagging workflow with failing tests

**Files:**
- Create: `tests/test_tag_entries_openai.py`
- Test: `tests/test_tag_entries_openai.py`

- [ ] **Step 1: Create the tagging tool test file with validation coverage**

Create `tests/test_tag_entries_openai.py` with this content:

```python
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.tag_entries_openai import (
    build_allowed_topic_map,
    normalize_assignment,
    write_assignments,
)


class TagEntriesOpenAITests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = {
            "topics": [
                {"slug": "comfort", "name": "Comfort", "group": "need", "description": "desc", "related": ["peace"]},
                {"slug": "peace", "name": "Peace", "group": "need", "description": "desc", "related": ["comfort"]},
                {"slug": "prayer", "name": "Prayer", "group": "christian-life", "description": "desc", "related": []},
            ]
        }

    def test_build_allowed_topic_map_indexes_topics_by_slug(self):
        allowed = build_allowed_topic_map(self.taxonomy)

        self.assertEqual(sorted(allowed.keys()), ["comfort", "peace", "prayer"])
        self.assertEqual(allowed["comfort"]["group"], "need")

    def test_normalize_assignment_filters_duplicates_and_requires_allowed_topics(self):
        normalized = normalize_assignment(
            {
                "primary_topic": "comfort",
                "topics": ["comfort", "peace", "comfort"],
                "reader_needs": ["comfort", "peace"],
            },
            build_allowed_topic_map(self.taxonomy),
        )

        self.assertEqual(normalized["primary_topic"], "comfort")
        self.assertEqual(normalized["topics"], ["comfort", "peace"])
        self.assertEqual(normalized["reader_needs"], ["comfort", "peace"])

    def test_normalize_assignment_rejects_unknown_topics(self):
        with self.assertRaises(ValueError):
            normalize_assignment(
                {
                    "primary_topic": "unknown",
                    "topics": ["comfort"],
                    "reader_needs": [],
                },
                build_allowed_topic_map(self.taxonomy),
            )

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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tagging tests to verify they fail because the tool does not exist**

Run: `python3 -m unittest tests.test_tag_entries_openai -v`

Expected: FAIL with `ModuleNotFoundError` or import errors for `tools.tag_entries_openai`.

- [ ] **Step 3: Commit the failing tagging-test checkpoint**

```bash
git add tests/test_tag_entries_openai.py
git commit -m "test: cover OpenAI entry tagging tool"
```

## Task 3: Add curated taxonomy data and implement the OpenAI tagging tool

**Files:**
- Create: `data/topic_taxonomy.json`
- Create: `data/entry_topics.json`
- Create: `tools/tag_entries_openai.py`
- Test: `tests/test_tag_entries_openai.py`

- [ ] **Step 1: Create the first curated taxonomy file**

Create `data/topic_taxonomy.json` with this starter taxonomy:

```json
{
  "topics": [
    {
      "slug": "comfort",
      "name": "Comfort",
      "group": "need",
      "description": "For seasons of sorrow, inward distress, and the need for consolation.",
      "related": ["peace", "hope", "grief"]
    },
    {
      "slug": "peace",
      "name": "Peace",
      "group": "need",
      "description": "For resting in God when the mind is troubled.",
      "related": ["comfort", "assurance", "hope"]
    },
    {
      "slug": "hope",
      "name": "Hope",
      "group": "need",
      "description": "For looking beyond present darkness to God’s future mercy.",
      "related": ["comfort", "peace", "heaven"]
    },
    {
      "slug": "guidance",
      "name": "Guidance",
      "group": "need",
      "description": "For seeking the Lord’s direction in uncertainty and duty.",
      "related": ["prayer", "faith", "providence"]
    },
    {
      "slug": "strength",
      "name": "Strength",
      "group": "need",
      "description": "For weakness, trial, endurance, and dependence on Christ.",
      "related": ["faith", "comfort", "temptation"]
    },
    {
      "slug": "forgiveness",
      "name": "Forgiveness",
      "group": "need",
      "description": "For pardon, mercy, and cleansing from sin.",
      "related": ["repentance", "grace", "redemption"]
    },
    {
      "slug": "temptation",
      "name": "Temptation",
      "group": "need",
      "description": "For resisting sin, spiritual conflict, and watchfulness.",
      "related": ["strength", "holiness", "prayer"]
    },
    {
      "slug": "grief",
      "name": "Grief",
      "group": "need",
      "description": "For bereavement, sorrow, and affliction.",
      "related": ["comfort", "hope", "death-and-resurrection"]
    },
    {
      "slug": "patience",
      "name": "Patience",
      "group": "need",
      "description": "For waiting well under pressure, pain, or delay.",
      "related": ["comfort", "strength", "holiness"]
    },
    {
      "slug": "assurance",
      "name": "Assurance",
      "group": "need",
      "description": "For confidence in Christ, salvation, and God’s keeping power.",
      "related": ["peace", "faith", "christ"]
    },
    {
      "slug": "prayer",
      "name": "Prayer",
      "group": "christian-life",
      "description": "For communion with God through asking, thanksgiving, and dependence.",
      "related": ["faith", "guidance", "scripture"]
    },
    {
      "slug": "faith",
      "name": "Faith",
      "group": "christian-life",
      "description": "For trusting Christ and resting in God’s word and promises.",
      "related": ["assurance", "hope", "guidance"]
    },
    {
      "slug": "obedience",
      "name": "Obedience",
      "group": "christian-life",
      "description": "For holy conduct, duty, and glad submission to God.",
      "related": ["holiness", "good-works", "repentance"]
    },
    {
      "slug": "thanksgiving",
      "name": "Thanksgiving",
      "group": "christian-life",
      "description": "For gratitude, praise, and glad remembrance of God’s mercies.",
      "related": ["prayer", "grace", "faith"]
    },
    {
      "slug": "holiness",
      "name": "Holiness",
      "group": "christian-life",
      "description": "For sanctification, purity, watchfulness, and growth in grace.",
      "related": ["obedience", "repentance", "holy-spirit"]
    },
    {
      "slug": "repentance",
      "name": "Repentance",
      "group": "christian-life",
      "description": "For sorrow over sin, self-examination, and turning again to God.",
      "related": ["forgiveness", "holiness", "grace"]
    },
    {
      "slug": "good-works",
      "name": "Good Works",
      "group": "christian-life",
      "description": "For useful service, diligence, and visible Christian conduct.",
      "related": ["obedience", "love-of-neighbor", "holiness"]
    },
    {
      "slug": "love-of-neighbor",
      "name": "Love of Neighbor",
      "group": "christian-life",
      "description": "For compassion, forgiveness, fellowship, and practical love toward others.",
      "related": ["good-works", "grace", "obedience"]
    },
    {
      "slug": "christ",
      "name": "Christ",
      "group": "study",
      "description": "For the person, offices, beauty, and sufficiency of Christ.",
      "related": ["grace", "redemption", "assurance"]
    },
    {
      "slug": "grace",
      "name": "Grace",
      "group": "study",
      "description": "For God’s free favor, mercy, and saving kindness toward sinners.",
      "related": ["forgiveness", "redemption", "faith"]
    },
    {
      "slug": "redemption",
      "name": "Redemption",
      "group": "study",
      "description": "For pardon, atonement, justification, and salvation through Christ.",
      "related": ["christ", "grace", "forgiveness"]
    },
    {
      "slug": "scripture",
      "name": "Scripture",
      "group": "study",
      "description": "For the love, use, truth, and authority of God’s word.",
      "related": ["prayer", "faith", "guidance"]
    },
    {
      "slug": "holy-spirit",
      "name": "The Holy Spirit",
      "group": "study",
      "description": "For the Spirit’s indwelling, sanctifying, guiding, and comforting work.",
      "related": ["holiness", "christ", "assurance"]
    },
    {
      "slug": "heaven",
      "name": "Heaven",
      "group": "study",
      "description": "For eternal joy, rest, glory, and the believer’s final home with God.",
      "related": ["hope", "death-and-resurrection", "christ"]
    },
    {
      "slug": "death-and-resurrection",
      "name": "Death and Resurrection",
      "group": "study",
      "description": "For mortality, dying in peace, resurrection hope, and final victory.",
      "related": ["grief", "heaven", "hope"]
    },
    {
      "slug": "providence",
      "name": "Providence",
      "group": "study",
      "description": "For God’s rule, guidance, protection, and wise ordering of events.",
      "related": ["guidance", "comfort", "faith"]
    }
  ]
}
```

- [ ] **Step 2: Seed the repository with an empty approved assignment file**

Create `data/entry_topics.json` with this content:

```json
{}
```

- [ ] **Step 3: Implement the OpenAI tagging tool**

Create `tools/tag_entries_openai.py` with this implementation:

```python
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib import error, request


ROOT = Path(__file__).resolve().parent.parent
ENTRIES_PATH = ROOT / "data" / "entries.json"
TAXONOMY_PATH = ROOT / "data" / "topic_taxonomy.json"
OUTPUT_PATH = ROOT / "data" / "entry_topics.json"
CACHE_PATH = ROOT / "data" / "entry_topics_cache.json"
API_URL = "https://api.openai.com/v1/responses"
MODEL = "gpt-5-mini"


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_allowed_topic_map(taxonomy):
    topics = taxonomy.get("topics", [])
    allowed = {topic["slug"]: topic for topic in topics}
    if not allowed:
        raise ValueError("Taxonomy does not contain any topics.")
    return allowed


def normalize_assignment(raw_assignment, allowed_topics):
    primary_topic = raw_assignment.get("primary_topic")
    if primary_topic not in allowed_topics:
        raise ValueError(f"Unknown primary topic: {primary_topic}")

    def dedupe(values):
        seen = set()
        ordered = []
        for value in values:
            if value not in allowed_topics:
                raise ValueError(f"Unknown topic slug: {value}")
            if value not in seen:
                ordered.append(value)
                seen.add(value)
        return ordered

    topics = dedupe(raw_assignment.get("topics", []))
    reader_needs = dedupe(raw_assignment.get("reader_needs", []))

    if primary_topic not in topics:
        topics.insert(0, primary_topic)

    return {
        "primary_topic": primary_topic,
        "topics": topics,
        "reader_needs": reader_needs,
    }


def write_assignments(path: Path, assignments):
    ordered = {key: assignments[key] for key in sorted(assignments.keys())}
    path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_cache(path: Path):
    if not path.exists():
        return {}
    return load_json(path)


def write_cache(path: Path, cache_payload):
    path.write_text(json.dumps(cache_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_prompt(entry, taxonomy):
    topic_lines = [
        f"- {topic['slug']}: {topic['name']} ({topic['group']}) — {topic['description']}"
        for topic in taxonomy["topics"]
    ]
    topic_text = "\n".join(topic_lines)
    poem = entry.get("poem", "")
    return f"""You are classifying devotional entries into an approved taxonomy.

Allowed topics:
{topic_text}

Return strict JSON with these keys:
- primary_topic: one allowed topic slug
- topics: 2-4 allowed topic slugs including the primary topic
- reader_needs: 0-2 allowed topic slugs, normally from the need group

Entry:
Date: {entry['display_date']}
Title: {entry['title']}
Verse reference: {entry['verse_ref']}
Verse text: {entry['bible_verse']}
Poem: {poem}
"""


def fetch_assignment(entry, taxonomy, api_key):
    payload = {
        "model": MODEL,
        "input": build_prompt(entry, taxonomy),
        "text": {"format": {"type": "json_object"}},
    }
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI request failed: {exc.code} {detail}") from exc

    output_text = response_payload["output"][0]["content"][0]["text"]
    return json.loads(output_text)


def select_entries(entries, entry_mmdd=None, limit=None):
    selected = entries
    if entry_mmdd:
        selected = [entry for entry in selected if entry["mmdd"] == entry_mmdd]
    if limit is not None:
        selected = selected[:limit]
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--entry")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    entries = load_json(ENTRIES_PATH)
    taxonomy = load_json(TAXONOMY_PATH)
    allowed_topics = build_allowed_topic_map(taxonomy)
    assignments = load_json(OUTPUT_PATH) if args.resume and OUTPUT_PATH.exists() else {}
    cache_payload = load_cache(CACHE_PATH)
    selected_entries = select_entries(entries, entry_mmdd=args.entry, limit=args.limit)

    if not args.dry_run:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required unless --dry-run is used.")
    else:
        api_key = None

    report_rows = []

    for entry in selected_entries:
        mmdd = entry["mmdd"]
        if args.resume and mmdd in assignments:
            continue

        if mmdd in cache_payload:
            raw_assignment = cache_payload[mmdd]
        elif args.dry_run:
            raw_assignment = {
                "primary_topic": "comfort",
                "topics": ["comfort", "peace"],
                "reader_needs": ["comfort"],
            }
        else:
            raw_assignment = fetch_assignment(entry, taxonomy, api_key)
            cache_payload[mmdd] = raw_assignment
            write_cache(CACHE_PATH, cache_payload)

        normalized = normalize_assignment(raw_assignment, allowed_topics)
        assignments[mmdd] = normalized
        report_rows.append({"mmdd": mmdd, **normalized})

    if args.report or args.dry_run:
        print(json.dumps(report_rows, indent=2, ensure_ascii=False))

    if not args.dry_run:
        write_assignments(OUTPUT_PATH, assignments)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tagging tests to verify they pass**

Run: `python3 -m unittest tests.test_tag_entries_openai -v`

Expected: PASS for all `TagEntriesOpenAITests`.

- [ ] **Step 5: Smoke-test the CLI without network writes**

Run: `python3 tools/tag_entries_openai.py --dry-run --limit 2 --report`

Expected: prints two normalized JSON assignment objects and does not modify `data/entry_topics.json`.

- [ ] **Step 6: Commit the taxonomy and tooling**

```bash
git add data/topic_taxonomy.json data/entry_topics.json tools/tag_entries_openai.py tests/test_tag_entries_openai.py
git commit -m "feat: add explore topic taxonomy tooling"
```

## Task 4: Extend the static generator to emit Explore pages, topic chips, and sitemap entries

**Files:**
- Modify: `tools/generate_entry_pages.py`
- Test: `tests/test_generate_entry_pages.py`

- [ ] **Step 1: Add topic helper functions near the top of the generator**

In `tools/generate_entry_pages.py`, add these helpers below `build_entry_href`:

```python
def build_topic_href(topic_slug):
    return f"/explore/{topic_slug}/"


def build_topic_map(topic_taxonomy):
    if not topic_taxonomy:
        return {}
    return {
        topic["slug"]: topic
        for topic in topic_taxonomy.get("topics", [])
    }


def group_topics(topic_taxonomy):
    grouped = {"need": [], "christian-life": [], "study": []}
    for topic in topic_taxonomy.get("topics", []):
        grouped.setdefault(topic["group"], []).append(topic)
    return grouped


def build_topic_index(entries, entry_topics):
    topic_index = {}
    for entry in entries:
        assignment = entry_topics.get(entry["mmdd"])
        if not assignment:
            continue
        seen = []
        for slug in assignment.get("topics", []) + assignment.get("reader_needs", []):
            if slug not in seen:
                seen.append(slug)
        for slug in seen:
            topic_index.setdefault(slug, []).append(entry)
    return topic_index
```

- [ ] **Step 2: Add HTML renderers for nav, topic chips, Explore cards, and topic pages**

Still in `tools/generate_entry_pages.py`, add these helpers above `render_entry_page`:

```python
def render_primary_nav(prefix, current_page=None):
    devotional_current = ' aria-current="page"' if current_page == "devotional" else ""
    about_current = ' aria-current="page"' if current_page == "about" else ""
    explore_current = ' aria-current="page"' if current_page == "explore" else ""
    return f"""
          <nav class="site-nav" aria-label="Primary">
            <a href="{prefix}index.html"{devotional_current}>Devotional</a>
            <a href="{prefix}explore/"{explore_current}>Explore</a>
            <a href="{prefix}about.html"{about_current}>About</a>
          </nav>"""


def render_topic_chips(assignment, topic_map):
    if not assignment:
        return ""

    chips = []
    for slug in assignment.get("topics", []):
        topic = topic_map.get(slug)
        if not topic:
            continue
        chips.append(
            f'<a class="entry-topic-chip" href="{build_topic_href(slug)}">{escape(topic["name"])}</a>'
        )

    if not chips:
        return ""

    return f"""
          <section class="entry-topic-chips" aria-label="Related topics">
            {"".join(chips)}
          </section>"""


def render_explore_section(title, topics):
    cards = []
    for topic in topics:
        cards.append(
            f"""
            <li class="explore-card">
              <a href="{build_topic_href(topic['slug'])}">
                <span class="explore-card-title">{escape(topic['name'])}</span>
                <span class="explore-card-description">{escape(topic['description'])}</span>
              </a>
            </li>"""
        )

    return f"""
        <section class="explore-section">
          <h2 class="entry-section-title">{escape(title)}</h2>
          <ul class="explore-card-list">
            {''.join(cards)}
          </ul>
        </section>"""


def render_explore_page(topic_taxonomy, site_url):
    grouped = group_topics(topic_taxonomy)
    main_nav = render_primary_nav("../", current_page="explore")
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="canonical" href="{site_url}/explore/" />
    <title>Explore Devotions by Topic</title>
    <meta name="description" content="Browse The Believer's Daily Treasure by need, Christian life, and study theme." />
    <link rel="stylesheet" href="../style.css?v=20260519b" />
  </head>
  <body>
    <div class="page">
      <header class="site-header">
        <div class="brand">
          <p class="site-eyebrow">Abraham Lincoln's Daily Devotional</p>
          <h1 class="site-title">Explore Devotions by Topic</h1>
          <p class="site-tagline">Find a devotion for today’s need, grow in the Christian life, or study a theme.</p>
        </div>
        <div class="site-actions">{main_nav}<button class="theme-toggle" id="themeToggle" type="button">Dark mode</button></div>
      </header>
      <main class="main-content">
        <article class="about-card">
          {render_explore_section('Find a devotion for today’s need', grouped.get('need', []))}
          {render_explore_section('Grow in the Christian life', grouped.get('christian-life', []))}
          {render_explore_section('Study by theme', grouped.get('study', []))}
        </article>
      </main>
    </div>
    <script src="../theme.js?v=20260123"></script>
  </body>
</html>
"""


def render_topic_page(topic, related_topics, entries, entry_topics, site_url):
    main_nav = render_primary_nav("../../", current_page="explore")
    related_links = "".join(
        f'<a class="entry-topic-chip" href="{build_topic_href(related["slug"])}">{escape(related["name"])}</a>'
        for related in related_topics
    )
    entry_rows = []
    for entry in entries:
        excerpt = entry["bible_verse"] if len(entry["bible_verse"]) <= 140 else f"{entry['bible_verse'][:137].rstrip()}..."
        entry_rows.append(
            f"""
            <li class="explore-entry-item">
              <a href="{build_entry_href(entry)}">
                <span class="explore-entry-date">{escape(entry['display_date'])}</span>
                <span class="explore-entry-title">{escape(entry['title'])}</span>
                <span class="explore-entry-excerpt">{escape(excerpt)}</span>
              </a>
            </li>"""
        )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="canonical" href="{site_url}{build_topic_href(topic['slug'])}" />
    <title>{escape(topic['name'])} Devotions</title>
    <meta name="description" content="{escape(topic['description'])}" />
    <link rel="stylesheet" href="../../style.css?v=20260519b" />
  </head>
  <body>
    <div class="page">
      <header class="site-header">
        <div class="brand">
          <p class="site-eyebrow">Abraham Lincoln's Daily Devotional</p>
          <h1 class="site-title">{escape(topic['name'])}</h1>
          <p class="site-tagline">{escape(topic['description'])}</p>
        </div>
        <div class="site-actions">{main_nav}<button class="theme-toggle" id="themeToggle" type="button">Dark mode</button></div>
      </header>
      <main class="main-content">
        <article class="about-card">
          <p class="entry-text"><a href="/explore/">Back to Explore</a></p>
          <ul class="explore-entry-list">{''.join(entry_rows)}</ul>
          <div class="entry-topic-chips">{related_links}</div>
        </article>
      </main>
    </div>
    <script src="../../theme.js?v=20260123"></script>
  </body>
</html>
"""
```

- [ ] **Step 3: Extend `render_entry_page`, `write_sitemap`, and `generate_site` to use the topic data**

Update `render_entry_page`, `write_sitemap`, and `generate_site` in `tools/generate_entry_pages.py` like this:

```python
def render_entry_page(entry, previous_entry, next_entry, esv_text, site_url, topic_map=None, assignment=None):
    topic_map = topic_map or {}
    topic_chips = render_topic_chips(assignment, topic_map)
    # keep the existing metadata and page body
    # replace the static site nav block with:
    main_nav = render_primary_nav("../../")
    # then inside the header use:
    # <div class="site-actions">{main_nav}<button ...>Dark mode</button></div>
    # and insert {topic_chips} immediately after the poem section.


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
    for topic in (topic_taxonomy or {}).get("topics", []):
        url = ET.SubElement(root, "url")
        loc = ET.SubElement(url, "loc")
        loc.text = f"{site_url}{build_topic_href(topic['slug'])}"
    sitemap_path = output_root / "sitemap.xml"
    sitemap_path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")


def generate_site(entries, esv_cache, output_root, site_url, topic_taxonomy=None, entry_topics=None):
    validate_entries(entries)
    topic_taxonomy = topic_taxonomy or {"topics": []}
    entry_topics = entry_topics or {}
    topic_map = build_topic_map(topic_taxonomy)
    topic_index = build_topic_index(entries, entry_topics)

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
        assignment = entry_topics.get(entry["mmdd"])
        html = render_entry_page(entry, previous_entry, next_entry, esv_text, site_url, topic_map, assignment)
        (entry_dir / "index.html").write_text(html, encoding="utf-8")

    explore_dir = output_root / "explore"
    explore_dir.mkdir(parents=True, exist_ok=True)
    (explore_dir / "index.html").write_text(render_explore_page(topic_taxonomy, site_url), encoding="utf-8")

    for topic in topic_taxonomy.get("topics", []):
        topic_dir = explore_dir / topic["slug"]
        topic_dir.mkdir(parents=True, exist_ok=True)
        related_topics = [topic_map[slug] for slug in topic.get("related", []) if slug in topic_map]
        topic_entries = topic_index.get(topic["slug"], [])
        topic_html = render_topic_page(topic, related_topics, topic_entries, entry_topics, site_url)
        (topic_dir / "index.html").write_text(topic_html, encoding="utf-8")

    write_sitemap(entries, output_root, site_url, topic_taxonomy)
    write_robots_txt(output_root, site_url)
    write_routes_manifest(entries, output_root)
```

- [ ] **Step 4: Update `main()` so the generator loads taxonomy and assignments from disk**

Replace `main()` in `tools/generate_entry_pages.py` with:

```python
def main():
    entries = load_json(ENTRIES_PATH)
    esv_cache = load_json(ESV_CACHE_PATH)
    topic_taxonomy = load_json(ROOT / "data" / "topic_taxonomy.json")
    entry_topics = load_json(ROOT / "data" / "entry_topics.json")
    generate_site(entries, esv_cache, OUTPUT_ROOT, SITE_URL, topic_taxonomy, entry_topics)
```

- [ ] **Step 5: Run generator tests and confirm they pass**

Run: `python3 -m unittest tests.test_generate_entry_pages -v`

Expected: PASS for the existing entry-page coverage and the new Explore/topic assertions.

- [ ] **Step 6: Regenerate site output in the workspace**

Run: `python3 tools/generate_entry_pages.py`

Expected: updated `entries/`, `explore/`, `sitemap.xml`, `robots.txt`, and `data/routes.json` written without exceptions.

- [ ] **Step 7: Commit the generator changes**

```bash
git add tools/generate_entry_pages.py tests/test_generate_entry_pages.py entries explore sitemap.xml robots.txt data/routes.json
git commit -m "feat: generate explore topic pages"
```

## Task 5: Wire the Explore link into hand-authored pages and verify the UX

**Files:**
- Modify: `style.css`
- Modify: `index.html`
- Modify: `about.html`
- Modify: `copyright.html`

- [ ] **Step 1: Add styles for topic chips and Explore browse layouts**

In `style.css`, add these rules near the existing card and list component styles:

```css
.entry-topic-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 24px;
}

.entry-topic-chip {
    display: inline-flex;
    align-items: center;
    padding: 8px 14px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--surface-elevated);
    font-family: var(--font-ui);
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.explore-section + .explore-section {
    margin-top: 28px;
}

.explore-card-list,
.explore-entry-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.explore-card-list {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
}

.explore-card a,
.explore-entry-item a {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 20px;
    border: 1px solid var(--border);
    border-radius: 20px;
    background: var(--surface-elevated);
}

.explore-card-title,
.explore-entry-title {
    font-family: var(--font-display);
    font-size: 1.1rem;
}

.explore-card-description,
.explore-entry-excerpt,
.explore-entry-date {
    color: var(--muted);
}

.explore-entry-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
}
```

- [ ] **Step 2: Add `Explore` to the shared nav on hand-authored pages**

In `index.html`, update the primary nav to:

```html
          <nav class="site-nav" aria-label="Primary">
            <a href="index.html" aria-current="page">Devotional</a>
            <a href="explore/">Explore</a>
            <a href="about.html">About</a>
          </nav>
```

In `about.html`, update the primary nav to:

```html
          <nav class="site-nav" aria-label="Primary">
            <a href="index.html">Devotional</a>
            <a href="explore/">Explore</a>
            <a href="about.html" aria-current="page">About</a>
          </nav>
```

In `copyright.html`, update the primary nav the same way, setting `aria-current="page"` only if that page already uses it for its own nav item.

- [ ] **Step 3: Add a lightweight Explore CTA on the homepage below the permalink area**

In `index.html`, insert this block after the permalink `<aside>` and before the footer:

```html
      <section class="about-card" aria-label="Explore more devotions">
        <header class="about-header">
          <h2 class="about-title">Explore by topic</h2>
        </header>
        <p class="entry-text">
          Browse devotions by comfort, prayer, hope, temptation, Scripture, heaven, and more.
        </p>
        <div class="about-cta">
          <a href="explore/" class="cta-button">Explore Topics</a>
        </div>
      </section>
```

- [ ] **Step 4: Start the local server and manually verify the main browse paths**

Run: `python3 -m http.server 8000`

Expected: local site available at `http://localhost:8000`.

Then manually verify:

- `http://localhost:8000/` still loads today’s devotion.
- The main nav shows `Explore`.
- `http://localhost:8000/explore/` loads the Explore hub.
- At least one topic page loads and links into generated entries.
- A generated entry page shows topic chips that link back to Explore.

- [ ] **Step 5: Run the full automated test suite**

Run: `python3 -m unittest tests.test_generate_entry_pages tests.test_tag_entries_openai -v`

Expected: PASS for all tests.

- [ ] **Step 6: Commit the hand-authored page updates**

```bash
git add style.css index.html about.html copyright.html
git commit -m "feat: add explore entry points"
```

## Task 6: Populate approved topic assignments and publish the first Explore dataset

**Files:**
- Modify: `data/entry_topics.json`
- Test: `tools/tag_entries_openai.py`

- [ ] **Step 1: Generate a first-pass assignment report for review**

Run: `OPENAI_API_KEY=your_key_here python3 tools/tag_entries_openai.py --limit 25 --report`

Expected: printed JSON assignments for the first 25 entries plus a warm cache file at `data/entry_topics_cache.json`.

- [ ] **Step 2: Generate approved assignments for the full dataset**

Run: `OPENAI_API_KEY=your_key_here python3 tools/tag_entries_openai.py --resume`

Expected: `data/entry_topics.json` populated with one object per devotional entry keyed by `mmdd`.

- [ ] **Step 3: Spot-check the output before regenerating the site**

Read and review these representative entries in `data/entry_topics.json`:

```json
{
  "0101": {
    "primary_topic": "grace",
    "topics": ["grace", "christ", "comfort"],
    "reader_needs": ["comfort", "assurance"]
  },
  "0415": {
    "primary_topic": "prayer",
    "topics": ["prayer", "faith", "guidance"],
    "reader_needs": ["guidance"]
  },
  "1214": {
    "primary_topic": "heaven",
    "topics": ["heaven", "comfort", "hope"],
    "reader_needs": ["comfort", "grief"]
  }
}
```

The exact slugs may differ, but confirm the overall shape matches the schema and the labels feel plausible.

- [ ] **Step 4: Regenerate the site with approved assignments**

Run: `python3 tools/generate_entry_pages.py`

Expected: topic pages now list meaningful entry sets rather than only the minimal test fixture output.

- [ ] **Step 5: Commit the approved topic assignments**

```bash
git add data/entry_topics.json entries explore sitemap.xml robots.txt data/routes.json
git commit -m "feat: publish explore topic assignments"
```
