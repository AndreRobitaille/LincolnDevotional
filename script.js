document.addEventListener('DOMContentLoaded', () => {
    const devotionalContent = {
        title: document.getElementById('entryTitle'),
        displayDateElement: document.getElementById('entryDisplayDate'), // For the MMMM D date below title
        devotional: document.getElementById('entryDevotional'),
        poem: document.getElementById('entryPoem')
    };
    const prevDayBtn = document.getElementById('prevDayBtn');
    const nextDayBtn = document.getElementById('nextDayBtn');
    const currentDisplayDateNav = document.getElementById('currentDisplayDate'); // For nav bar MMDD
    const datePicker = document.getElementById('datePicker');
    const goToDateBtn = document.getElementById('goToDateBtn');

    let allEntries = [];
    let currentDate = new Date(); // Holds the date currently being viewed

    // --- Data Loading ---
    async function loadDevotionals() {
        try {
            const response = await fetch('lincoln_devotional_fixed.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            allEntries = await response.json();
            // Set date picker to today and load today's entry
            const today = new Date();
            datePicker.value = today.toISOString().split('T')[0]; // YYYY-MM-DD format
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
        return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    }


    function findEntry(date) {
        const mmdd = getMMDD(date);
        return allEntries.find(entry => entry.url_date_code === mmdd);
    }

    // --- Display Logic ---
    function displayEntryForDate(date) {
        const entry = findEntry(date);
        currentDate = date; // Update the global current date being viewed

        currentDisplayDateNav.textContent = formatNavDate(date);
        // Update the date picker to reflect the currently viewed date
        datePicker.value = date.toISOString().split('T')[0];


        if (entry) {
            devotionalContent.title.textContent = entry.title || "Title not found";
            // Use entry.display_date if available, otherwise format from the JS Date object
            devotionalContent.displayDateElement.textContent = entry.display_date || formatDisplayDate(date);
            devotionalContent.devotional.textContent = entry.devotional || "Devotional not found.";
            devotionalContent.poem.textContent = entry.poem || "Poem not found.";
        } else {
            devotionalContent.title.textContent = "No Entry Available";
            devotionalContent.displayDateElement.textContent = formatDisplayDate(date);
            devotionalContent.devotional.textContent = "There is no devotional entry for this day.";
            devotionalContent.poem.textContent = "";
        }
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

    goToDateBtn.addEventListener('click', () => {
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

    // Initial load
    loadDevotionals();
});
