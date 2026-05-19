document.addEventListener('DOMContentLoaded', () => {
    const devotionalContent = {
        title: document.getElementById('entryTitle'),
        displayDateElement: document.getElementById('entryDisplayDate'),
        devotional: document.getElementById('entryDevotional'), // KJV
        esv: document.getElementById('entryEsv'),
        esvBlock: document.getElementById('esvBlock'),
        verseRef: document.getElementById('entryVerseRef'),
        poem: document.getElementById('entryPoem')
    };

    const prevDayBtn = document.getElementById('prevDayBtn');
    const nextDayBtn = document.getElementById('nextDayBtn');
    const currentDisplayDateNav = document.getElementById('currentDisplayDate');
    const datePicker = document.getElementById('datePicker');
    const datePickerWrap = document.getElementById('datePickerWrap');
    const permalinkArea = document.getElementById('devotionLinkArea');
    const permalinkLink = document.getElementById('devotionLink');

    let allEntries = [];
    let esvCache = {};
    let routeMap = {};
    let currentDate = new Date();
    let currentYear = currentDate.getFullYear();
    let currentEntry = null;

    // --- Data Loading ---
    async function loadDevotionals() {
        try {
            // Fetch both data files in parallel
            const [entriesResponse, esvResponse] = await Promise.all([
                fetch('data/entries.json'),
                fetch('data/esv_cache.json').catch(e => {
                    console.warn("Could not load ESV cache:", e);
                    return null;
                })
            ]);
            const routesResponse = await fetch('data/routes.json').catch(() => null);

            if (!entriesResponse.ok) {
                throw new Error(`HTTP error loading entries! status: ${entriesResponse.status}`);
            }
            allEntries = await entriesResponse.json();

            if (esvResponse && esvResponse.ok) {
                try {
                    esvCache = await esvResponse.json();
                } catch (e) {
                    console.error("Error parsing ESV cache:", e);
                }
            }

            if (routesResponse && routesResponse.ok) {
                try {
                    routeMap = await routesResponse.json();
                } catch (e) {
                    console.error("Error parsing routes manifest:", e);
                }
            }

            // Set date picker to today and load today's entry
            const today = new Date();
            datePicker.value = today.toLocaleDateString('en-CA'); 
            currentDate = today;
            currentYear = today.getFullYear();
            displayEntryForDate(currentDate);
        } catch (error) {
            console.error("Could not load devotional data:", error);
            devotionalContent.title.textContent = "Error loading data.";
            devotionalContent.devotional.textContent = error.message; // Show specific error on screen
        }
    }

    // --- Date Formatting and Finding ---
    function getMMDD(date) {
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${month}${day}`;
    }

    // Formats date for display (e.g., "June 2")
    function formatDisplayDate(date) {
        return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric' });
    }
    
    // Formats date for display in nav (e.g., "June 2, 2025")
    function formatNavDate(date) {
        return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric' });
    }


    function findEntry(date) {
        const mmdd = getMMDD(date);
        return allEntries.find(entry => entry.mmdd === mmdd);
    }

    function findEntryIndex(entry) {
        return allEntries.findIndex(item => item.mmdd === entry.mmdd);
    }

    function buildPermalinkHref(entry) {
        return routeMap[entry.mmdd] || null;
    }

    function updatePermalink(entry) {
        if (!permalinkArea || !permalinkLink) {
            return;
        }

        if (!entry) {
            permalinkArea.classList.add('hidden');
            permalinkLink.removeAttribute('href');
            return;
        }

        const href = buildPermalinkHref(entry);
        if (!href) {
            permalinkArea.classList.add('hidden');
            permalinkLink.removeAttribute('href');
            return;
        }

        permalinkLink.href = href;
        const datePart = entry.display_date ? ` — ${entry.display_date}` : '';
        const titlePart = entry.title ? `: ${entry.title}` : '';
        permalinkLink.dataset.linkTitle = `The Believer's Daily Treasure${datePart}${titlePart}`;
        permalinkArea.classList.remove('hidden');
    }

    function getAdjacentEntry(entry, direction) {
        if (!entry || !allEntries.length) {
            return null;
        }

        const currentIndex = findEntryIndex(entry);
        if (currentIndex < 0) {
            return null;
        }

        const nextIndex = (currentIndex + direction + allEntries.length) % allEntries.length;
        return allEntries[nextIndex];
    }

    function buildPickerDate(entry, year) {
        if (!entry) {
            return null;
        }

        const pickerDate = new Date(year, entry.month - 1, entry.day);
        if (pickerDate.getMonth() !== entry.month - 1 || pickerDate.getDate() !== entry.day) {
            return null;
        }

        return pickerDate;
    }

    function syncDatePicker(entry, pickerDate) {
        if (!datePicker || !currentDisplayDateNav) {
            return;
        }

        if (entry) {
            currentDisplayDateNav.textContent = entry.display_date || formatDisplayDate(pickerDate || currentDate);
        } else if (pickerDate) {
            currentDisplayDateNav.textContent = formatNavDate(pickerDate);
        } else {
            currentDisplayDateNav.textContent = 'Select a date';
        }

        datePicker.value = pickerDate ? pickerDate.toLocaleDateString('en-CA') : '';
    }

    function displayEntry(entry, pickerDate = null) {
        currentEntry = entry;
        currentDate = pickerDate || currentDate;

        syncDatePicker(entry, pickerDate);

        if (entry) {
            const mmdd = entry.mmdd;

            devotionalContent.title.textContent = entry.title || 'Title not found';
            devotionalContent.displayDateElement.textContent = entry.display_date || formatDisplayDate(pickerDate || currentDate);
            devotionalContent.devotional.textContent = entry.bible_verse || 'Verse not found.';

            if (esvCache && esvCache[mmdd] && esvCache[mmdd].text) {
                devotionalContent.esv.textContent = esvCache[mmdd].text;
                devotionalContent.esvBlock.classList.remove('hidden');
            } else {
                devotionalContent.esv.textContent = '';
                devotionalContent.esvBlock.classList.add('hidden');
            }

            devotionalContent.verseRef.textContent = entry.verse_ref || '';

            if (entry.poem) {
                renderPoemLines(entry.poem);
            } else {
                devotionalContent.poem.textContent = 'Poem not found.';
            }

            updatePermalink(entry);
            return;
        }

        devotionalContent.title.textContent = 'No Entry Available';
        devotionalContent.displayDateElement.textContent = pickerDate ? formatDisplayDate(pickerDate) : '';
        devotionalContent.devotional.textContent = 'There is no devotional entry for this day.';
        devotionalContent.verseRef.textContent = '';
        devotionalContent.esvBlock.classList.add('hidden');
        devotionalContent.poem.textContent = '';
        updatePermalink(null);
    }

    // --- Display Logic ---
    function renderPoemLines(poemText) {
        if (!poemText) {
            devotionalContent.poem.textContent = '';
            return;
        }

        const fragment = document.createDocumentFragment();
        const lines = poemText.split(/\r?\n/);
        lines.forEach((line) => {
            const lineElement = document.createElement('div');
            lineElement.classList.add('poem-line');
            const cleanedLine = line.replace(/\r/g, '');
            if (!cleanedLine.trim()) {
                lineElement.classList.add('poem-line--blank');
            }
            lineElement.textContent = cleanedLine;
            fragment.appendChild(lineElement);
        });
        devotionalContent.poem.replaceChildren(fragment);
    }

    function displayEntryForDate(date) {
        const entry = findEntry(date);
        currentYear = date.getFullYear();
        currentDate = date;
        displayEntry(entry, date);
    }

    // --- Event Listeners ---
    prevDayBtn.addEventListener('click', () => {
        const previousEntry = getAdjacentEntry(currentEntry, -1);
        if (previousEntry) {
            displayEntry(previousEntry, buildPickerDate(previousEntry, currentYear));
        }
    });

    nextDayBtn.addEventListener('click', () => {
        const nextEntry = getAdjacentEntry(currentEntry, 1);
        if (nextEntry) {
            displayEntry(nextEntry, buildPickerDate(nextEntry, currentYear));
        }
    });

    datePicker.addEventListener('change', () => {
        const selectedDateValue = datePicker.value; // YYYY-MM-DD
        if (selectedDateValue) {
            // Date picker gives date in local timezone based on YYYY-MM-DD.
            // new Date('YYYY-MM-DD') can have timezone issues (interprets as UTC midnight).
            // Safer:
            const parts = selectedDateValue.split('-');
            const year = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1; // Month is 0-indexed in JS Date
            const day = parseInt(parts[2], 10);
            const selectedDate = new Date(year, month, day);
            currentYear = year;
            displayEntryForDate(selectedDate);
        }
    });

    if (datePickerWrap) {
        datePickerWrap.addEventListener('click', () => {
            if (typeof datePicker.showPicker === 'function') {
                datePicker.showPicker();
                return;
            }
            datePicker.focus();
        });
    }

    // Initial load
    loadDevotionals();
});
