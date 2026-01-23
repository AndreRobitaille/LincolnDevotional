# Lincoln Daily Devotional

A static website and structured dataset based on *The Believer’s Daily Treasure*, a 19th-century Christian devotional long associated with President Abraham Lincoln and his personal reading.

This repository provides a faithful digital presentation of the devotional along with a reusable, machine-readable dataset intended for reading, study, or reuse without restriction.

---

## About the Project

*The Believer’s Daily Treasure* was first published in the mid-1800s and reflects the devotional language and scriptural usage common to that period, including extensive use of the King James Bible.

The devotional remained in circulation through later printings, most notably the 1957 reprint by Carl Sandburg commonly titled *Lincoln’s Daily Devotional*, as well as the modern edition currently published by Applewood Books. These editions have played an important role in preserving and sharing the text with new generations of readers.

This project builds on that tradition by presenting the devotional in a simple, static digital form and by providing a clean, structured dataset for others to reuse.

---

## Text Sources and Editorial Approach

The goal of this project is preservation and accuracy, not revision.

Editorial work focused on:

- Faithful transcription of historical poems, while updating bible references and verse text
- Correction of clear typographical and transcription errors that have propagated across editions
- Retention of historical language, spelling, and tone
- Consistent formatting of poetry and line breaks where source material varied
- Preservation of King James Bible language and references

One poem substitution present in later printings was removed in favor of the original poem in the devotional. No doctrinal, theological, or stylistic reinterpretation has been introduced.

---

## Enhancements in This Digital Edition

- **Complete Scripture Text**  
  Physical printings often truncated verses to fit the page. This edition restores full verse text using the 1769 Oxford King James Version (KJV) while preserving original references and correcting minor citation errors where necessary.

- **Accessibility and Usability**  
  Responsive layout for mobile and desktop, dark mode support, and fast page loads.

- **Structured Data**  
  The devotional is provided as a single JSON dataset for easy reuse in other projects.

---

## Features

- **Daily Entry Loading**  
  Automatically displays the correct devotional for the current date.

- **Navigation**  
  Previous and next day navigation, plus a date picker to jump to any entry.

- **Visual Design**  
  Clean, typography-focused layout inspired by historical printing and designed for screens.

- **Static Architecture**  
  Fully static HTML, CSS, and JavaScript. No backend, database, or build tools required.

- **Parallel Translations**  
  Includes the full King James Version (KJV) text and, where available, the English Standard Version (ESV) for comparison.

---

## Quick Start

No build tools or package managers are required.

1. Clone the repository:

   ```bash
   git clone https://github.com/AndreRobitaille/LincolnDevotional.git
   cd LincolnDevotional
   ```

2. Open `index.html` in your browser.

   Or run a local server:

   ```bash
   python3 -m http.server
   ```

   Then visit `http://localhost:8000`.

---

## Developer Tools

The repository includes Python scripts in the `tools/` directory to manage data.

### Setup

To fetch ESV verses, you need an API key from [API.ESV.org](https://api.esv.org/).
Create a `.env` file in the project root:

```bash
ESV_API_KEY=your_api_key_here
```

### Scripts

- **Fetch ESV Verses**: `python3 tools/fetch_esv.py --all`  
  Fetches verse text from the ESV API and caches it locally in `data/esv_cache.json`.
  Use the --help switch for additional options.
  
- **Audit Data**: `python3 tools/audit_esv.py`  
  Checks for reference mismatches, empty text, or suspicious formatting.
  
- **Clean Data**: `python3 tools/clean_esv.py`  
  Normalizes punctuation and capitalization in cached verses.
