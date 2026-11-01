# Focused taxonomy

Replace the current 15 labels with **40 topics and 7 reader needs**, using a maximum of **25 readings per label**. The taxonomy gives every one of the 366 readings a primary topic. Its largest topic has **18 readings** and its largest reader need has **22**; these totals include secondary assignments.

This addresses [issue 4](https://github.com/AndreRobitaille/LincolnDevotional/issues/4) and [issue 5](https://github.com/AndreRobitaille/LincolnDevotional/issues/5) together: useful, specific labels replace the crowded categories, and the coverage comes from the actual subjects in the book. The result is 47 selectable labels across both facets. The older 35–45 guidance is a sizing guide rather than a reason to combine different subjects.

## Tagging rules

Treat Andre's “25 or so” as a hard limit of 25 for validation. Count every distinct reading attached to a label, whether the topic is primary or secondary. Apply the same rule to reader needs.

Prefer one or two words for each displayed tag; three words is the maximum. Keep the detail in the descriptions and editorial scopes.

Assign one primary topic for the reading's dominant subject and at most one secondary topic for another substantial theme. A shared word or a prayer in the poem is insufficient by itself. Reader needs remain optional; the taxonomy uses them on 86 readings. Small, useful collections are acceptable: Grief has three readings.

When a coherent label exceeds 25, split its meaning into useful narrower labels or retire it. Do not truncate a result list, omit a valid assignment to satisfy the cap, or retain the broad tag as a hidden alias. Each proposed label has inclusion and exclusion guidance in [editorial_scopes.json](editorial_scopes.json).

## Reader needs

| Need | Readings |
| --- | ---: |
| Grief | 3 |
| Fearing Death | 13 |
| Financial Worry | 6 |
| Guilt | 16 |
| Being Mistreated | 13 |
| Recurring Sin | 22 |
| Seeking Direction | 16 |

These replace the broad Comfort, Hope, Strength, Peace, Repentance, Gratitude, Guidance, and Assurance filters. Gratitude remains available as the specific Thanksgiving topic; the other old needs lead to narrower topics or situations.

## Topics

Use these five headings to organise the topic choices. Headings are navigation aids without a filter or passage count; only the individual labels select readings. Put the seven reader needs before the topic groups so readers can begin with their situation.

### Salvation and belonging

| Topic | All readings | Primary |
| --- | ---: | ---: |
| God's Love | 7 | 6 |
| Redemption | 12 | 6 |
| God's Forgiveness | 9 | 8 |
| Justification | 8 | 7 |
| In Christ | 11 | 10 |
| Adoption | 7 | 6 |
| Holy Spirit | 17 | 15 |

### Prayer and devotion

| Topic | All readings | Primary |
| --- | ---: | ---: |
| Loving God | 5 | 5 |
| Consecration | 10 | 10 |
| God's Guidance | 5 | 3 |
| Scripture | 10 | 8 |
| Prayer | 12 | 10 |
| Intercession | 7 | 6 |
| Thanksgiving | 13 | 9 |
| Joy in Salvation | 12 | 7 |

### Life with others

| Topic | All readings | Primary |
| --- | ---: | ---: |
| Serving Others | 15 | 14 |
| Church Fellowship | 18 | 12 |
| Forgiving Others | 7 | 6 |
| Gospel Witness | 14 | 13 |
| Integrity | 9 | 8 |
| Stewardship | 11 | 10 |
| Humility | 13 | 11 |
| Self Control | 12 | 11 |
| Holiness | 18 | 14 |

### Trials and growth

| Topic | All readings | Primary |
| --- | ---: | ---: |
| Refuge | 12 | 12 |
| Providence | 17 | 14 |
| Perseverance | 11 | 10 |
| Watchfulness | 6 | 6 |
| Repentance | 16 | 15 |
| Patience | 12 | 11 |
| Refining Trials | 12 | 7 |
| Resisting Temptation | 14 | 13 |
| Christ's Strength | 14 | 8 |

### Death and life to come

| Topic | All readings | Primary |
| --- | ---: | ---: |
| Facing Death | 8 | 7 |
| Resurrection | 8 | 6 |
| Final Judgment | 7 | 5 |
| Heavenly Rest | 18 | 16 |
| God's Presence | 10 | 9 |
| Heavenly Worship | 6 | 4 |
| Heavenly Glory | 10 | 8 |

## Editorial examples

| Reading | Current primary | Proposed primary | Reason |
| --- | --- | --- | --- |
| January 2: Redeemed by the Blood of Christ | Grace | Redemption | The ransom paid by Christ is the subject of both verse and poem; a broad Grace label conceals that distinction. |
| January 17: The Spirit of Adoption Received | Faith | Adoption | Adoption is primary; the Spirit who bears witness is the independent secondary theme. |
| March 8: Pardon Through Christ | Grace | God's Forgiveness | Forgiveness is primary; redemption by Christ's blood is also explicit and substantial. |
| July 15: Prayer a Source of Joy | Prayer | Prayer | Prayer is the source of joy named in the reading. A generic Joy or Comfort tag would add little direction. |
| September 28: Christ's Intercession for the Tempted | Prayer | Intercession | Christ prays for the tempted disciple. Intercession is more precise than the former Prayer and Faith combination. |
| October 23: Of Departed Friends | Faith | Resurrection | The passage grounds reunion in resurrection; Grief gives the reader a separate practical way to find it. |
| November 20: Of an Incorruptible Body | Faith | Resurrection | The transformation of the mortal body is distinct from a generic promise of heaven or comfort. |
| December 13: Heaven a State of Service | Obedience | Heavenly Worship | Service before God's throne belongs with heavenly worship, rather than a general Obedience tag. |

There are 77 readings with a secondary topic. The [passage lists](passages-by-tag.md) show every assignment, distinguish primary from secondary, and give the verse reference. Read the entry alongside its label to review the editorial fit; counts alone cannot establish that fit.

## Implementation record

The approved vocabulary and all 366 assignments are installed in `data/topic_taxonomy.json` and `data/entry_topics.json`. The descriptions retain the detailed scope behind each short label. Explore puts reader needs first, groups topics under five headings, and shows the selected tag's description. Daily entry chips link to the focused filters.

`tools/audit_topics.py` enforces the 25-reading and three-word limits, complete coverage, and valid assignments. Both page generation and the PR/deployment workflow run it. The tagging maintenance tool checkpoints draft progress only in its internal cache, validates the complete candidate collection, and atomically replaces approved assignments after success. `--resume` restores matching checkpoints and fetches only unfinished entries. Checkpoints bind the source text, vocabulary, model, and approved dataset; changes to those inputs stop recovery before any API request. Older unscoped caches are not used as draft checkpoints.

Retired links such as `?topic=faith` display an explanation and links to the narrower choices in `data/legacy_tag_suggestions.json`. They do not select an arbitrary replacement or display a combined broad result. Unknown filters also offer an explicit recovery path. Full text search remains available for broad terms.

This vocabulary and its bounded collections address issue 5. The complete passage lists, scope definitions, and explicit primary and secondary choices form the editorial record for issue 4. The earlier sizing guidance is superseded by the maximum of 25 readings per label and three words per displayed name.

## Local validation

Run from the repository root:

```sh
python3 tools/audit_topics.py
```

The audit checks complete date coverage, valid and distinct vocabularies, primary membership, unknown and misplaced tags, duplicate assignments, empty labels, per-reading limits, the three-word label maximum, and the 25-reading maximum across both facets. It only reads files. It validates the production dataset before page generation and deployment.

Local verification passed the full draft and 15 CLI checks, including accepting 25 and rejecting 26 primary, secondary, or reader-need members. A secondary assignment produced `Topic gods-guidance has 26 passages; maximum is 25`. Missing leap day, unknown and misplaced tags, duplicates, empty labels, and missing primary membership were also rejected. The existing generator produced matching counts for all 47 labels and valid topic-chip links for all 366 readings with the proposed data.

## Source and status

Editorial assignments prepared by Codex from all 366 titles, KJV passages, and poems in [entries.json at 8c9a831](https://github.com/AndreRobitaille/LincolnDevotional/blob/8c9a8310c382a79caaa81ff23db55eb9d9cd944c/data/entries.json). [source.json](source.json) records the immutable source blobs. No paid tagging API was used.

The JSON files in this directory preserve the accepted editorial proposal. The corresponding data files and maintenance audit in the repository root are authoritative for generation and deployment.
