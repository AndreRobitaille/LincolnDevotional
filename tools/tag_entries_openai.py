from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parent.parent
ENTRIES_PATH = ROOT / "data" / "entries.json"
TOPIC_TAXONOMY_PATH = ROOT / "data" / "topic_taxonomy.json"
ENTRY_TOPICS_PATH = ROOT / "data" / "entry_topics.json"
CACHE_PATH = ROOT / "data" / "entry_topics_cache.json"
MODEL = "gpt-5-mini"


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_allowed_topic_map(topic_taxonomy):
    return {topic["slug"]: topic for topic in topic_taxonomy.get("topics", [])}


def build_allowed_reader_needs_map(topic_taxonomy):
    return {need["slug"]: need for need in topic_taxonomy.get("reader_needs", [])}


def _build_allowed_topic_name_map(allowed_topics):
    return {
        _normalize_topic_text(topic["name"]): slug
        for slug, topic in allowed_topics.items()
        if isinstance(topic.get("name"), str)
    }


def _normalize_topic_text(value):
    return value.strip().casefold()


def _dedupe_preserve_order(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _normalize_topic_value(value):
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        slug = value.get("slug")
        if isinstance(slug, str):
            return slug.strip()
        name = value.get("name")
        if isinstance(name, str):
            return name.strip()
    raise ValueError(f"Unsupported topic value: {value!r}")


def _coerce_assignment_for_generation(assignment):
    coerced = dict(assignment)
    primary_topic = coerced.get("primary_topic")
    if isinstance(primary_topic, dict):
        coerced["primary_topic"] = primary_topic.get("slug") or primary_topic.get("name") or primary_topic

    raw_topics = coerced.get("topics", [])
    if not isinstance(raw_topics, list):
        raw_topics = [raw_topics]

    topics = []
    for topic in raw_topics:
        if isinstance(topic, str):
            topics.append(topic)
        elif isinstance(topic, dict):
            slug = topic.get("slug")
            name = topic.get("name")
            if isinstance(slug, str):
                topics.append(slug)
            elif isinstance(name, str):
                topics.append(name)
    coerced["topics"] = topics

    reader_needs = []
    raw_reader_needs = coerced.get("reader_needs", [])
    if not isinstance(raw_reader_needs, list):
        raw_reader_needs = [raw_reader_needs]
    for need in raw_reader_needs:
        if isinstance(need, str):
            reader_needs.append(need)
        elif isinstance(need, dict):
            slug = need.get("slug")
            name = need.get("name")
            if isinstance(slug, str):
                reader_needs.append(slug)
            elif isinstance(name, str):
                reader_needs.append(name)
    coerced["reader_needs"] = reader_needs
    return coerced


def _sanitize_optional_reader_needs(assignment, allowed_topics, allowed_reader_needs=None):
    sanitized = dict(assignment)
    reader_needs = []
    for need in assignment.get("reader_needs", []):
        try:
            reader_needs.append(normalize_assignment({"primary_topic": assignment["primary_topic"], "topics": [], "reader_needs": [need]}, allowed_topics, allowed_reader_needs)["reader_needs"][0])
        except (KeyError, ValueError, IndexError, TypeError):
            continue
    sanitized["reader_needs"] = reader_needs
    return sanitized


def normalize_assignment(assignment, allowed_topics, allowed_reader_needs=None):
    # When no separate reader-needs vocabulary is provided, fall back to validating
    # reader_needs against topics — preserves legacy taxonomy shape.
    effective_reader_needs = allowed_reader_needs if allowed_reader_needs is not None else allowed_topics
    allowed_topic_names = _build_allowed_topic_name_map(allowed_topics)
    allowed_reader_need_names = _build_allowed_topic_name_map(effective_reader_needs)

    def resolve_topic(value):
        topic_value = _normalize_topic_value(value)
        if topic_value in allowed_topics:
            return topic_value
        normalized_value = _normalize_topic_text(topic_value)
        if normalized_value in allowed_topic_names:
            return allowed_topic_names[normalized_value]
        raise ValueError(f"Unknown topic value: {topic_value}")

    def resolve_reader_need(value):
        need_value = _normalize_topic_value(value)
        if need_value in effective_reader_needs:
            return need_value
        normalized_value = _normalize_topic_text(need_value)
        if normalized_value in allowed_reader_need_names:
            return allowed_reader_need_names[normalized_value]
        raise ValueError(f"Unknown reader_need value: {need_value}")

    primary_topic = resolve_topic(assignment["primary_topic"])
    if primary_topic not in allowed_topics:
        raise ValueError(f"Unknown primary_topic: {primary_topic}")

    raw_topics = assignment.get("topics", [])
    if not isinstance(raw_topics, list):
        raw_topics = [raw_topics]
    topics = [resolve_topic(topic) for topic in raw_topics]
    raw_reader_needs = assignment.get("reader_needs", [])
    if not isinstance(raw_reader_needs, list):
        raw_reader_needs = [raw_reader_needs]
    reader_needs = [resolve_reader_need(need) for need in raw_reader_needs]

    for topic in topics:
        if topic not in allowed_topics:
            raise ValueError(f"Unknown topic: {topic}")
    for need in reader_needs:
        if need not in effective_reader_needs:
            raise ValueError(f"Unknown reader_need: {need}")

    topics = _dedupe_preserve_order([primary_topic, *topics])
    reader_needs = _dedupe_preserve_order(reader_needs)
    return {"primary_topic": primary_topic, "topics": topics, "reader_needs": reader_needs}


def write_assignments(path, assignments):
    path.write_text(json.dumps(assignments, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_cache():
    if not CACHE_PATH.exists():
        return {}
    return load_json(CACHE_PATH)


def write_cache(cache):
    write_assignments(CACHE_PATH, cache)


def _format_vocab_lines(items):
    lines = []
    for item in items:
        slug = item.get("slug", "")
        description = item.get("description", "").strip()
        lines.append(f"- {slug}: {description}")
    return "\n".join(lines)


def build_prompt(entry, topic_taxonomy):
    topics = topic_taxonomy.get("topics", [])
    reader_needs = topic_taxonomy.get("reader_needs", [])
    topic_lines = _format_vocab_lines(topics)
    need_lines = _format_vocab_lines(reader_needs) if reader_needs else "(none defined)"
    entry_payload = {
        "display_date": entry.get("display_date"),
        "title": entry.get("title"),
        "verse_ref": entry.get("verse_ref"),
        "bible_verse": entry.get("bible_verse"),
        "poem": entry.get("poem"),
    }
    return (
        "You are tagging a daily Christian devotional for a reader-browse experience. "
        "Be selective and discriminating, not generous.\n\n"
        "Rules:\n"
        "1. primary_topic: the SINGLE topic that is the dominant theological theme of THIS specific entry. "
        "Do not default to grace or faith unless the entry is genuinely about that doctrine.\n"
        "2. topics: an array containing primary_topic plus AT MOST ONE additional topic, only if it is a major "
        "secondary theme (not merely mentioned). Most entries should have exactly 1 topic; very few should have 2; "
        "never more than 2.\n"
        "3. reader_needs: an array of AT MOST 2 needs that name what a reader in spiritual distress would seek today, "
        "only when the entry actually speaks to that need. Empty array is acceptable and often correct. "
        "Do not include topic slugs in reader_needs.\n"
        "4. Use only the slugs from the allowed lists below. Return slugs, not display names.\n\n"
        f"Allowed topics:\n{topic_lines}\n\n"
        f"Allowed reader_needs:\n{need_lines}\n\n"
        "Return only a valid JSON object with keys primary_topic, topics, and reader_needs. "
        "No markdown, no prose, no code fences, no extra keys.\n\n"
        f"Entry to tag: {json.dumps(entry_payload, ensure_ascii=False)}"
    )


def fetch_assignment(entry, topic_taxonomy, api_key, timeout=180, max_retries=2):
    payload = json.dumps({
        "model": MODEL,
        "input": build_prompt(entry, topic_taxonomy),
        "text": {"format": {"type": "json_object"}},
    }).encode("utf-8")
    last_error = None
    for attempt in range(max_retries + 1):
        req = request.Request(
            "https://api.openai.com/v1/responses",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (TimeoutError, OSError) as err:
            last_error = err
            if attempt < max_retries:
                continue
            raise
    raise last_error


def extract_response_text(response_payload):
    for output_item in response_payload.get("output", []):
        if output_item.get("type") != "message":
            continue
        for content_item in output_item.get("content", []):
            if content_item.get("type") in {"output_text", "text"}:
                text = content_item.get("text", "")
                if text:
                    return text
    raise ValueError("OpenAI Responses payload did not contain text output")


def parse_assignment_response(response_payload):
    text = extract_response_text(response_payload)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Parsed assignment must be a JSON object")
    return parsed


def select_entries(entries, limit):
    return entries[:limit] if limit is not None else entries


def _sample_assignment(index, allowed_topics, allowed_reader_needs=None):
    slugs = list(allowed_topics)
    primary = slugs[index % len(slugs)]
    secondary = slugs[(index + 1) % len(slugs)] if len(slugs) > 1 else primary
    need_slugs = list(allowed_reader_needs) if allowed_reader_needs else []
    reader_need = [need_slugs[index % len(need_slugs)]] if need_slugs else []
    return {"primary_topic": primary, "topics": [primary, secondary], "reader_needs": reader_need}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--entry", action="append", default=[])
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Skip entries that already have assignments")
    args = parser.parse_args(argv)

    entries = load_json(ENTRIES_PATH)
    topic_taxonomy = load_json(TOPIC_TAXONOMY_PATH)
    allowed_topics = build_allowed_topic_map(topic_taxonomy)
    allowed_reader_needs = build_allowed_reader_needs_map(topic_taxonomy)
    selected = select_entries(entries, args.limit)
    if args.entry:
        selected_mmdd = set(args.entry)
        selected = [entry for entry in entries if entry["mmdd"] in selected_mmdd]
    assignments = load_json(ENTRY_TOPICS_PATH) if ENTRY_TOPICS_PATH.exists() else {}
    cache = load_cache()
    if args.resume:
        selected = [entry for entry in selected if entry["mmdd"] not in assignments]

    if not args.dry_run and not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required")

    for index, entry in enumerate(selected):
        if args.dry_run:
            raw_assignment = _sample_assignment(index, allowed_topics, allowed_reader_needs)
        else:
            api_response = fetch_assignment(entry, topic_taxonomy, os.environ["OPENAI_API_KEY"])
            raw_assignment = parse_assignment_response(api_response)
        sanitized = _coerce_assignment_for_generation(raw_assignment)
        sanitized = _sanitize_optional_reader_needs(sanitized, allowed_topics, allowed_reader_needs)
        normalized = normalize_assignment(sanitized, allowed_topics, allowed_reader_needs)
        assignments[entry["mmdd"]] = normalized
        cache[entry["mmdd"]] = normalized
        if args.report:
            print(json.dumps(normalized, sort_keys=True))
        # Incremental save so a mid-loop crash never loses more than the current entry.
        if not args.dry_run:
            write_assignments(ENTRY_TOPICS_PATH, assignments)
            write_cache(cache)

    if not args.dry_run:
        write_assignments(ENTRY_TOPICS_PATH, assignments)
        write_cache(cache)


if __name__ == "__main__":
    main()
