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

    let allEntries = [];
    let esvCache = {};
    let currentDate = new Date();

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

            // Set date picker to today and load today's entry
            const today = new Date();
            datePicker.value = today.toLocaleDateString('en-CA'); 
            currentDate = today; 
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
        currentDate = date; // Update the global current date being viewed

        currentDisplayDateNav.textContent = formatNavDate(date);
        // Update the date picker to reflect the currently viewed date.
        // Using locale formatting avoids off-by-one errors from UTC conversion.
        datePicker.value = date.toLocaleDateString('en-CA');


        if (entry) {
            const mmdd = entry.mmdd;

            devotionalContent.title.textContent = entry.title || "Title not found";
            devotionalContent.displayDateElement.textContent = entry.display_date || formatDisplayDate(date);
            
            // KJV Verse (Always present)
            devotionalContent.devotional.textContent = entry.bible_verse || "Verse not found.";
            
            // ESV Verse (Check cache)
            if (esvCache && esvCache[mmdd] && esvCache[mmdd].text) {
                devotionalContent.esv.textContent = esvCache[mmdd].text;
                devotionalContent.esvBlock.classList.remove('hidden');
            } else {
                devotionalContent.esv.textContent = "";
                devotionalContent.esvBlock.classList.add('hidden');
            }

            devotionalContent.verseRef.textContent = entry.verse_ref || "";
            
            if (entry.poem) {
                renderPoemLines(entry.poem);
            } else {
                devotionalContent.poem.textContent = "Poem not found.";
            }
        } else {
            devotionalContent.title.textContent = "No Entry Available";
            devotionalContent.displayDateElement.textContent = formatDisplayDate(date);
            devotionalContent.devotional.textContent = "There is no devotional entry for this day.";
            devotionalContent.verseRef.textContent = "";
            devotionalContent.esvBlock.classList.add('hidden');
            devotionalContent.poem.textContent = "";
        }

        // Removed Reftagger call since it is no longer used
    }

    // --- Event Listeners ---
    prevDayBtn.addEventListener('click', () => {
        const newDate = new Date(currentDate);
        newDate.setDate(currentDate.getDate() - 1);
        displayEntryForDate(newDate);
    });

    nextDayBtn.addEventListener('click', () => {
        const newDate = new Date(currentDate);
        newDate.setDate(currentDate.getDate() + 1);
        displayEntryForDate(newDate);
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
