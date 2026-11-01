(function () {
  "use strict";

  const dataNode = document.getElementById("explore-data");
  const resultsNode = document.querySelector("[data-explore-results]");
  const countNode = document.querySelector("[data-result-count]");
  const clearButton = document.querySelector(".explore-clear");
  const searchInput = document.getElementById("devotion-search");
  const searchStatus = document.getElementById("search-status");
  const retiredFilter = document.querySelector("[data-retired-filter]");
  const filterDescription = document.querySelector("[data-filter-description]");
  if (!dataNode || !resultsNode) {
    return;
  }

  let data;
  try {
    data = JSON.parse(dataNode.textContent || "{}");
  } catch (err) {
    renderMessage("Unable to load devotions.");
    return;
  }

  const entries = Array.isArray(data.entries) ? data.entries : [];
  const monthsByNumber = new Map((data.months || []).map((m) => [m.number, m.name]));
  let searchIndex = null;
  let searchPromise = null;

  function normalizeSearch(text) {
    return text.normalize("NFKC")
      .toLowerCase()
      .replace(/[‘’]/g, "'")
      .replace(/[–—]/g, "-")
      .replace(/\s+/g, " ")
      .trim();
  }

  function loadSearchIndex() {
    if (searchIndex || searchPromise) return searchPromise;
    searchStatus.textContent = "Loading search…";
    searchPromise = (async function () {
      try {
        const response = await fetch("../data/search-index.json");
        if (!response.ok) throw new Error("Search index HTTP " + response.status);
        const records = await response.json();
        if (!Array.isArray(records)) throw new Error("Invalid search index");
        const index = new Map(records.map((record) => [record.mmdd, record]));
        const fields = ["title", "verse_ref", "devotional", "kjv", "esv"];
        if (!entries.every((entry) => {
          const record = index.get(entry.mmdd);
          return record && fields.every((field) => typeof record[field] === "string");
        })) {
          throw new Error("Incomplete search index");
        }
        searchIndex = index;
        searchStatus.textContent = "";
        renderResults();
      } catch (err) {
        console.error("Unable to load search index:", err);
        searchStatus.textContent = "Search is unavailable. You can still browse devotions; type again to retry.";
        searchPromise = null;
        renderResults();
      }
    })();
    return searchPromise;
  }

  function searchFields(record) {
    return [
      { label: "Title", text: record.title },
      { label: "Reference", text: record.verse_ref },
      { label: "Devotional", text: record.devotional },
      { label: "KJV", text: record.kjv },
      { label: "ESV", text: record.esv },
    ];
  }

  function matchesSearch(entry, query) {
    if (!query) return true;
    return searchFields(searchIndex.get(entry.mmdd)).some((field) =>
      normalizeSearch(field.text).includes(query),
    );
  }

  function searchSnippet(entry, query) {
    const record = searchIndex.get(entry.mmdd);
    const fields = searchFields(record);
    // Prefer matching passage text; title/reference-only hits get a poem excerpt.
    const field = fields.slice(2).find((item) =>
      normalizeSearch(item.text).includes(query),
    ) || fields[2];
    const text = normalizeSearch(field.text);
    const position = Math.max(0, text.indexOf(query));
    const start = Math.max(0, text.lastIndexOf(" ", Math.max(0, position - 45)) + 1);
    const displayText = field.text.normalize("NFKC").replace(/\s+/g, " ").trim();
    let end = Math.min(displayText.length, start + Math.max(150, query.length));
    if (end < displayText.length) {
      const wordEnd = displayText.lastIndexOf(" ", end);
      if (wordEnd > position + query.length) end = wordEnd;
    }
    const excerpt = (start ? "…" : "") + displayText.slice(start, end)
      + (end < displayText.length ? "…" : "");
    return record.verse_ref + " · " + field.label + ": " + excerpt;
  }

  // Global single-select: at most one chip is active across both facets.
  // state.facet is "topic" | "need" | null; state.slug is the selected value or null.
  const state = {
    facet: null,
    slug: null,
  };

  function firstValue(raw) {
    if (!raw) return null;
    const value = raw.split(",")[0].trim();
    return value || null;
  }

  function readUrlState() {
    const params = new URLSearchParams(window.location.search);
    const topic = firstValue(params.get("topic"));
    const need = firstValue(params.get("need"));
    if (topic) {
      state.facet = "topic";
      state.slug = topic;
    } else if (need) {
      state.facet = "need";
      state.slug = need;
    } else {
      state.facet = null;
      state.slug = null;
    }
  }

  function writeUrlState() {
    const params = new URLSearchParams(window.location.search);
    params.delete("topic");
    params.delete("need");
    if (state.facet && state.slug) {
      params.set(state.facet, state.slug);
    }
    const search = params.toString();
    const newUrl = window.location.pathname + (search ? "?" + search : "");
    window.history.replaceState(null, "", newUrl);
  }

  function matchesFilters(entry) {
    if (!state.facet || !state.slug) {
      return true;
    }
    const haystack =
      state.facet === "topic" ? entry.topics || [] : entry.needs || [];
    return haystack.indexOf(state.slug) !== -1;
  }

  function groupByMonth(filtered) {
    const groups = new Map();
    for (const entry of filtered) {
      if (!groups.has(entry.month)) {
        groups.set(entry.month, []);
      }
      groups.get(entry.month).push(entry);
    }
    return groups;
  }

  function el(tag, props, children) {
    const node = document.createElement(tag);
    if (props) {
      for (const key in props) {
        if (!Object.prototype.hasOwnProperty.call(props, key)) continue;
        if (key === "class") {
          node.className = props[key];
        } else if (key === "text") {
          node.textContent = props[key];
        } else {
          node.setAttribute(key, props[key]);
        }
      }
    }
    if (children) {
      for (const child of children) {
        if (child) node.appendChild(child);
      }
    }
    return node;
  }

  function renderMessage(text) {
    resultsNode.textContent = "";
    resultsNode.appendChild(el("p", { class: "explore-empty", text: text }));
  }

  function renderFilterContext() {
    const records = state.facet === "need" ? data.needs : data.topics;
    const selected = (records || []).find((record) => record.slug === state.slug);
    if (filterDescription) {
      filterDescription.hidden = !selected;
      filterDescription.textContent = selected
        ? selected.name + ": " + selected.description : "";
    }
    if (!retiredFilter) return !state.facet || Boolean(selected);
    retiredFilter.replaceChildren();
    retiredFilter.hidden = !state.facet || Boolean(selected);
    if (retiredFilter.hidden) return true;

    const legacyChoices = (data.legacy || {})[state.slug];
    const suggestions = Array.isArray(legacyChoices) ? legacyChoices : [];
    retiredFilter.appendChild(el("p", {
      text: suggestions.length
        ? "This older filter has been replaced. Choose a focused tag, or clear filters to browse all readings."
        : "This filter is unavailable. Choose another tag, or clear filters to browse all readings.",
    }));
    const choices = el("div", { class: "facet-chips" });
    for (const suggestion of suggestions) {
      const params = new URLSearchParams(window.location.search);
      params.delete("topic");
      params.delete("need");
      params.set(suggestion.facet, suggestion.slug);
      choices.appendChild(el("a", {
        class: "facet-chip",
        href: "?" + params.toString(),
        text: suggestion.name,
      }));
    }
    retiredFilter.appendChild(choices);
    return false;
  }

  function renderResults() {
    const validFilter = renderFilterContext();
    if (clearButton) clearButton.hidden = !state.facet;
    if (!validFilter) {
      if (countNode) countNode.textContent = "Choose a tag";
      renderMessage("Choose a focused tag above, or clear filters to see all devotions.");
      return;
    }
    const query = searchIndex && searchInput ? normalizeSearch(searchInput.value) : "";
    const filtered = entries.filter((entry) =>
      matchesFilters(entry) && matchesSearch(entry, query),
    );

    if (countNode) {
      const word = filtered.length === 1 ? "devotion" : "devotions";
      countNode.textContent = filtered.length + " " + word;
    }
    if (clearButton) {
      clearButton.hidden = !state.facet;
    }

    if (filtered.length === 0) {
      const message = query
        ? "No devotions match your search and filters. Try another word or clear a filter."
        : "No devotions match these filters. Try clearing one.";
      renderMessage(message);
      return;
    }

    resultsNode.textContent = "";
    const groups = groupByMonth(filtered);
    const monthNumbers = Array.from(groups.keys()).sort((a, b) => a - b);
    const showPrimaryBadge = state.facet === "topic";

    const fragment = document.createDocumentFragment();
    for (const num of monthNumbers) {
      const monthEntries = groups.get(num);
      const monthName = monthsByNumber.get(num) || "";
      const countLabel =
        monthEntries.length === 1
          ? "1 devotion"
          : monthEntries.length + " devotions";

      const header = el("header", { class: "explore-month-header" }, [
        el("h3", { class: "explore-month-title", text: monthName }),
        el("span", { class: "explore-month-count", text: countLabel }),
      ]);

      const list = el("ul", { class: "explore-entries-list" });
      for (const entry of monthEntries) {
        const link = el("a", {
          class: "explore-entry",
          href: entry.href,
        });
        link.appendChild(
          el("span", { class: "explore-entry-date", text: entry.display_date }),
        );
        link.appendChild(
          el("span", { class: "explore-entry-title", text: entry.title }),
        );
        if (showPrimaryBadge && entry.primary === state.slug) {
          link.appendChild(
            el("span", { class: "explore-entry-primary", text: "Primary" }),
          );
        }
        if (query) {
          link.appendChild(el("span", {
            class: "explore-entry-snippet",
            text: searchSnippet(entry, query),
          }));
        }
        list.appendChild(el("li", {}, [link]));
      }

      fragment.appendChild(
        el("section", { class: "explore-month" }, [header, list]),
      );
    }
    resultsNode.appendChild(fragment);
  }

  function syncChipStates() {
    document.querySelectorAll(".facet-chip").forEach((chip) => {
      const active =
        state.facet === chip.dataset.facet && state.slug === chip.dataset.slug;
      chip.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function toggleChip(chip) {
    if (chip.dataset.disabled === "true") {
      return;
    }
    const facet = chip.dataset.facet;
    const slug = chip.dataset.slug;
    if (state.facet === facet && state.slug === slug) {
      // Clicking the active chip clears the selection.
      state.facet = null;
      state.slug = null;
    } else {
      // Clicking any other chip replaces whatever was selected before.
      state.facet = facet;
      state.slug = slug;
    }
    syncChipStates();
    writeUrlState();
    renderResults();
  }

  function clearAll() {
    state.facet = null;
    state.slug = null;
    syncChipStates();
    writeUrlState();
    renderResults();
  }

  document.querySelectorAll(".facet-chip").forEach((chip) => {
    chip.addEventListener("click", function () {
      toggleChip(chip);
    });
  });
  if (clearButton) {
    clearButton.addEventListener("click", clearAll);
  }
  if (searchInput && searchStatus) {
    searchInput.closest(".explore-search").hidden = false;
    searchInput.addEventListener("focus", loadSearchIndex);
    searchInput.addEventListener("input", function () {
      loadSearchIndex();
      renderResults();
    });
  }
  window.addEventListener("popstate", function () {
    readUrlState();
    syncChipStates();
    renderResults();
  });

  readUrlState();
  syncChipStates();
  renderResults();
})();
