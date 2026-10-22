const api = acquireVsCodeApi();
let saved = api.getState() ?? {};
let rendered = false;
const persist = () => {
  if (!rendered) return;
  saved.scroll = window.scrollY;
  saved.queryExpanded = document.getElementById("query-details").open;
  saved.expanded = [...document.querySelectorAll("#results details")]
    .filter((item) => item.open)
    .map((item) => item.dataset.file);
  api.setState(saved);
};
window.addEventListener("scroll", persist);
document.getElementById("query-details").addEventListener("toggle", persist);
window.addEventListener("message", ({ data }) => {
  if (data.type !== "snapshot") return;
  rendered = false;
  const view = {
    selected: saved.selected ?? data.snapshot.selected,
    scroll: saved.scroll ?? data.snapshot.scroll,
    expanded: saved.expanded ?? data.snapshot.expanded,
    queryExpanded: saved.queryExpanded ?? data.snapshot.queryExpanded,
  };
  saved = { ...data.snapshot, ...view };
  document.getElementById("title").textContent = saved.title;
  document.getElementById("query").textContent = saved.query;
  document.getElementById("query-details").open = saved.queryExpanded ?? false;
  document.getElementById("count").textContent =
    `${saved.results.length} pinned results`;
  const root = document.getElementById("results");
  root.replaceChildren();
  const groups = new Map();
  for (const [index, result] of saved.results.entries()) {
    let group = groups.get(result.file);
    if (!group) {
      group = document.createElement("details");
      group.dataset.file = result.file;
      group.open = saved.expanded ? saved.expanded.includes(result.file) : true;
      const summary = document.createElement("summary");
      summary.textContent = result.displayFile ?? result.file;
      summary.title = result.file;
      group.append(summary);
      root.append(group);
      groups.set(result.file, group);
      group.addEventListener("toggle", persist);
    }
    const button = document.createElement("button");
    button.className = "match";
    button.dataset.index = index;
    button.textContent = `${result.binding ? `${result.binding}: ` : ""}${result.name} · ${result.kind} · ${result.line}:${result.column}\n${result.excerpt}`;
    button.classList.toggle("selected", index === saved.selected);
    button.setAttribute("aria-pressed", String(index === saved.selected));
    button.addEventListener("click", () => {
      saved.selected = index;
      for (const item of root.querySelectorAll("button")) {
        const selected = Number(item.dataset.index) === index;
        item.classList.toggle("selected", selected);
        item.setAttribute("aria-pressed", String(selected));
      }
      persist();
      api.postMessage({ type: "open", index });
    });
    group.append(button);
  }
  api.setState(saved);
  requestAnimationFrame(() => {
    window.scrollTo(0, view.scroll ?? 0);
    requestAnimationFrame(() => {
      rendered = true;
      persist();
    });
  });
});
api.postMessage({ type: "ready" });
