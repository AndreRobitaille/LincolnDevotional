# Static Entry Page Date Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a date picker to generated static entry pages so readers can jump directly to any day while preserving Previous/Next as no-JS navigation.

**Architecture:** Keep the dynamic index-page picker logic untouched. Generate the same center picker affordance into each static page, then enhance it with a small shared JavaScript file that reads the selected month/day, looks up the destination in `data/routes.json`, and redirects to the matching static entry URL.

**Tech Stack:** Static HTML/CSS/JavaScript, Python 3 standard library generator, Python `unittest`

---

## File Structure

- Modify: `tools/generate_entry_pages.py`
  - Extend the static page template to emit picker markup, data attributes, and a script tag for the new helper.
- Create: `static-entry-nav.js`
  - Own all static-page picker behavior: initialization, picker open/focus behavior, one-time manifest fetch, safe date parsing, and redirect.
- Modify: `style.css`
  - Reuse existing navigation styles and, if necessary, add minimal rules so static Previous/Next links visually align with the index page nav.
- Modify: `tests/test_generate_entry_pages.py`
  - Add failing tests for generated picker markup, helper script inclusion, and static-page initialization data.

## Task 1: Lock down generated static-page HTML with failing tests

**Files:**
- Modify: `tests/test_generate_entry_pages.py`
- Test: `tests/test_generate_entry_pages.py`

- [ ] **Step 1: Write the failing test for picker markup and helper script**

Add the following test method inside `GenerateEntryPagesTests` in `tests/test_generate_entry_pages.py`:

```python
    def test_generate_site_adds_date_picker_to_static_navigation(self):
        with TemporaryDirectory() as tmp_dir:
            output_root = Path(tmp_dir)
            generate_site(self.entries, self.esv_cache, output_root, "https://lincolndevotional.com")

            html = (output_root / "entries" / "january-1" / "index.html").read_text()

            self.assertIn('<nav class="entry-nav" aria-label="Entry navigation">', html)
            self.assertIn('class="date-picker-wrap"', html)
            self.assertIn('class="date-picker-label">Jump to</span>', html)
            self.assertIn('class="current-date-display">January 1</span>', html)
            self.assertIn('type="date"', html)
            self.assertIn('data-entry-mmdd="0101"', html)
            self.assertIn('data-routes-path="../../data/routes.json"', html)
            self.assertIn('<script src="../../static-entry-nav.js?v=20260519a"></script>', html)
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `python3 -m unittest tests.test_generate_entry_pages.GenerateEntryPagesTests.test_generate_site_adds_date_picker_to_static_navigation -v`

Expected: FAIL with one or more missing generated markup assertions.

- [ ] **Step 3: Tighten the existing navigation test to require the center control ordering**

Add this helper near the top of `tests/test_generate_entry_pages.py`, below the imports:

```python
def assert_in_order(test_case, html, fragments):
    current_index = -1
    for fragment in fragments:
        next_index = html.index(fragment)
        test_case.assertGreater(next_index, current_index)
        current_index = next_index
```

Then use it in `test_generate_site_writes_entry_pages_sitemap_and_robots` after reading `html`:

```python
            assert_in_order(
                self,
                html,
                [
                    'Previous</a>',
                    'class="date-picker-wrap"',
                    'Next</a>',
                ],
            )
```

- [ ] **Step 4: Run the full generator test file to confirm the new expectations fail only for missing implementation**

Run: `python3 -m unittest tests.test_generate_entry_pages -v`

Expected: FAIL in the new picker-related assertions; existing non-picker tests should still pass.

- [ ] **Step 5: Commit the failing-test checkpoint**

```bash
git add tests/test_generate_entry_pages.py
git commit -m "test: cover static entry page date picker"
```

## Task 2: Implement static-page picker generation and shared helper

**Files:**
- Modify: `tools/generate_entry_pages.py`
- Create: `static-entry-nav.js`
- Modify: `style.css`
- Test: `tests/test_generate_entry_pages.py`

- [ ] **Step 1: Add helper functions for static picker markup in the generator**

In `tools/generate_entry_pages.py`, add two helpers above `render_entry_page`:

```python
def build_static_asset_version():
    return "20260519a"


def render_static_date_picker(entry):
    return f"""
            <div
              class="date-picker-wrap"
              data-entry-mmdd="{entry['mmdd']}"
              data-routes-path="../../data/routes.json"
            >
              <span class="date-picker-label">Jump to</span>
              <span class="current-date-display">{escape(entry['display_date'])}</span>
              <input type="date" class="nav-date-input" aria-label="Jump to another date" />
            </div>"""
```

This keeps the generated nav markup readable and avoids burying all new HTML inside `render_entry_page`.

- [ ] **Step 2: Update `render_entry_page` to include the center picker and helper script**

Inside `render_entry_page`, replace the current `navigation` block with:

```python
    prev_link = f'<a href="../{slugify_entry(previous_entry)}/">&larr; Previous</a>'
    next_link = f'<a href="../{slugify_entry(next_entry)}/">Next &rarr;</a>'
    date_picker = render_static_date_picker(entry)
    navigation = f"""
          <nav class="entry-nav" aria-label="Entry navigation">
            {prev_link}
            {date_picker}
            {next_link}
          </nav>"""
```

And before the closing `</body>`, add:

```python
    <script src="../../static-entry-nav.js?v={build_static_asset_version()}"></script>
```

Keep the existing `theme.js` and `share.js` tags intact.

- [ ] **Step 3: Create the shared static navigation helper**

Create `static-entry-nav.js` with this implementation:

```javascript
document.addEventListener('DOMContentLoaded', () => {
    const pickerWrap = document.querySelector('.date-picker-wrap[data-entry-mmdd]');
    if (!pickerWrap) {
        return;
    }

    const datePicker = pickerWrap.querySelector('.nav-date-input');
    const currentDisplayDate = pickerWrap.querySelector('.current-date-display');
    const entryMmdd = pickerWrap.dataset.entryMmdd;
    const routesPath = pickerWrap.dataset.routesPath;

    if (!datePicker || !currentDisplayDate || !entryMmdd || !routesPath) {
        console.warn('Static entry date picker is missing required elements or data attributes.');
        return;
    }

    let routeMapPromise = null;

    function buildCurrentYearDate(mmdd) {
        const month = parseInt(mmdd.slice(0, 2), 10);
        const day = parseInt(mmdd.slice(2, 4), 10);
        const year = new Date().getFullYear();
        const date = new Date(year, month - 1, day);

        if (date.getMonth() !== month - 1 || date.getDate() != day) {
            return null;
        }

        return date;
    }

    function toDateInputValue(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function getMmddFromInputValue(value) {
        const parts = value.split('-');
        if (parts.length !== 3) {
            return null;
        }

        const month = parts[1];
        const day = parts[2];
        if (!month || !day) {
            return null;
        }

        return `${month}${day}`;
    }

    async function loadRouteMap() {
        if (!routeMapPromise) {
            routeMapPromise = fetch(routesPath)
                .then((response) => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status} loading routes manifest`);
                    }
                    return response.json();
                });
        }

        return routeMapPromise;
    }

    const currentDate = buildCurrentYearDate(entryMmdd);
    if (currentDate) {
        datePicker.value = toDateInputValue(currentDate);
    }

    pickerWrap.addEventListener('click', () => {
        if (typeof datePicker.showPicker === 'function') {
            datePicker.showPicker();
            return;
        }

        datePicker.focus();
    });

    datePicker.addEventListener('click', (event) => {
        event.stopPropagation();
    });

    datePicker.addEventListener('change', async () => {
        const mmdd = getMmddFromInputValue(datePicker.value);
        if (!mmdd) {
            console.warn('Static entry date picker received an invalid value.');
            return;
        }

        try {
            const routeMap = await loadRouteMap();
            const href = routeMap[mmdd];
            if (!href) {
                console.warn(`No static entry route found for ${mmdd}.`);
                return;
            }

            window.location.href = href;
        } catch (error) {
            console.error('Unable to load static entry routes.', error);
        }
    });
});
```

- [ ] **Step 4: Make any minimal style adjustments needed for static links to match the nav bar**

In `style.css`, keep the current shared classes. Only change selectors if the static links need to match the existing nav buttons more closely. Use this minimal adjustment:

```css
.entry-nav a,
.entry-nav .nav-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 7rem;
    padding: 10px 14px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--surface);
    font-family: var(--font-ui);
    font-size: 0.8rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.entry-nav a {
    color: var(--accent-strong);
}

.entry-nav .nav-button {
    color: var(--text);
    background: transparent;
}
```

Then keep the existing hover/focus selectors, updating them only if needed so both anchors and buttons keep their current behavior.

- [ ] **Step 5: Run the targeted new test until it passes**

Run: `python3 -m unittest tests.test_generate_entry_pages.GenerateEntryPagesTests.test_generate_site_adds_date_picker_to_static_navigation -v`

Expected: PASS

- [ ] **Step 6: Run the full generator test suite**

Run: `python3 -m unittest tests.test_generate_entry_pages -v`

Expected: PASS

- [ ] **Step 7: Commit the implementation checkpoint**

```bash
git add tools/generate_entry_pages.py static-entry-nav.js style.css tests/test_generate_entry_pages.py
git commit -m "feat: add static entry page date picker"
```

## Task 3: Regenerate static pages and verify output manually

**Files:**
- Modify: `entries/*/index.html`
- Modify: `data/routes.json` (only if generator rewrites formatting or contents)
- Test: generated static pages in `entries/`

- [ ] **Step 1: Regenerate the static entry pages**

Run: `python3 tools/generate_entry_pages.py`

Expected: command exits successfully with no output.

- [ ] **Step 2: Spot-check generated HTML for one representative page**

Open `entries/january-1/index.html` and confirm it now contains all of the following fragments:

```html
<nav class="entry-nav" aria-label="Entry navigation">
  <a href="../december-31/">&larr; Previous</a>
  <div
    class="date-picker-wrap"
    data-entry-mmdd="0101"
    data-routes-path="../../data/routes.json"
  >
  ...
  <script src="../../static-entry-nav.js?v=20260519a"></script>
```

- [ ] **Step 3: Run a local static server for manual browser verification**

Run: `python3 -m http.server 8000`

Expected: server starts and serves the repo root at `http://localhost:8000/`.

- [ ] **Step 4: Manually verify the acceptance criteria in a browser**

Check:
- `http://localhost:8000/entries/january-1/` shows Previous • Jump to January 1 • Next
- clicking the center control opens the native date picker
- choosing January 2 navigates to `/entries/january-2/`
- light mode styling matches the index page nav bar
- dark mode styling matches the index page nav bar
- `http://localhost:8000/` still has a working index page picker

- [ ] **Step 5: Inspect the browser console while testing**

Expected: no JavaScript errors during static-page date navigation or index-page date navigation.

- [ ] **Step 6: Commit regenerated pages and helper asset**

```bash
git add entries static-entry-nav.js tools/generate_entry_pages.py style.css tests/test_generate_entry_pages.py
git commit -m "build: regenerate static entry pages"
```

## Self-Review Checklist

- Spec coverage:
  - picker appears between Previous and Next: covered by Task 1 assertions and Task 2 generator changes
  - picker navigates to the selected static page: covered by Task 2 helper implementation and Task 3 manual verification
  - styling matches index page in light/dark mode: covered by Task 2 style rules and Task 3 manual verification
  - no regression in index picker: covered by Task 3 manual verification
- Placeholder scan:
  - no TBD/TODO placeholders remain
  - every code-changing step includes concrete code or concrete file content to add
- Type consistency:
  - `data-entry-mmdd`, `data-routes-path`, `.date-picker-wrap`, `.current-date-display`, and `.nav-date-input` are used consistently across tests, generator output, and helper script
