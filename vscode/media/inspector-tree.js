let lastReveal;
let wasVisible = false;
const views = new WeakMap();

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
  let view = views.get(host);
  if (!view) {
    view = { items: new Map() };
    views.set(host, view);
  }
  view.state = state;
  view.post = post;
  const ids = new Set(rows.map((row) => row.id));
  for (const [id, entry] of view.items)
    if (!ids.has(id)) {
      entry.item.remove();
      view.items.delete(id);
    }
  host.setAttribute("aria-busy", String(state.running));
  for (const [index, row] of rows.entries()) {
    let entry = view.items.get(row.id);
    if (!entry) {
      const item = document.createElement("li"),
        line = document.createElement("div"),
        toggle = document.createElement("button"),
        name = document.createElement("span"),
        kind = document.createElement("span");
      line.append(toggle, name, kind);
      item.append(line);
      entry = { item, line, toggle, name, kind };
      view.items.set(row.id, entry);
      const current = () =>
        view.state.tree.find((candidate) => candidate.id === row.id);
      toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        const row = current();
        if (!row || view.state.running) return;
        item.focus();
        view.post("expand", { id: row.id, expanded: !row.expanded });
      });
      toggle.addEventListener("dblclick", (event) => event.stopPropagation());
      item.addEventListener("click", () => {
        if (view.state.running) return;
        item.focus();
        view.post("child", { id: row.id });
      });
      item.addEventListener("dblclick", () => {
        if (view.state.running && !current()?.selected) return;
        view.post("properties", { id: row.id });
      });
      item.addEventListener("keydown", (event) => {
        if (view.state.running) return;
        const row = current();
        if (!row) return;
        const rows = view.state.tree,
          index = rows.findIndex((candidate) => candidate.id === row.id);
        const select = (id) => {
          view.items.get(id)?.item.focus();
          view.post("child", { id });
        };
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
          if (next) select(next.id);
        } else if (event.key === "ArrowRight") {
          event.preventDefault();
          if (row.expandable && !row.expanded)
            view.post("expand", { id: row.id, expanded: true });
          else if (rows[index + 1]?.parent === row.id)
            select(rows[index + 1].id);
        } else if (event.key === "ArrowLeft") {
          event.preventDefault();
          if (row.expandable && row.expanded)
            view.post("expand", { id: row.id, expanded: false });
          else if (row.parent) select(row.parent);
        } else if (["Enter", " "].includes(event.key)) {
          event.preventDefault();
          view.post(event.key === "Enter" ? "properties" : "child", {
            id: row.id,
          });
        }
      });
    }
    const { item, line, toggle, name, kind } = entry;
    item.setAttribute("role", "treeitem");
    item.setAttribute("aria-level", String(row.depth + 1));
    item.setAttribute("aria-selected", String(row.selected));
    item.setAttribute("aria-disabled", String(state.running));
    item.setAttribute("aria-posinset", String(positions.get(row.id)[0]));
    item.setAttribute("aria-setsize", String(positions.get(row.id)[1]));
    if (row.expandable)
      item.setAttribute("aria-expanded", String(row.expanded));
    else item.removeAttribute("aria-expanded");
    item.setAttribute("aria-label", `${row.kind}: ${row.name}`);
    item.dataset.node = row.id;
    item.dataset.vscodeContext = JSON.stringify({
      webviewSection: "ast-node",
      ctkAstNodeId: row.id,
      ctkAstContext: state.contextId,
      ctkAstCanRun: !state.running,
      preventDefaultContextMenuItems: true,
    });
    item.dataset.loaded = String(row.loaded);
    item.tabIndex = row.selected || (!selectedId && index === 0) ? 0 : -1;
    item.className = row.selected ? "ast-item selected" : "ast-item";
    line.className = "tree-row";
    line.style.setProperty("--depth", String(row.depth));
    toggle.className = row.expandable ? "twisty" : "twisty leaf";
    if (row.expandable) {
      toggle.textContent = row.expanded ? "▾" : "▸";
      toggle.tabIndex = -1;
      toggle.disabled = state.running;
      toggle.setAttribute(
        "aria-label",
        `${row.expanded ? "Collapse" : "Expand"} ${row.name}`,
      );
    }
    toggle.setAttribute("aria-hidden", String(!row.expandable));
    toggle.tabIndex = -1;
    name.className = "tree-name";
    name.textContent = row.name;
    kind.className = "tree-kind";
    kind.textContent = row.name === row.kind ? "" : row.kind;
    item.title = row.locationValid
      ? `${row.kind} · ${row.file}:${row.line}:${row.column}`
      : row.kind;
    elements.set(row.id, item);
    if (host.children[index] !== item)
      host.insertBefore(item, host.children[index] ?? null);
  }
  host.scrollTop = top;
  if (active) (elements.get(active) ?? elements.get(selectedId))?.focus();
  const visible = !host.closest("[hidden]");
  if (visible && (state.treeReveal !== lastReveal || !wasVisible)) {
    elements
      .get(selectedId)
      ?.scrollIntoView({ block: "nearest", inline: "nearest" });
    lastReveal = state.treeReveal;
  }
  wasVisible = visible;
  return [...host.querySelectorAll("[role=treeitem]")].map((item) => ({
    id: item.dataset.node,
    level: Number(item.getAttribute("aria-level")),
    ...(item.hasAttribute("aria-expanded")
      ? { expanded: item.getAttribute("aria-expanded") === "true" }
      : {}),
    selected: item.getAttribute("aria-selected") === "true",
    loaded: item.dataset.loaded === "true",
    context: JSON.parse(item.dataset.vscodeContext),
  }));
}
