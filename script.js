document.addEventListener('DOMContentLoaded', () => {
    const devotionalContent = {
        title: document.getElementById('entryTitle'),
        displayDateElement: document.getElementById('entryDisplayDate'), // For the MMMM D date below title
        devotional: document.getElementById('entryDevotional'),
        verseRef: document.getElementById('entryVerseRef'),
        poem: document.getElementById('entryPoem')
    };
    const prevDayBtn = document.getElementById('prevDayBtn');
    const nextDayBtn = document.getElementById('nextDayBtn');
    const currentDisplayDateNav = document.getElementById('currentDisplayDate'); // For nav bar MMDD
    const datePicker = document.getElementById('datePicker');
    const datePickerWrap = document.getElementById('datePickerWrap');

    let allEntries = [];
    let currentDate = new Date(); // Holds the date currently being viewed

    // --- Data Loading ---
    async function loadDevotionals() {
        try {
            const response = await fetch('data/entries.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            allEntries = await response.json();
            // Set date picker to today and load today's entry
            const today = new Date();
            // Use locale-based formatting to avoid timezone issues when
            // populating the date input. toISOString() uses UTC which can
            // shift the day depending on the user's timezone.
            datePicker.value = today.toLocaleDateString('en-CA'); // YYYY-MM-DD format
            currentDate = today; // Initialize currentDate
            displayEntryForDate(currentDate);
        } catch (error) {
            console.error("Could not load devotional data:", error);
            devotionalContent.title.textContent = "Error loading data.";
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
            devotionalContent.title.textContent = entry.title || "Title not found";
            // Use entry.display_date if available, otherwise format from the JS Date object
            devotionalContent.displayDateElement.textContent = entry.display_date || formatDisplayDate(date);
            
            // Combine bible_verse and verse_ref
            devotionalContent.devotional.textContent = entry.bible_verse || "Verse not found.";
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
            devotionalContent.poem.textContent = "";
        }

         // After updating content, tell Reftagger to scan the new content
    if (window.refTagger && typeof window.refTagger.tag === 'function') {
        // console.log("Re-running Reftagger to tag new content..."); // Optional: for debugging
        window.refTagger.tag();
    } else {
        // This else block is just for debugging in case refTagger or its tag method isn't found.
        // console.log("Reftagger object or .tag() method not found. Reftagger might not have loaded yet or API changed.");
    }
    // --- END OF REFTAGGER SECTION ---

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
