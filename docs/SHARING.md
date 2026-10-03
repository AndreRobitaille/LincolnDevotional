# Sharing previews

The site serves **367 pre-rendered PNGs**: one for each of the 366 calendar dates,
including February 29, and one evergreen site card. They live in
`assets/og/v1/`. Filenames follow the entry routes: `october-3.png`,
`february-29.png`, and `site.png`. `manifest.json` records each image's headline,
date, layout bounds, and checksums.

Images are ordinary static files. Sharing a link triggers no rendering, AI call,
API request, or background job on this site. Generation uses local Python and
Pillow; the AI image-generation cost is **$0**. The initial PNG set totals about
17.5 MiB, with individual files between 35 and 62 KiB. Hosting bandwidth follows
the existing hosting plan.

## Design and editorial choices

Cards are 1200 × 630 pixels. Ivory lettering (`#fff9ec`) sits on navy (`#102432`),
wine (`#422238`), or green (`#143b31`). Text contrast exceeds 11:1 in every palette.
The existing Lincoln profile has an added stovepipe hat so it remains recognizable
at thumbnail size. The card contains a short headline and a date; detailed
Scripture, references, and site copy belong in the accompanying metadata.

Headlines use Newsreader at 104–148 pixels and dates use Inter at 72 pixels.
Headlines occupy at most three lines. All text and the silhouette stay inside a
centered square crop. At 360px image width, even the minimum headline size is
about 31px. Platform layouts and cropping can vary.

`data/share_headlines.json` contains a separately edited headline for every date.
These phrases were reviewed against **all 366 original titles, KJV passages,
and poems** on October 3, 2026. They are promotional summaries; the original
book titles and devotional text remain intact. There is no automatic two-word
cutoff. For example:

| Date | Card headline | Detail retained |
| --- | --- | --- |
| September 2 | God Does Not Tempt to Sin | The negation and its object |
| September 23 / 24 | Kept from Temptation / Kept in Temptation | Two different forms of preservation |
| April 2–5 | Works for God's Glory / Works Like Christ's / Works by Christ's Grace / Works in Christ's Name | The qualification of each day's good works |
| August 30 | Past Mercies in Affliction | Both the past mercies and their context |
| November 22 / 23 | Being with Christ / Ever with Christ | The added permanence in the second entry |

Each record stores the original title and a SHA-256 fingerprint of its title,
reference, KJV text, and poem. A source edit fails validation until the headline
is reviewed and its stored fingerprint is updated. This detects stale editorial
review; it does not automate judgment about meaning.

## Metadata and general pages

All **370 public pages** include metadata in their original HTML, available
without JavaScript:

- `og:title`, `og:description`, `og:url`, `og:type`, `og:site_name`, and `og:locale`.
- An absolute HTTPS `og:image`, its PNG type, width, height, and descriptive alt text.
- `twitter:card=summary_large_image`, title, description, image, and image alt text.
- A canonical URL matching `og:url`, plus existing favicon and Apple touch icon links.

Daily pages use their own image. Their social title combines the date with the
**full original title**; the description contains the date, title, reference,
and a word-boundary-truncated KJV excerpt, limited to 160 characters. SEO document
titles retain the title format introduced by PR #11.

The homepage, About, Copyright, and Explore use `site.png` with “Lincoln's
Devotional” and “Daily readings.” Each keeps its own page title and description
in the surrounding share preview. Explore's query filters use the same evergreen
card. The homepage is a changing daily reader, so its share card is evergreen;
the “Share this devotion” link points to the stable dated entry instead.

The generator refreshes a marked block in each hand-maintained general page from
that page's existing `og:title` and `og:description`. Edit those source tags and
the normal description when changing editorial copy, then regenerate. Do not
edit the marked generated block by hand. No social account handle or invented
publication timestamp is added.

## Regenerate and validate

The website itself has no build or Python dependency. These are maintenance
commands for producing files that are committed and uploaded with the site:

```bash
python3 -m pip install -r tools/share_requirements.txt
python3 tools/generate_entry_pages.py
python3 tools/generate_share_images.py
python3 -m unittest tests.test_generate_entry_pages tests.test_tag_entries_openai tests.test_share_images
python3 tools/generate_share_images.py --check
```

Use the pinned Pillow version for reproducible rasterization. CI uses Python
3.14 and runs both the tests and image checker before the existing FTPS step.
Pull requests validate without uploading. Generation needs no network access
after installing Pillow. Commit the generated HTML, PNGs, manifest, source
headlines, tools, and any changed sitemap files together.

The tests cover all dates and all page metadata, type size, square-crop bounds,
contrast, PNG dimensions, source fingerprints, and file checksums. They also
exercise missing files, a changed pixel, stale inputs, and source edits. The
`--check` command independently renders every expected card in memory and
compares its decoded pixels with the committed PNG, without writing files.

For a source edit, review the proposed phrase against the title, KJV passage,
and poem before updating `source_title` and `source_sha256` in the headline
record. The fingerprint helper is `tools.social_meta.source_fingerprint(entry)`.
Do not refresh fingerprints in bulk without reviewing the changed entries.
If a heading no longer fits, shorten it thoughtfully; the renderer fails rather
than reducing it below the minimum type size.

Before publishing changes to an already published image set, change
`IMAGE_VERSION` in `tools/social_meta.py` to the next version (for example `v2`),
then run both generators. This produces new image URLs while keeping manageable
date-based filenames. Keep old published version directories available for
existing cached previews until they can be retired deliberately.

## Source artwork and fonts

`tools/share_assets/` contains the variable Newsreader and Inter font files,
their SIL Open Font License notices, and the hat profile in SVG and transparent
PNG forms. Fonts came from the official Google Fonts repository. The profile is
derived from this repository's `icon.svg`; the original favicon is unchanged.
The renderer uses the bundled PNG so Chromium and SVG rendering tools are not
required for generation. After editing the SVG, rebuild its raster source with:

```bash
rsvg-convert --width 264 --height 368 tools/share_assets/lincoln-stovepipe.svg \
  -o tools/share_assets/lincoln-stovepipe.png
```

Then regenerate and inspect the cards at 360px and 240px wide, as well as a
centered square crop. During the initial implementation, monthly contact sheets
covering every date were inspected at 240px wide, with larger examples checked
at 360px. Those temporary QA artifacts are under ignored `tmp/og-review/proofs/`.

## After deployment

The PNG is already available when a sharing service requests it; preview timing
depends on the platform's fetches and caches. It is not a per-share generation
delay. Check a normal entry, February 29, a long heading, and the homepage using
the platform's preview inspector after release. Confirm the new public PNG URLs
return HTTP 200 and `image/png`, and that crawlers can reach them without login.
The local HTTP server cannot validate cPanel's Apache configuration.

Old previews may persist until a platform refreshes its cache. Slack documents
a roughly 30-minute global preview cache; Meta requires a changed image URL to
reliably request replacement artwork. Versioned directories support that change.
The metadata follows the [Open Graph protocol](https://ogp.me/), with thumbnail
readability informed by [Apple's rich-preview guidance](https://developer.apple.com/documentation/technotes/tn3156-create-rich-previews-for-messages).
See also [Slack's crawler behavior](https://api.slack.com/robots),
[Meta's sharing guidance](https://developers.facebook.com/docs/sharing/webmasters/),
and [LinkedIn's image guidance](https://www.linkedin.com/help/linkedin/answer/a521928).
