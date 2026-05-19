document.addEventListener("DOMContentLoaded", () => {
  const pickerWrap = document.querySelector('.date-picker-wrap[data-entry-mmdd]');

  if (!pickerWrap) {
    console.warn("Static entry nav: missing date picker wrapper.");
    return;
  }

  const dateInput = pickerWrap.querySelector(".nav-date-input");
  const currentDateDisplay = pickerWrap.querySelector(".current-date-display");
  const entryMmdd = pickerWrap.dataset.entryMmdd;
  const routesPath = pickerWrap.dataset.routesPath;

  if (!dateInput || !currentDateDisplay || !entryMmdd || !routesPath) {
    console.warn("Static entry nav: missing required navigation elements.");
    return;
  }

  const buildCurrentYearDate = (mmdd) => {
    if (!/^\d{4}$/.test(mmdd)) {
      return null;
    }

    const month = Number(mmdd.slice(0, 2));
    const day = Number(mmdd.slice(2, 4));
    const year = 2024;
    const date = new Date(year, month - 1, day);

    if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
      return null;
    }

    return date;
  };

  const toDateInputValue = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  };

  const getMmddFromInputValue = (value) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return null;
    }

    return `${value.slice(5, 7)}${value.slice(8, 10)}`;
  };

  let routeMapPromise;
  const loadRouteMap = async () => {
    if (!routeMapPromise) {
      routeMapPromise = fetch(routesPath).then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load route map: ${response.status}`);
        }

        return response.json();
      });
    }

    return routeMapPromise;
  };

  const currentYearDate = buildCurrentYearDate(entryMmdd);
  if (currentYearDate) {
    dateInput.value = toDateInputValue(currentYearDate);
    currentDateDisplay.title = `Current page date: ${currentDateDisplay.textContent}`;
  }

  pickerWrap.addEventListener("click", () => {
    if (typeof dateInput.showPicker === "function") {
      dateInput.showPicker();
      return;
    }

    dateInput.focus();
  });

  dateInput.addEventListener("click", (event) => {
    event.stopPropagation();
  });

  dateInput.addEventListener("change", async () => {
    const mmdd = getMmddFromInputValue(dateInput.value);

    if (!mmdd) {
      console.warn("Static entry nav: invalid selected date.");
      return;
    }

    try {
      const routes = await loadRouteMap();
      const href = routes[mmdd];

      if (!href) {
        console.warn(`Static entry nav: no route found for ${mmdd}.`);
        return;
      }

      window.location.href = href;
    } catch (error) {
      console.error("Static entry nav: failed to resolve route.", error);
    }
  });
});
