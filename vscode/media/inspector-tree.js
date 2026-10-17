let lastReveal;

export function renderTree(host, state, post) {
  const active =
    document.hasFocus() && host.contains(document.activeElement)
      ? document.activeElement.closest("[role=treeitem]")?.dataset.node
      : undefined;
  const top = host.scrollTop,
    rows = state.tree,
    elements = new Map();
  const selectedId = rows.find((row) => row.selected)?.id;
  const groups = new Map(),
    positions = new Map();
  for (const row of rows) {
    const siblings = groups.get(row.parent) ?? [];
    siblings.push(row.id);
    groups.set(row.parent, siblings);
  }
  for (const siblings of groups.values())
    for (const [index, id] of siblings.entries())
      positions.set(id, [index + 1, siblings.length]);
  host.replaceChildren();
  host.setAttribute("aria-busy", String(state.running));
  const focus = (id) => {
    elements.get(id)?.focus();
    post("child", { id });
  };
  for (const [index, row] of rows.entries()) {
    const item = document.createElement("li"),
      line = document.createElement("div"),
      toggle = document.createElement(row.expandable ? "button" : "span"),
      name = document.createElement("span"),
      kind = document.createElement("span");
    item.setAttribute("role", "treeitem");
    item.setAttribute("aria-level", String(row.depth + 1));
    item.setAttribute("aria-selected", String(row.selected));
    item.setAttribute("aria-disabled", String(state.running));
    item.setAttribute("aria-posinset", String(positions.get(row.id)[0]));
    item.setAttribute("aria-setsize", String(positions.get(row.id)[1]));
    if (row.expandable)
      item.setAttribute("aria-expanded", String(row.expanded));
    item.setAttribute("aria-label", `${row.kind}: ${row.name}`);
    item.dataset.node = row.id;
    item.dataset.loaded = String(row.loaded);
    item.tabIndex = row.selected || (!selectedId && index === 0) ? 0 : -1;
    item.className = row.selected ? "ast-item selected" : "ast-item";
    line.className = "tree-row";
    line.style.setProperty("--depth", String(row.depth));
    toggle.className = "twisty";
    if (row.expandable) {
      toggle.textContent = row.expanded ? "▾" : "▸";
      toggle.tabIndex = -1;
      toggle.disabled = state.running;
      toggle.setAttribute(
        "aria-label",
        `${row.expanded ? "Collapse" : "Expand"} ${row.name}`,
      );
      toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        item.focus();
        post("expand", { id: row.id, expanded: !row.expanded });
      });
    } else toggle.setAttribute("aria-hidden", "true");
    name.className = "tree-name";
    name.textContent = row.name;
    kind.className = "tree-kind";
    kind.textContent = row.name === row.kind ? "" : row.kind;
    item.title = row.locationValid
      ? `${row.kind} · ${row.file}:${row.line}:${row.column}`
      : row.kind;
    line.append(toggle, name, kind);
    item.append(line);
    item.addEventListener("click", () => {
      if (state.running) return;
      item.focus();
      post("child", { id: row.id });
    });
    item.addEventListener("keydown", (event) => {
      if (state.running) return;
      const next =
        event.key === "ArrowDown"
          ? rows[index + 1]
          : event.key === "ArrowUp"
            ? rows[index - 1]
            : event.key === "Home"
              ? rows[0]
              : event.key === "End"
                ? rows.at(-1)
                : undefined;
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        if (next) focus(next.id);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        if (row.expandable && !row.expanded)
          post("expand", { id: row.id, expanded: true });
        else if (rows[index + 1]?.parent === row.id) focus(rows[index + 1].id);
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        if (row.expandable && row.expanded)
          post("expand", { id: row.id, expanded: false });
        else if (row.parent) focus(row.parent);
      } else if (["Enter", " "].includes(event.key)) {
        event.preventDefault();
        post("child", { id: row.id });
      }
    });
    elements.set(row.id, item);
    host.append(item);
  }
  host.scrollTop = top;
  if (active) (elements.get(active) ?? elements.get(selectedId))?.focus();
  if (state.treeReveal !== lastReveal) {
    elements
      .get(selectedId)
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
    lastReveal = state.treeReveal;
  }
  return [...host.querySelectorAll("[role=treeitem]")].map((item) => ({
    id: item.dataset.node,
    level: Number(item.getAttribute("aria-level")),
    ...(item.hasAttribute("aria-expanded")
      ? { expanded: item.getAttribute("aria-expanded") === "true" }
      : {}),
    selected: item.getAttribute("aria-selected") === "true",
    loaded: item.dataset.loaded === "true",
  }));
}
