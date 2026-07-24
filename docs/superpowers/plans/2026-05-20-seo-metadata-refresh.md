# SEO Metadata Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh metadata for better qualified search clicks from daily devotional readers while keeping the Lincoln connection as secondary credibility.

**Architecture:** Keep the existing static-site generator as the source of truth for generated entry and Explore metadata. Add small helper functions in `tools/generate_entry_pages.py` for reusable social metadata and clean text truncation, then regenerate static HTML.

**Tech Stack:** Static HTML/CSS/JS, Python 3 standard library, `unittest` tests in `tests/test_generate_entry_pages.py`.

---

## File Structure

- Modify `tools/generate_entry_pages.py`: add clean excerpt/social metadata helpers; update entry and Explore generated head tags.
- Modify `tests/test_generate_entry_pages.py`: add focused unit tests for clean description truncation and generated metadata.
- Modify generated HTML by running `python3 tools/generate_entry_pages.py`: updates `entries/*/index.html`, `explore/index.html`, `sitemap.xml`, `robots.txt`, and `data/routes.json` if generator output changes.
- Modify hand-authored static pages: `index.html`, `about.html`, `copyright.html`.

---

### Task 1: Add Clean Metadata Helper Tests

**Files:**
- Modify: `tests/test_generate_entry_pages.py`

- [ ] **Step 1: Add tests for clean description truncation and social metadata**

Add these test methods inside `GenerateEntryPagesTests`:

```python
    def test_build_description_truncates_at_word_boundary(self):
        entry = dict(self.entries[0])
        entry["bible_verse"] = (
            "This sentence has many carefully chosen words so the generated "
            "metadata excerpt should stop cleanly before cutting a word apart."
        )

        description = build_description(entry)

        self.assertLessEqual(len(description), 160)
        self.assertNotIn("apar...", description)
        self.assertTrue(description.endswith("..."))
        self.assertIn("metadata excerpt should stop cleanly", description)

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
                self.assertIn('<meta name="twitter:site" content="https://lincolndevotional.com/" />', html)
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m unittest tests/test_generate_entry_pages.py -v`

Expected: FAIL because `og:type`, `og:site_name`, and Twitter card metadata are not generated yet.

---

### Task 2: Implement Generator Metadata Helpers

**Files:**
- Modify: `tools/generate_entry_pages.py`

- [ ] **Step 1: Add helper constants and functions after `SITE_URL`**

```python
SITE_NAME = "The Believer's Daily Treasure"
HOMEPAGE_DESCRIPTION = (
    "A short daily Christian devotional with Scripture for every day, drawn from "
    "The Believer’s Daily Treasure, the devotional Abraham Lincoln carried."
)
EXPLORE_DESCRIPTION = "Browse 366 daily Christian devotions by topic and by today’s need."


def truncate_at_word_boundary(text, max_length):
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    cutoff = max_length - 3
    truncated = normalized[:cutoff].rsplit(" ", 1)[0].rstrip(" ,;:-")
    if not truncated:
        truncated = normalized[:cutoff].rstrip(" ,;:-")
    return f"{truncated}..."


def render_common_social_meta():
    return f'''<meta property="og:type" content="website" />
    <meta property="og:site_name" content="{escape(SITE_NAME)}" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:site" content="{SITE_URL}/" />'''
```

- [ ] **Step 2: Update `build_description` to use clean truncation**

Replace the current excerpt logic with:

```python
def build_description(entry):
    title = entry["title"].strip()
    date_text = entry["display_date"].strip()
    verse_ref = entry["verse_ref"].strip()
    bible_verse = entry["bible_verse"].strip()
    prefix = f"{date_text}: {title}. {verse_ref}. "
    excerpt = truncate_at_word_boundary(bible_verse, max(40, 160 - len(prefix)))
    return f"{prefix}{excerpt}"
```

- [ ] **Step 3: Add common metadata to generated Explore and entry heads**

In `render_explore_page`, replace the hard-coded description string with `{escape(EXPLORE_DESCRIPTION)}` and add `{render_common_social_meta()}` after `og:url`.

In `render_entry_page`, add `{render_common_social_meta()}` after `og:url`.

- [ ] **Step 4: Run tests and verify pass**

Run: `python3 -m unittest tests/test_generate_entry_pages.py -v`

Expected: PASS.

---

### Task 3: Refresh Hand-Authored Page Metadata

**Files:**
- Modify: `index.html`
- Modify: `about.html`
- Modify: `copyright.html`

- [ ] **Step 1: Update `index.html` head metadata**

Use:

```html
    <title>Daily Christian Devotional • The Believer's Daily Treasure</title>
    <link rel="canonical" href="https://lincolndevotional.com/" />
    <meta name="description" content="A short daily Christian devotional with Scripture for every day, drawn from The Believer’s Daily Treasure, the devotional Abraham Lincoln carried." />
    <meta property="og:title" content="Daily Christian Devotional • The Believer's Daily Treasure" />
    <meta property="og:description" content="A short daily Christian devotional with Scripture for every day, drawn from The Believer’s Daily Treasure, the devotional Abraham Lincoln carried." />
    <meta property="og:url" content="https://lincolndevotional.com/" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="The Believer's Daily Treasure" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:site" content="https://lincolndevotional.com/" />
```

- [ ] **Step 2: Update `about.html` head metadata**

Use:

```html
    <title>About The Believer's Daily Treasure • Lincoln's Devotional</title>
    <link rel="canonical" href="https://lincolndevotional.com/about.html" />
    <meta name="description" content="Learn about The Believer’s Daily Treasure, a restored daily Christian devotional associated with Abraham Lincoln and rooted in historic Scripture readings." />
    <meta property="og:title" content="About The Believer's Daily Treasure • Lincoln's Devotional" />
    <meta property="og:description" content="Learn about The Believer’s Daily Treasure, a restored daily Christian devotional associated with Abraham Lincoln and rooted in historic Scripture readings." />
    <meta property="og:url" content="https://lincolndevotional.com/about.html" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="The Believer's Daily Treasure" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:site" content="https://lincolndevotional.com/" />
```

- [ ] **Step 3: Update `copyright.html` head metadata**

Use:

```html
    <title>Copyright and Public Domain Notice • Lincoln's Devotional</title>
    <link rel="canonical" href="https://lincolndevotional.com/copyright.html" />
    <meta name="description" content="Copyright and public-domain notes for The Believer’s Daily Treasure, King James Version Scripture, ESV Scripture, and this devotional website." />
    <meta property="og:title" content="Copyright and Public Domain Notice • Lincoln's Devotional" />
    <meta property="og:description" content="Copyright and public-domain notes for The Believer’s Daily Treasure, King James Version Scripture, ESV Scripture, and this devotional website." />
    <meta property="og:url" content="https://lincolndevotional.com/copyright.html" />
    <meta property="og:type" content="website" />
    <meta property="og:site_name" content="The Believer's Daily Treasure" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:site" content="https://lincolndevotional.com/" />
```

---

### Task 4: Regenerate Static Pages and Verify SEO Output

**Files:**
- Modify generated static HTML under `entries/`
- Modify generated `explore/index.html`

- [ ] **Step 1: Regenerate generated pages**

Run: `python3 tools/generate_entry_pages.py`

Expected: command exits with status 0.

- [ ] **Step 2: Run unit tests**

Run: `python3 -m unittest tests/test_generate_entry_pages.py -v`

Expected: PASS.

- [ ] **Step 3: Run metadata audit**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import html
import re

root = Path('.')
files = list((root / 'entries').glob('*/index.html'))
titles = {}
descriptions = {}
missing = []
for path in files:
    text = path.read_text(encoding='utf-8')
    title_match = re.search(r'<title>(.*?)</title>', text)
    desc_match = re.search(r'<meta name="description" content="(.*?)"', text)
    title = html.unescape(title_match.group(1)) if title_match else ''
    desc = html.unescape(desc_match.group(1)) if desc_match else ''
    if not title or not desc or 'rel="canonical"' not in text or 'property="og:url"' not in text:
        missing.append(str(path))
    titles.setdefault(title, []).append(path)
    descriptions.setdefault(desc, []).append(path)

duplicate_titles = [value for value in titles.values() if len(value) > 1]
duplicate_descriptions = [value for value in descriptions.values() if len(value) > 1]
print('entry_pages', len(files))
print('missing_core_meta', len(missing))
print('duplicate_titles', len(duplicate_titles))
print('duplicate_descriptions', len(duplicate_descriptions))
assert len(files) == 366
assert not missing
assert not duplicate_titles
assert not duplicate_descriptions
PY
```

Expected output includes:

```text
entry_pages 366
missing_core_meta 0
duplicate_titles 0
duplicate_descriptions 0
```

---

## Self-Review

- Spec coverage: homepage/about/copyright metadata, generated entry descriptions, generated social tags, and Explore non-landing-page decision are covered.
- Placeholder scan: no `TBD`, `TODO`, or undefined implementation steps remain.
- Type consistency: helper names are consistent across tests and implementation steps.
