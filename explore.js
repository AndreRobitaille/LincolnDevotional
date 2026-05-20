(function () {
  "use strict";

  const dataNode = document.getElementById("explore-data");
  const resultsNode = document.querySelector("[data-explore-results]");
  const countNode = document.querySelector("[data-result-count]");
  const clearButton = document.querySelector(".explore-clear");
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

  function renderResults() {
    const filtered = entries.filter(matchesFilters);

    if (countNode) {
      const word = filtered.length === 1 ? "devotion" : "devotions";
      countNode.textContent = filtered.length + " " + word;
    }
    if (clearButton) {
      clearButton.hidden = !state.facet;
    }

    if (filtered.length === 0) {
      renderMessage("No devotions match these filters. Try clearing one.");
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
  window.addEventListener("popstate", function () {
    readUrlState();
    syncChipStates();
    renderResults();
  });

  readUrlState();
  syncChipStates();
  renderResults();
})();
