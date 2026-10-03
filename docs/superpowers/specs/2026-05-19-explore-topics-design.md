# Explore Topics and Reader Discovery Design

## Goal

Improve reader exploration without disrupting the site’s current daily-reading flow.

The primary objective is to help visitors find relevant devotionals when they arrive with a need, question, or spiritual concern rather than a date. A secondary objective is to improve SEO by creating meaningful, crawlable topic hubs and stronger internal linking between entries.

## Current State

- `index.html` is the main reading experience and focuses on the devotional for the current date.
- Static entry pages already exist at stable URLs under `/entries/<month>-<day>/`.
- The site already has foundational SEO elements including canonicals, sitemap, robots.txt, and per-entry metadata.
- There is no archive, topic system, browse hub, or search experience.
- `data/entries.json` already contains a strong topical signal through entry titles, verse references, verse text, and poems.

## Audience and Usage Model

The topic system should be designed around how real visitors are likely to use the site.

### Primary audience patterns

1. **Daily reader**
   - Wants today’s devotion and light navigation to nearby days.
   - Should not be forced into a browse-heavy experience.

2. **Reader in a particular need**
   - Arrives looking for comfort, peace, hope, guidance, strength, forgiveness, help in temptation, patience, or assurance.
   - Needs a simple browse path that does not require theological vocabulary.

3. **Historically or spiritually curious visitor**
   - Wants to understand what kind of devotional themes this book covers.
   - Benefits from structured exploration.

4. **Study-oriented visitor**
   - Wants to browse themes like Christ, redemption, Scripture, affliction, prayer, heaven, or the Holy Spirit.
   - Benefits from stable theme pages and internal links.

### Product conclusion

The system should be **browse-first**, not search-first.

Search may be added later, but the first version should focus on a guided exploration model that works for readers who know what they feel or need, not only readers who know exactly what term to search.

## Chosen Approach

Add a new static **Explore** page that organizes devotionals into topic-based browse paths, led by reader needs first and backed by a controlled taxonomy.

The implementation should use:

- a curated taxonomy file
- an AI-assisted tagging workflow constrained to approved topics
- generated static topic pages
- topic chips on devotional entry pages

This preserves the current static-site architecture while adding a much more useful exploration layer.

## Alternatives Considered

### 1. Full-text search first

- Useful eventually
- Less helpful as the primary experience for readers who arrive with a spiritual need but no exact query
- Adds interface complexity before a good taxonomy exists
- Better as a later enhancement once topics and tags are established

### 2. Pure theological taxonomy

- Accurate and useful for study-oriented visitors
- Less natural for readers arriving with needs like grief, fear, temptation, or discouragement
- Risks making the site feel more academic than devotional

### 3. Open-ended AI-generated tags

- Fast to generate initially
- High risk of inconsistency, duplication, and low editorial quality
- Weak fit for a static browsing system because free-form tag drift quickly creates clutter

### 4. Browse-first controlled taxonomy (chosen)

- Best fit for real visitor behavior
- Supports both devotional browsing and structured study
- Produces stable, reviewable pages and labels
- Creates good internal linking and SEO value

## Information Architecture

### Main navigation

Add an **Explore** link to the primary site navigation.

The homepage should remain centered on today’s devotion. Explore should be a clearly available path, not a replacement for the existing landing-page behavior.

### Explore page

Create a new static page at:

- `/explore/`

This page should be the main discovery hub.

It should contain three browse sections, in this order:

#### 1. Find a devotion for today’s need

Examples:

- Comfort
- Peace
- Hope
- Guidance
- Strength
- Forgiveness
- Temptation
- Grief
- Patience
- Assurance

This section should lead because it is the most intuitive path for many visitors.

#### 2. Grow in the Christian life

Examples:

- Prayer
- Faith
- Obedience
- Thanksgiving
- Holiness
- Repentance
- Good works
- Love of neighbor

This section supports devotional practice and discipleship-oriented browsing.

#### 3. Study by theme

Examples:

- Christ
- Grace
- Redemption
- Scripture
- The Holy Spirit
- Heaven
- Death and resurrection
- Providence

This section supports historical, theological, and study-oriented use.

### Explore page card behavior

Each topic card or list item should include:

- topic name
- brief description
- optional entry count if it improves scanability without visual clutter

The page should remain simple and clearly readable. It should not feel like a faceted search application.

## Topic Pages

Generate one static page per topic or need, using URLs like:

- `/explore/comfort/`
- `/explore/prayer/`
- `/explore/christ/`

Each topic page should include:

- page title
- short introductory blurb
- list of matching devotional entries
- each entry displayed as date, title, and short verse excerpt
- link back to the Explore hub
- optional related-topic links

The topic page should function as both:

- a useful human browse page
- a crawlable SEO landing page for the theme

## Entry Page Integration

Each static devotional entry page should include small linked topic chips.

Example:

- Comfort
- Prayer
- Affliction

These chips should link back to the relevant topic pages and help readers continue exploring from a page they already found meaningful.

This creates a natural loop:

- homepage → Explore
- Explore → topic page
- topic page → devotional entry
- devotional entry → related topic page

## Taxonomy Strategy

The system should use a **controlled taxonomy**, not free-form tags.

The taxonomy should prioritize labels that are understandable to ordinary readers while still supporting theological structure.

### Recommended taxonomy layers

#### Reader needs

Examples:

- comfort
- peace
- hope
- guidance
- strength
- forgiveness
- grief
- temptation
- patience
- assurance

#### Christian life topics

Examples:

- prayer
- faith
- obedience
- thanksgiving
- holiness
- repentance
- good-works
- love-of-neighbor

#### Study themes

Examples:

- christ
- grace
- redemption
- scripture
- holy-spirit
- heaven
- death-and-resurrection
- providence

### Size guidance

Tracked in GitHub Issues: #5 (https://github.com/AndreRobitaille/LincolnDevotional/issues/5).

Too few topics will make pages overly broad and vague. Too many topics will make the browse system noisy and difficult to maintain.

## Data Model

Keep `data/entries.json` as the devotional source of truth.

### New file: `data/topic_taxonomy.json`

This file should define the approved taxonomy and browsing metadata.

Each topic should include at least:

- slug
- display name
- group (`need`, `christian-life`, `study`)
- short description
- optional related topics

### New file: `data/entry_topics.json`

This file should store approved topic assignments for entries.

Each entry should include:

- `primary_topic`
- `topics` (typically 2 to 4)
- `reader_needs` (typically 0 to 2)

Example:

```json
{
  "0418": {
    "primary_topic": "self-examination",
    "topics": ["repentance", "holiness", "assurance"],
    "reader_needs": ["spiritual-honesty"]
  }
}
```

This keeps the topic layer separate, reviewable, and easy to regenerate.

## AI-Assisted Tagging Workflow

Use AI to classify entries **only within the approved taxonomy**.

The system should not allow unconstrained label invention.

### Why AI fits here

- The devotional dataset is structured and finite.
- The entry titles already carry strong thematic meaning.
- Verse text and poem text provide additional nuance.
- Human review can realistically validate results because the corpus is bounded.

### Suggested tagging script behavior

Add a Python script that:

- reads `data/entries.json`
- reads `data/topic_taxonomy.json`
- sends entry title, verse reference, verse text, and poem to OpenAI
- asks for structured classification against approved topic slugs only
- writes results to `data/entry_topics.json`
- caches responses to reduce repeat cost

Suggested workflow flags:

- `--dry-run`
- `--limit`
- `--entry 0418`
- `--resume`
- `--report`

### Editorial rule

AI suggestions should be reviewed and stored as approved data in the repository.

Tagging should be an intentional editorial workflow, not an automatic step during every deployment.

## Static Generation Flow

The static generation process should combine:

- `data/entries.json`
- `data/topic_taxonomy.json`
- `data/entry_topics.json`

It should generate:

- `/explore/index.html`
- one static topic page per taxonomy entry
- topic chips on devotional entry pages

This generation should stay inside the project’s current static-site model and existing Python tooling approach.

## SEO and Internal Linking Benefits

This feature should improve SEO as a consequence of better reader exploration, not as a disconnected metadata exercise.

Expected SEO benefits:

- crawlable topic hubs
- stronger internal linking between related devotionals
- improved discoverability beyond date-based entry pages
- more meaningful landing pages for topic-based queries
- better long-tail relevance for both devotional and study-oriented searches

The Explore system should complement existing static entry page SEO rather than replacing it.

## Non-Goals for Version 1

- Building a full search interface
- Adding faceted filtering UI
- Replacing the homepage’s daily-devotion focus
- Allowing users to create their own tags or lists
- Automatically publishing unreviewed AI classifications
- Building a complex archive browser beyond the Explore use case

## QA and Editorial Review

Before publishing:

- every entry should have a primary topic
- topic assignments should look plausible to a human reader
- no topic page should feel empty or incoherent
- Tracked in GitHub Issues: #4 (https://github.com/AndreRobitaille/LincolnDevotional/issues/4).
- entry chips should feel helpful, not random or excessive
- Explore page should stay visually simple and easy to scan

## Rollout Plan

1. Define and approve the taxonomy.
2. Build the AI-assisted tagging script.
3. Generate and review entry-topic assignments.
4. Generate the Explore page and topic pages.
5. Add topic chips to devotional entry pages.
6. Tracked in GitHub Issues: #6 (https://github.com/AndreRobitaille/LincolnDevotional/issues/6).

## Recommendation Summary

Implement a browse-first Explore system centered on reader needs, supported by Christian life topics and study themes, using AI-assisted classification into a controlled taxonomy and generating static topic pages plus topic chips on devotional entries.

This is the best fit for the site’s audience, architecture, and goals:

- better for readers than search-first
- better for consistency than free-form AI tagging
- better for SEO than leaving entries connected only by date navigation
- well aligned with the existing static generation model
