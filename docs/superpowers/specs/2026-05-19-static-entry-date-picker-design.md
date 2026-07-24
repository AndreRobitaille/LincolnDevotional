## Static Entry Page Date Picker Design

### Goal
Add the existing date-jump affordance to generated static devotional entry pages so readers can navigate directly from any static page to any other day without returning to the index page.

### Scope
- Add a center date-picker control to the static entry page navigation bar.
- Keep Previous/Next navigation as plain links.
- Use shared JavaScript for static-page date jumping.
- Reuse `data/routes.json` as the source of truth for static entry URLs.
- Preserve the current index page picker behavior.

### Non-goals
- Refactoring the index page picker logic.
- Adding user-facing error UI for failed date-jump enhancement.
- Changing the static page SEO strategy or URL scheme.

### Current State
- `index.html` renders an `.entry-nav` with Previous button, date picker, and Next button.
- `script.js` drives the dynamic page picker and in-page entry switching.
- `tools/generate_entry_pages.py` generates static entry pages with only Previous/Next links.
- `data/routes.json` already maps `MMDD` keys to canonical static entry URLs.

### Recommended Approach
Implement a shared static-page helper script plus generated picker markup.

Why this approach:
- Keeps static routing logic centralized in `data/routes.json`.
- Avoids duplicating inline navigation logic across 365 generated pages.
- Minimizes regression risk by not refactoring the working dynamic-page script.
- Preserves no-JS fallback via the existing Previous/Next links.

### Architecture

#### 1. Static page template generation
Update `tools/generate_entry_pages.py` so each generated static page renders a three-part navigation bar:
- Previous link
- date-picker control
- Next link

The generated markup should match the existing index-page visual structure closely enough to reuse current navigation styles.

The template should also render the metadata needed by the helper script, preferably as data attributes on the picker wrapper or input, including:
- current entry `mmdd`
- a path to the shared routes manifest, if needed

#### 2. Shared static navigation helper
Add a small shared JavaScript file dedicated to static entry page date navigation.

Responsibilities:
- locate the static picker widget
- initialize the date input value from the current entry month/day using the current year
- open the native date picker from the wrapper when supported
- parse the selected date safely in local time
- convert the selected date to `MMDD`
- load `data/routes.json` once
- redirect to the matching static URL

This file should be loaded only by generated static entry pages.

#### 3. Routing source of truth
Keep `data/routes.json` as the sole runtime lookup table for static-page date jumping.

This avoids duplicating slug rules in multiple places and keeps future route changes centralized in the existing generation flow.

### Interaction Design

#### Navigation behavior
- Previous/Next remain plain anchor links and work with or without JavaScript.
- The center control mirrors the existing index pattern:
  - “Jump to” label
  - current day display text
  - hidden/native `input[type="date"]`

#### Initialization behavior
On page load, the helper script should:
- find the picker elements
- determine the current entry month/day from rendered metadata
- create a valid picker date using the current year
- populate the input value in `YYYY-MM-DD` format
- update the visible label to the entry display date already rendered into the page

Using the current year is acceptable because the devotional is keyed only by month/day and the year is irrelevant to destination routing.

#### Selection behavior
On picker change:
- read the chosen `YYYY-MM-DD` value
- parse with local-time-safe logic rather than `new Date('YYYY-MM-DD')`
- derive `MMDD`
- resolve the destination from the manifest
- navigate with `window.location.href`

#### Failure behavior
If enhancement fails:
- keep the visible static page content intact
- keep Previous/Next working
- log a warning or error to the console
- do not show extra UI for this failure mode

### Styling
- Reuse the existing shared navigation styles in `style.css` for `.entry-nav`, `.date-picker-wrap`, `.date-picker-label`, `.current-date-display`, and `.nav-date-input`.
- Preserve the same light/dark appearance as the index page.
- If needed, make narrowly scoped style adjustments so static Previous/Next links visually match the date picker bar without destabilizing the index page layout.

### File Changes
- `tools/generate_entry_pages.py`
  - add static picker markup to the generated nav
  - include the shared static helper script
  - emit any data attributes needed for initialization
- `style.css`
  - reuse or minimally adjust shared nav styles if static links need alignment tweaks
- new shared JS file
  - implement static-page picker initialization and navigation
- `tests/test_generate_entry_pages.py`
  - assert generated static pages include picker markup and helper script

### Testing and Verification

#### Automated
Extend `tests/test_generate_entry_pages.py` to verify generated HTML includes:
- the `.entry-nav` wrapper
- the center picker markup
- the shared helper script reference

#### Regeneration check
Run the page generator and inspect representative generated files to confirm the new markup is emitted correctly.

#### Manual browser verification
Check at least one static entry page for:
- Previous • Jump to date • Next layout
- working date selection navigation
- matching light-mode styling
- matching dark-mode styling

Also verify the dynamic index page picker still works unchanged.

### Risks and Mitigations
- **Risk:** styling drift between static and dynamic navigation
  - **Mitigation:** reuse current shared classes rather than inventing a second nav pattern
- **Risk:** manifest path issues from nested static pages
  - **Mitigation:** render an explicit correct asset path from the generator or use a root-relative fetch path consistently
- **Risk:** timezone-related date parsing bugs
  - **Mitigation:** parse picker values manually into local date parts
- **Risk:** unnecessary regression on the index page
  - **Mitigation:** keep dynamic-page logic separate from static-page helper logic

### Decision Summary
- Use a shared helper script for static pages.
- Keep Previous/Next as no-JS fallback links.
- Use `data/routes.json` for destination lookup.
- Keep the index page implementation functionally unchanged.
