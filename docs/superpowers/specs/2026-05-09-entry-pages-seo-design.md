# Entry Pages for SEO and Crawlability Design

## Goal

Improve SEO by giving each devotional entry a stable, crawlable, shareable URL with full content rendered in static HTML. A secondary goal is improving AI/LLM crawlability and citation by exposing entry content in predictable, non-JavaScript-dependent pages.

## Current State

- `index.html` is the main devotional landing page.
- `script.js` loads devotional content from `data/entries.json` and `data/esv_cache.json` at runtime.
- There is no sitemap.
- There are no dedicated per-entry HTML pages.
- Current devotional rendering depends on JavaScript, which weakens crawlability and makes direct indexing of individual entries less reliable.

## Chosen Approach

Generate one static HTML page per devotional entry under a readable path such as:

- `/entries/january-1/`

Keep the current homepage as the “today” experience, but add generated entry pages as canonical destinations for indexing and sharing.

## Alternatives Considered

### 1. Static page per entry (chosen)

- Best SEO outcome
- Best AI/LLM crawlability outcome
- Supports sitemap inclusion cleanly
- Allows unique metadata per devotional
- Adds generation and output files, but keeps runtime simple and reliable

### 2. Single entry template with path/query-driven JavaScript

- Fewer generated files
- Shareable links possible
- Still weaker for search and crawlability because primary content remains more dependent on runtime behavior

### 3. Query/hash URLs on the existing homepage

- Easiest to add
- Weakest indexing result
- Not aligned with the primary SEO goal

## URL Strategy

Use human-readable slugs based on the devotional date, for example:

- `january-1`
- `february-14`
- `december-31`

These slugs should be deterministic and generated from existing date data. The entry page URL should be the canonical URL for that devotional.

## Architecture

### Homepage

- Keep `index.html` as the main landing page for today’s devotional experience.
- Continue allowing date selection and current JS-driven navigation there.
- Add a visible link from the homepage’s currently displayed devotional to that devotional’s dedicated entry page.

### Entry Pages

Generate static files at paths like:

- `entries/january-1/index.html`

Each entry page should contain the devotional content directly in the HTML source, without depending on `script.js` for the main content.

### Generator

Add a Python generator script, expected at:

- `tools/generate_entry_pages.py`

Responsibilities:

- Read `data/entries.json`
- Read `data/esv_cache.json`
- Generate one entry page per devotional
- Generate `sitemap.xml`
- Optionally generate `robots.txt` if the site does not already have one
- Validate required fields and guard against duplicate slugs

## Entry Page Content Structure

Each generated entry page should include:

- devotional title
- display date
- KJV verse text
- verse reference
- optional ESV verse text when available
- poem text
- homepage link
- previous devotional link
- next devotional link

The content should be present as plain HTML in the page source so that crawlers and LLM systems can retrieve it without executing JavaScript.

## Metadata Requirements

Each entry page should have unique metadata:

- `<title>`
- meta description
- canonical URL
- Open Graph title
- Open Graph description
- Open Graph URL

The entry page should be self-canonical. It should not canonicalize to the homepage.

The homepage should remain canonical to itself as the landing page.

## Internal Linking

Phase 1 internal linking should include:

- homepage → dedicated entry page for the displayed devotional
- entry page → homepage
- entry page → previous devotional
- entry page → next devotional

This improves crawl depth and makes the generated entry set easier to discover.

An archive/index page may be added later, but it is not required for phase 1.

## Sitemap and Robots

Generate a `sitemap.xml` that includes:

- homepage
- about page
- copyright page
- every generated devotional entry page

If `robots.txt` is absent, add one that references the sitemap.

## Styling and Frontend Behavior

- Generated entry pages should visually match the current site as closely as practical.
- Reuse existing shared CSS.
- `theme.js` may still run on generated entry pages for light/dark mode.
- Avoid loading `script.js` on generated entry pages unless needed for non-content behavior, since the main devotional content must already be present in HTML.

## Error Handling and Data Rules

- Fail generation if required devotional fields are missing.
- Fail generation if slug creation would produce duplicates.
- Do not fail the whole build if ESV content is missing for one entry; omit that section for the affected page.
- Emit clear generator output so data issues are easy to fix.

## Verification

Verification should be manual and script-based:

1. Run the generator.
2. Confirm `sitemap.xml` exists and contains entry URLs.
3. Open a few generated pages locally.
4. Confirm page source contains devotional content without requiring JS execution.
5. Confirm metadata varies per entry.
6. Confirm canonical URLs point to each entry page itself.
7. Confirm previous/next links work.

## Non-Goals for Phase 1

- Replacing the current homepage experience
- Adding a full archive browsing UX
- Introducing a build system or framework
- Converting the whole site to server-side rendering

## Implementation Boundaries

This work should stay within the project’s existing static-site model:

- static HTML output
- shared CSS/JS assets where useful
- Python tooling in `tools/`
- existing JSON data as the source of truth

No build pipeline or framework migration is required.

## Recommendation Summary

Implement dedicated static devotional entry pages at readable URLs, generate them from existing JSON data, and publish them in a sitemap. This is the strongest fit for the project’s static architecture and the clearest path to better SEO, crawlability, and stable citation targets.
