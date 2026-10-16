const api = acquireVsCodeApi();
const element = (id) => document.getElementById(id);
const post = (type, data = {}) => api.postMessage({ type, ...data });
let state;
let actionRevision;
let searchRevision;
let resultRevision;
let searchResults;
const values = (selector, key) =>
  Object.fromEntries(
    [...document.querySelectorAll(selector)].map((input) => [
      input.dataset[key],
      input.value,
    ]),
  );
const nodeValues = () => values("[data-argument]", "argument");
element("node-options").addEventListener("input", () =>
  post("nodeArguments", {
    revision: state?.actions.action?.revision ?? "",
    values: nodeValues(),
  }),
);
function search(type) {
  post(type, {
    values: values("[data-parameter]", "parameter"),
    scope: element("scope").value,
    kinds: [...document.querySelectorAll("#kinds input:checked")].map(
      (input) => input.value,
    ),
    source: state?.source ?? "",
  });
}
element("run").addEventListener("click", () => search("run"));
element("symbols-panel").addEventListener("input", () => search("update"));
element("symbols-panel").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.matches("input")) {
    event.preventDefault();
    search("run");
  }
});
element("output").addEventListener("click", () => post("showOutput"));
for (const tab of ["symbols", "actions"]) {
  element(`${tab}-tab`).addEventListener("click", () => post("tab", { tab }));
  element(`${tab}-tab`).addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      const next = tab === "symbols" ? "actions" : "symbols";
      post("tab", { tab: next });
      element(`${next}-tab`).focus();
    }
  });
}
element("node-picker").addEventListener("click", () => post("nodeChoose"));
element("node-run").addEventListener("click", () =>
  post("nodeRun", { values: nodeValues() }),
);
element("node-options").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.matches("input")) {
    event.preventDefault();
    post("nodeRun", { values: nodeValues() });
  }
});
element("node-followup").addEventListener("click", () =>
  post("nodeChoose", { followup: true }),
);
for (const [id, type] of [
  ["node-back", "nodeBack"],
  ["node-root", "nodeRoot"],
  ["node-refresh", "nodeRefresh"],
  ["node-close", "nodeClose"],
  ["node-edit", "nodeEdit"],
])
  element(id).addEventListener("click", () => post(type));
for (const view of ["bindings", "files"])
  element(`${view}-view`).addEventListener("click", () =>
    post("nodeView", { view }),
  );
function paragraph(parent, text, className = "muted") {
  const p = document.createElement("p");
  p.className = className;
  p.textContent = text;
  parent.append(p);
  return p;
}
function group(parent, label, open = true) {
  const details = document.createElement("details");
  details.open = open;
  const summary = document.createElement("summary");
  summary.textContent = label;
  details.append(summary);
  parent.append(details);
  return details;
}
function match(parent, result, node = false) {
  const button = document.createElement("button");
  button.className = node ? "node-match match" : "match";
  if (node) {
    button.dataset.node = result.nodeId;
    button.classList.toggle(
      "selected",
      result.nodeId === state.actions.selected,
    );
    button.setAttribute(
      "aria-pressed",
      String(result.nodeId === state.actions.selected),
    );
  }
  button.title = `${result.file}:${result.line}:${result.column}`;
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = `${node ? `${result.binding} · ` : ""}${result.name} · ${result.line}`;
  const excerpt = document.createElement("span");
  excerpt.className = "excerpt";
  excerpt.textContent = result.excerpt;
  button.append(name, excerpt);
  button.addEventListener("click", () =>
    post(node ? "nodeSelect" : "openResult", {
      id: node ? result.nodeId : result.id,
    }),
  );
  parent.append(button);
}
function renderSearch() {
  const revision = JSON.stringify([
    state.action.id,
    state.action.parameters,
    state.values,
  ]);
  if (
    revision !== searchRevision &&
    !element("fields").contains(document.activeElement)
  ) {
    searchRevision = revision;
    element("fields").replaceChildren();
    for (const p of state.action.parameters) {
      const input = document.createElement("input");
      input.dataset.parameter = p.name;
      input.placeholder = p.label;
      input.setAttribute("aria-label", p.label);
      input.value = state.values[p.name] ?? p.default ?? "";
      element("fields").append(input);
    }
  }
  element("scope").value = state.scope;
  element("target").textContent = state.target || "Open a C++ file to search.";
  for (const input of document.querySelectorAll("#kinds input"))
    input.checked = state.kinds.includes(input.value);
  for (const input of element("symbols-panel").querySelectorAll(
    "button,input,select",
  ))
    input.disabled = state.running;
  element("status").textContent = state.completed ? state.status : "";
  element("output").hidden = !state.errors.length && !state.output.length;
  element("errors").replaceChildren();
  for (const error of state.errors) paragraph(element("errors"), error, "");
  const resultKey = JSON.stringify([state.results, state.completed]);
  if (resultKey !== searchResults) {
    searchResults = resultKey;
    element("results").replaceChildren();
    const groups = new Map();
    for (const result of state.results) {
      if (!groups.has(result.file))
        groups.set(result.file, group(element("results"), result.displayFile));
      match(groups.get(result.file), result);
    }
    if (!state.results.length)
      paragraph(
        element("results"),
        state.completed
          ? "No matches."
          : "Search for a variable, class or function.",
      );
  }
  post("rendered", {
    action: state.action.id,
    matches: element("results").querySelectorAll(".match").length,
    groups: element("results").querySelectorAll(":scope > details").length,
  });
}
function renderActions() {
  const a = state.actions;
  if (!a) return;
  if (a.invalidAction || a.running || state.tab !== "actions")
    window.CtkArgumentCompletion.close();
  element("node-context").textContent = a.input
    ? `Input: ${a.input.label} · ${a.input.file}`
    : a.target
      ? `Input: file root · ${a.target}`
      : "Input: active C++ file root";
  element("node-picker").textContent =
    `${a.action?.title ?? "Select action…"} ▾`;
  element("node-description").textContent =
    a.action?.description ??
    "Choose an action to find nodes, then continue from a match.";
  const revision = JSON.stringify([a.action?.revision, a.values]);
  if (revision !== actionRevision) {
    window.CtkArgumentCompletion.close();
    actionRevision = revision;
    element("node-arguments").replaceChildren();
    for (const arg of a.action?.arguments ?? []) {
      const input = document.createElement(
        arg.type === "boolean" ? "select" : "input",
      );
      input.dataset.argument = arg.name;
      if (arg.type === "boolean") {
        for (const value of ["true", "false"]) {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = `${arg.description}: ${value}`;
          input.append(option);
        }
      }
      input.placeholder = `${arg.description}${arg.default === undefined ? " (required)" : ""}`;
      input.setAttribute("aria-label", arg.description);
      input.title = arg.description;
      input.value =
        a.values[arg.name] ??
        (arg.default === undefined ? "" : String(arg.default));
      if (arg.type === "number") input.inputMode = "decimal";
      const field = document.createElement("div");
      field.className = "argument-field";
      field.append(input);
      element("node-arguments").append(field);
      if (arg.type === "string")
        new window.CtkArgumentCompletion(
          input,
          field,
          arg.name,
          a.action.revision,
          post,
        );
    }
    if (a.action?.arguments.some((arg) => arg.default === undefined))
      element("node-options").open = true;
    if (!a.action?.arguments.length)
      paragraph(
        element("node-arguments"),
        "This action needs no extra arguments.",
      );
  }
  for (const button of element("actions-panel").querySelectorAll(
    "button,input,select",
  ))
    button.disabled = a.running;
  element("node-run").disabled =
    a.running || a.stale || a.invalidAction || !a.action;
  element("node-edit").disabled = a.running || !a.action;
  element("node-back").hidden = !a.back;
  element("node-root").hidden = !a.root;
  element("node-error").textContent = a.error;
  element("node-count").textContent = a.completed
    ? `${a.matches} matches${a.truncated ? " · limit reached" : ""}`
    : "";
  for (const view of ["bindings", "files"])
    element(`${view}-view`).setAttribute(
      "aria-pressed",
      String(view === a.view),
    );
  const selected = a.results.find((r) => r.nodeId === a.selected);
  element("node-selection").hidden = !selected;
  element("node-selected").textContent = selected
    ? `${selected.binding}: ${selected.name}`
    : "";
  element("node-followup").disabled = a.running || a.stale || !selected;
  const key = JSON.stringify([a.results, a.view]);
  if (key !== resultRevision) {
    resultRevision = key;
    element("node-results").replaceChildren();
    const groups = new Map();
    for (const result of a.results) {
      if (a.view === "bindings") {
        if (!groups.has(result.binding))
          groups.set(
            result.binding,
            group(
              element("node-results"),
              `${result.binding} (${a.results.filter((r) => r.binding === result.binding).length})`,
              result.binding !== "root",
            ),
          );
        match(groups.get(result.binding), result, true);
      } else {
        if (!groups.has(result.file))
          groups.set(
            result.file,
            group(element("node-results"), result.displayFile),
          );
        const file = groups.get(result.file);
        let row = [...file.querySelectorAll("details")].find(
          (item) => item.dataset.match === result.matchId,
        );
        if (!row) {
          row = group(file, `Match · line ${result.line}`);
          row.dataset.match = result.matchId;
        }
        match(row, result, true);
      }
    }
    if (!a.results.length)
      paragraph(
        element("node-results"),
        a.completed
          ? "No matching nodes. Change the action or its arguments."
          : "Run an action on the file root, select a binding, then run another action.",
      );
  }
  for (const button of element("node-results").querySelectorAll(
    "[data-node]",
  )) {
    button.classList.toggle("selected", button.dataset.node === a.selected);
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.node === a.selected),
    );
    button.disabled = a.running;
  }
  post("nodeRendered", {
    view: a.view,
    action: element("node-picker").textContent,
    arguments: [...document.querySelectorAll("[data-argument]")].map(
      (input) => input.dataset.argument,
    ),
    values: nodeValues(),
    canRun: !element("node-run").disabled,
    nodes: element("node-results").querySelectorAll(".node-match").length,
    groups: element("node-results").querySelectorAll(":scope > details").length,
  });
}
function render(next) {
  state = next;
  for (const tab of ["symbols", "actions"]) {
    const active = state.tab === tab;
    element(`${tab}-panel`).hidden = !active;
    element(`${tab}-tab`).setAttribute("aria-selected", String(active));
    element(`${tab}-tab`).tabIndex = active ? 0 : -1;
  }
  renderSearch();
  renderActions();
}
window.addEventListener("message", ({ data }) => {
  if (data.type === "state") render(data.state);
  if (data.type === "nodeArgumentCompletions")
    window.CtkArgumentCompletion.receive(data);
});
post("ready");
