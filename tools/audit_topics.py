"""Audit approved topic assignments without writing files or using APIs."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MAX_PASSAGES_PER_TAG = 25
MAX_TAG_WORDS = 3


def _assignment_slugs(items, label):
    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        raise ValueError(f"{label} must be an array of slugs")
    if len(items) != len(set(items)):
        raise ValueError(f"{label} contains duplicate slugs")
    return set(items)


def _vocabulary(items, label):
    if not isinstance(items, list) or not items:
        raise ValueError(f"{label} must be a nonempty array")
    slugs = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"{label} contains an invalid record")
        slug, name = item.get("slug"), item.get("name")
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError(f"{label} contains an empty slug")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{label} contains an empty name")
        if len(name.split()) > MAX_TAG_WORDS:
            raise ValueError(
                f"{label} label {name!r} exceeds the {MAX_TAG_WORDS}-word maximum"
            )
        slugs.append(slug)
    if len(slugs) != len(set(slugs)):
        raise ValueError(f"{label} contains duplicate slugs")
    return set(slugs)


def validate_taxonomy(taxonomy):
    if not isinstance(taxonomy, dict):
        raise ValueError("Taxonomy must be a JSON object")
    topics = _vocabulary(taxonomy.get("topics"), "Topics")
    needs = _vocabulary(taxonomy.get("reader_needs"), "Reader needs")
    if topics & needs:
        raise ValueError("A slug cannot appear in both facets")
    return topics, needs


def validate(taxonomy, assignments, entries, *, require_used_tags=True):
    """Count full membership, including secondary topics and both facets."""
    if not isinstance(taxonomy, dict) or not isinstance(assignments, dict):
        raise ValueError("Taxonomy and assignments must be JSON objects")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Entries must be a nonempty array")
    entry_keys = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("mmdd"), str):
            raise ValueError("Each entry must have a string mmdd")
        entry_keys.append(entry["mmdd"])
    if len(entry_keys) != len(set(entry_keys)):
        raise ValueError("Entries contain duplicate dates")
    missing = set(entry_keys) - set(assignments)
    extra = set(assignments) - set(entry_keys)
    if missing or extra:
        raise ValueError(f"Assignment coverage differs: missing={sorted(missing)}, extra={sorted(extra)}")

    topics, needs = validate_taxonomy(taxonomy)
    topic_counts = Counter()
    need_counts = Counter()
    primary_counts = Counter()
    for mmdd, assignment in assignments.items():
        if not isinstance(assignment, dict):
            raise ValueError(f"{mmdd}: assignment must be an object")
        primary = assignment.get("primary_topic")
        if not isinstance(primary, str) or primary not in topics:
            raise ValueError(f"{mmdd}: missing or unknown primary topic")
        assigned_topics = _assignment_slugs(assignment.get("topics"), f"{mmdd} topics")
        assigned_needs = _assignment_slugs(
            assignment.get("reader_needs"), f"{mmdd} reader needs"
        )
        if primary not in assigned_topics:
            raise ValueError(f"{mmdd}: primary topic must be in topics")
        if len(assigned_topics) > 2 or len(assigned_needs) > 2:
            raise ValueError(f"{mmdd}: at most two topics and two reader needs are allowed")
        if assigned_topics - topics or assigned_needs - needs:
            raise ValueError(f"{mmdd}: unknown or misplaced tag")
        topic_counts.update(assigned_topics)
        need_counts.update(assigned_needs)
        primary_counts[primary] += 1

    for facet, vocabulary, counts in (
        ("Topic", topics, topic_counts), ("Reader need", needs, need_counts),
    ):
        for slug in sorted(vocabulary):
            count = counts[slug]
            if count == 0 and require_used_tags:
                raise ValueError(f"{facet} {slug} has no passages")
            if count > MAX_PASSAGES_PER_TAG:
                raise ValueError(
                    f"{facet} {slug} has {count} passages; maximum is {MAX_PASSAGES_PER_TAG}"
                )
    return {
        "entries": len(entries),
        "topics": len(topics),
        "reader_needs": len(needs),
        "largest_topic": max(topic_counts.values(), default=0),
        "largest_reader_need": max(need_counts.values(), default=0),
        "entries_with_secondary_topics": sum(
            len(assignment["topics"]) == 2 for assignment in assignments.values()
        ),
        "topic_counts": dict(sorted(topic_counts.items())),
        "need_counts": dict(sorted(need_counts.items())),
        "primary_counts": dict(sorted(primary_counts.items())),
    }


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taxonomy", type=Path, default=ROOT / "data/topic_taxonomy.json")
    parser.add_argument("--assignments", type=Path, default=ROOT / "data/entry_topics.json")
    parser.add_argument("--entries", type=Path, default=ROOT / "data/entries.json")
    args = parser.parse_args(argv)
    try:
        report = validate(
            load_json(args.taxonomy), load_json(args.assignments), load_json(args.entries),
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"Topic audit failed: {error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
