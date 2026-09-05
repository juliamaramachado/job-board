(function () {
  "use strict";

  // Maps the exact "source" strings written by scrape.py to a short key
  // (used for the filter chips and the colored left-rule in CSS) and a
  // shorter display label.
  const SOURCE_META = {
    "USAJOBS": { key: "USAJOBS", label: "USAJOBS" },
    "Animal Behavior Society": { key: "ABS", label: "Animal Behavior Society" },
    "ISAE (Applied Ethology)": { key: "ISAE", label: "ISAE" },
  };

  const state = {
    jobs: [],
    activeSources: new Set(),
    query: "",
    sort: "date_desc",
  };

  const els = {
    metaLine: document.getElementById("meta-line"),
    search: document.getElementById("search"),
    sourceFilters: document.getElementById("source-filters"),
    sort: document.getElementById("sort"),
    resultCount: document.getElementById("result-count"),
    jobList: document.getElementById("job-list"),
    emptyState: document.getElementById("empty-state"),
  };

  function sourceMeta(sourceName) {
    return SOURCE_META[sourceName] || { key: sourceName, label: sourceName };
  }

  function formatDate(iso) {
    if (!iso) return "Undated";
    const d = new Date(iso + "T00:00:00Z");
    if (isNaN(d.getTime())) return "Undated";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function buildSourceChips(jobs) {
    const sources = Array.from(new Set(jobs.map((j) => j.source)));
    els.sourceFilters.innerHTML = "";
    sources.forEach((source) => {
      const meta = sourceMeta(source);
      state.activeSources.add(source);

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chip";
      btn.textContent = meta.label;
      btn.setAttribute("aria-pressed", "true");
      btn.dataset.source = source;
      btn.addEventListener("click", () => {
        const pressed = btn.getAttribute("aria-pressed") === "true";
        btn.setAttribute("aria-pressed", String(!pressed));
        if (pressed) {
          state.activeSources.delete(source);
        } else {
          state.activeSources.add(source);
        }
        render();
      });
      els.sourceFilters.appendChild(btn);
    });
  }

  function matchesQuery(job, query) {
    if (!query) return true;
    const blob = [job.title, job.org, job.location, job.category]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return blob.includes(query.toLowerCase());
  }

  function sortJobs(jobs, mode) {
    const sorted = jobs.slice();
    if (mode === "date_asc") {
      sorted.sort((a, b) => (a.date_posted || "0000-00-00").localeCompare(b.date_posted || "0000-00-00"));
    } else if (mode === "title_asc") {
      sorted.sort((a, b) => a.title.localeCompare(b.title));
    } else {
      sorted.sort((a, b) => (b.date_posted || "0000-00-00").localeCompare(a.date_posted || "0000-00-00"));
    }
    return sorted;
  }

  function renderJob(job) {
    const meta = sourceMeta(job.source);
    const li = document.createElement("li");
    li.className = "job";
    li.dataset.source = meta.key;

    const title = document.createElement("h2");
    title.className = "job-title";
    const link = document.createElement("a");
    link.href = job.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = job.title;
    title.appendChild(link);

    const metaLine = document.createElement("p");
    metaLine.className = "job-meta";
    const parts = [job.org, job.location, meta.label, job.category].filter(Boolean);
    metaLine.innerHTML = parts
      .map((p) => `<span>${escapeHtml(p)}</span>`)
      .join('<span class="sep">·</span>');

    const dateSpan = document.createElement("span");
    dateSpan.className = "job-date sep";
    dateSpan.textContent = "";

    li.appendChild(title);
    li.appendChild(metaLine);

    const dateP = document.createElement("p");
    dateP.className = "job-meta";
    dateP.innerHTML = `<span class="job-date">${escapeHtml(formatDate(job.date_posted))}</span>`;
    li.appendChild(dateP);

    return li;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function render() {
    const filtered = state.jobs
      .filter((j) => state.activeSources.has(j.source))
      .filter((j) => matchesQuery(j, state.query));

    const sorted = sortJobs(filtered, state.sort);

    els.jobList.innerHTML = "";
    sorted.forEach((job) => els.jobList.appendChild(renderJob(job)));

    els.resultCount.textContent = `${sorted.length} listing${sorted.length === 1 ? "" : "s"}`;
    els.emptyState.hidden = sorted.length !== 0;
  }

  function init(data) {
    state.jobs = data.jobs || [];
    buildSourceChips(state.jobs);

    const updated = data.generated_at
      ? new Date(data.generated_at).toLocaleString("en-US", {
          month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
        })
      : "not yet";
    els.metaLine.textContent = `Updated ${updated} · ${state.jobs.length} listings`;

    els.search.addEventListener("input", (e) => {
      state.query = e.target.value;
      render();
    });
    els.sort.addEventListener("change", (e) => {
      state.sort = e.target.value;
      render();
    });

    render();
  }

  fetch("data.json", { cache: "no-store" })
    .then((r) => r.json())
    .then(init)
    .catch((err) => {
      els.metaLine.textContent = "Could not load listings.";
      console.error(err);
    });
})();
