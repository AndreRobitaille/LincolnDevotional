# SEO Metadata Refresh Design

## Goal

Improve the site’s metadata so search snippets invite qualified clicks from people looking for a usable daily Christian devotional, while preserving the Lincoln connection as a credibility hook rather than the primary promise.

## Audience and Search Intent

The primary visitor is looking for a daily Christian devotional resource: Scripture, short reflection, and an entry for each day. The secondary visitor is interested because this is associated with Abraham Lincoln and *The Believer’s Daily Treasure*. Metadata should speak first to devotional usefulness and second to historical provenance.

## Scope

- Refresh homepage metadata to lead with daily devotional usefulness.
- Give About and Copyright pages distinct descriptions, canonicals, and Open Graph tags.
- Add common social metadata that improves previews without adding SEO-only pages.
- Improve generated entry descriptions so excerpts stop at clean word boundaries instead of awkward mid-word truncation.
- Keep Explore filters as UX state, not standalone SEO landing pages.

## Non-Goals

- Do not generate topic or reader-need landing pages.
- Do not add filtered Explore URLs to the sitemap.
- Do not chase broad impressions at the expense of click quality.
- Do not change page layout or visible page content unless required to keep metadata accurate.

## Metadata Direction

Homepage metadata should communicate: “a short daily Christian devotional with Scripture for every day,” then mention that it is drawn from the devotional Abraham Lincoln carried.

Entry pages should keep their specific date, title, Scripture reference, and verse excerpt because those are meaningful for searchers and for link previews. The excerpt builder should truncate cleanly at a word boundary and keep descriptions in a normal search-snippet range.

About metadata should emphasize the restored historical devotional and Lincoln connection. Copyright metadata should emphasize public-domain and source/copyright clarity.

Explore metadata should remain a single browse page: useful for visitors who arrive on the site, not an index of topic pages for search engines.

## Validation

- Unit tests should verify generated entry descriptions truncate cleanly.
- Unit tests should verify generated entry and Explore pages include the common social metadata.
- A metadata audit should confirm all generated entry pages still have unique titles/descriptions and core tags.
- Regenerating the static pages should update the committed HTML consistently.
