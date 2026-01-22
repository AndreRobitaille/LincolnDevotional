# Lincoln Daily Devotional

A static website and structured dataset based on *The Believer’s Daily Treasure*, a 19th-century Christian devotional long associated with :contentReference[oaicite:0]{index=0} and his personal reading.

This repository provides a faithful digital presentation of the devotional along with a reusable, machine-readable dataset intended for reading, study, or reuse without restriction.

---

## About the Project

*The Believer’s Daily Treasure* was first published in the mid-1800s and reflects the devotional language and scriptural usage common to that period, including extensive use of the King James Bible.

The devotional remained in circulation through later printings, most notably the 1950 reprint commonly titled *Lincoln’s Daily Devotional*, as well as the modern edition currently published by Applewood Books. These editions have played an important role in preserving and sharing the text with new generations of readers.

This project builds on that tradition by presenting the devotional in a simple, static digital form and by providing a clean, structured dataset for others to reuse.

---

## Text Sources and Editorial Approach

The goal of this project is preservation and accuracy, not revision.

Editorial work focused on:

- Faithful transcription of historical printings
- Correction of clear typographical and transcription errors that have propagated across editions
- Retention of historical language, spelling, and tone
- Consistent formatting of poetry and line breaks where source material varied
- Preservation of King James Bible language and references

One poem substitution present in later printings is retained as part of the devotional’s publication history. No doctrinal, theological, or stylistic reinterpretation has been introduced.

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

- **Scripture Tooltips**  
  Uses RefTagger for inline scripture references, displaying KJV text.

---

## Quick Start

No build tools or package managers are required.

1. Clone the repository:
   ```bash
   git clone https://github.com/AndreRobitaille/LincolnDevotional.git
   cd LincolnDevotional
