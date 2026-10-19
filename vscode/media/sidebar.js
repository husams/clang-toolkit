const api = acquireVsCodeApi();
const element = (id) => document.getElementById(id);
const post = (type, data = {}) => api.postMessage({ type, ...data });
let state;
let actionRevision;
let searchRevision;
let resultRevision;
let indexSearchTimer;
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
  if (
    state?.action.kind === "symbols" &&
    ["project", "global"].includes(element("scope").value)
  ) {
    post(type === "run" ? "indexRun" : "indexUpdate", {
      query: values("[data-parameter]", "parameter").NAME ?? "",
      scope: element("scope").value === "global" ? "global" : "project",
      project: element("index-project").value,
      kinds: [...document.querySelectorAll("#kinds input:checked")].map(
        (input) => input.value,
      ),
      exact: false,
    });
    return;
  }
  post(type, {
    values: values("[data-parameter]", "parameter"),
    scope: element("scope").value,
    kinds: [...document.querySelectorAll("#kinds input:checked")]
      .filter((input) => input.value !== "aliases")
      .map((input) => input.value),
    source: state?.source ?? "",
  });
}
function scheduleIndexedSearch() {
  clearTimeout(indexSearchTimer);
  indexSearchTimer = setTimeout(() => search("update"), 180);
}
element("index-cancel").addEventListener("click", () => post("indexCancel"));
element("symbols-panel").addEventListener("input", () => {
  if (state?.action.kind === "symbols") scheduleIndexedSearch();
  else search("update");
});
element("symbols-panel").addEventListener("change", (event) => {
  if (
    event.target.id === "scope" ||
    event.target.id === "index-project" ||
    event.target.closest("#kinds")
  )
    search("update");
});
element("symbols-panel").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.matches("input")) {
    event.preventDefault();
    clearTimeout(indexSearchTimer);
    search("run");
  }
});
element("run").addEventListener("click", () => search("run"));
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
element("node-scope").addEventListener("change", () =>
  post("nodeScope", { scope: element("node-scope").value }),
);
element("node-choose-directory").addEventListener("click", () =>
  post("nodeChooseDirectory"),
);
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
const resultToolbar = document.querySelector(".result-toolbar");
const pageInfo = document.createElement("span");
pageInfo.id = "node-page-info";
pageInfo.className = "muted";
pageInfo.setAttribute("role", "status");
pageInfo.setAttribute("aria-live", "polite");
const firstPage = document.createElement("button");
firstPage.id = "node-page-first";
firstPage.textContent = "First";
firstPage.addEventListener("click", () =>
  post("nodePage", { direction: "first" }),
);
const previousPage = document.createElement("button");
previousPage.id = "node-page-previous";
previousPage.textContent = "Previous";
previousPage.addEventListener("click", () =>
  post("nodePage", { direction: "previous" }),
);
const nextPage = document.createElement("button");
nextPage.id = "node-page-next";
nextPage.textContent = "Next";
nextPage.addEventListener("click", () =>
  post("nodePage", { direction: "next" }),
);
const lastPage = document.createElement("button");
lastPage.id = "node-page-last";
lastPage.textContent = "Last";
lastPage.addEventListener("click", () =>
  post("nodePage", { direction: "last" }),
);
const openCompleteResults = document.createElement("button");
openCompleteResults.id = "node-open-results";
openCompleteResults.textContent = "Open complete results";
openCompleteResults.addEventListener("click", () => post("nodeOpenResults"));
resultToolbar.append(
  pageInfo,
  firstPage,
  previousPage,
  nextPage,
  lastPage,
  openCompleteResults,
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
function match(parent, result, node = false, file = result.file) {
  const button = document.createElement("button");
  button.className = node ? "node-match match" : "match";
  if (node) {
    button.dataset.node = result.nodeId;
    button.dataset.binding = result.binding;
    button.classList.toggle(
      "selected",
      result.nodeId === state.actions.selected,
    );
    button.setAttribute(
      "aria-pressed",
      String(result.nodeId === state.actions.selected),
    );
  }
  button.title = `${node ? `${result.binding}: ${result.name}\n` : ""}${result.file}:${result.line}:${result.column}${node ? `\n${result.excerpt}` : ""}${result.detached ? "\nOpen this match to load its AST for inspection and actions." : ""}`;
  const name = document.createElement("span");
  name.className = "name";
  const location =
    result.file === file ? result.line : `${result.displayFile}:${result.line}`;
  name.textContent = `${node ? `${result.binding} · ` : ""}${result.name} · ${location}`;
  button.append(name);
  if (!node) {
    const excerpt = document.createElement("span");
    excerpt.className = "excerpt";
    excerpt.textContent = result.excerpt;
    button.append(excerpt);
  }
  button.addEventListener("click", () =>
    post(node ? "nodeSelect" : result.project ? "indexOpen" : "openResult", {
      id: node ? result.nodeId : result.id,
    }),
  );
  parent.append(button);
}
function renderSearch() {
  const indexed = state.action.kind === "symbols" && state.indexedSearchActive;
  const search = state.indexedSearch ?? {};
  const revision = JSON.stringify([
    state.action.id,
    state.action.parameters,
    indexed ? search.query : state.values,
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
      input.value =
        indexed && p.name === "NAME"
          ? (search.query ?? "")
          : (state.values[p.name] ?? p.default ?? "");
      element("fields").append(input);
    }
  }
  const scope = element("scope");
  for (const option of scope.options)
    option.hidden =
      state.action.kind === "symbols"
        ? false
        : !["file", "workspace"].includes(option.value);
  scope.value = indexed ? (search.scope ?? "project") : state.scope;
  element("index-project-label").hidden = !indexed || scope.value === "global";
  const projects = element("index-project");
  projects.replaceChildren();
  for (const item of search.projects ?? []) {
    const option = document.createElement("option");
    option.value = item.root;
    option.textContent = `${item.label} · ${item.root}`;
    projects.append(option);
  }
  projects.value = search.project ?? "";
  projects.disabled =
    !indexed || !(search.projects ?? []).length || scope.value === "global";
  element("target").textContent = indexed
    ? "Search indexed project symbols."
    : state.target || "Open a C++ file to search.";
  for (const input of document.querySelectorAll("#kinds input"))
    input.checked = indexed
      ? (search.kinds ?? []).includes(input.value)
      : input.value !== "aliases" && state.kinds.includes(input.value);
  const aliasKind = element("kinds").querySelector('input[value="aliases"]');
  aliasKind.parentElement.hidden = !indexed;
  for (const input of element("symbols-panel").querySelectorAll(
    "button,input,select",
  ))
    input.disabled = indexed
      ? search.running && input.tagName === "BUTTON"
      : state.running;
  element("index-cancel").hidden = !indexed || !search.running;
  element("index-cancel").disabled = false;
  element("status").textContent = indexed
    ? (search.status ?? "")
    : state.completed
      ? state.status
      : "";
  element("output").hidden =
    indexed || (!state.errors.length && !state.output.length);
  element("errors").replaceChildren();
  for (const error of indexed ? (search.errors ?? []) : state.errors)
    paragraph(element("errors"), error, "");
  const results = indexed ? (search.results ?? []) : state.results;
  const complete = indexed ? Boolean(search.completed) : state.completed;
  const resultKey = JSON.stringify([results, complete, indexed]);
  if (resultKey !== searchResults) {
    searchResults = resultKey;
    element("results").replaceChildren();
    const groups = new Map();
    for (const result of results) {
      const label =
        indexed && scope.value === "global"
          ? `${result.project} · ${result.displayFile}`
          : (result.displayFile ?? result.file);
      if (!groups.has(label))
        groups.set(label, group(element("results"), label));
      match(groups.get(label), result, false, result.file);
    }
    if (!results.length)
      paragraph(
        element("results"),
        complete
          ? "No matches."
          : indexed
            ? "Search indexed symbols by name."
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
  element("node-scope").value = a.scope ?? "file";
  element("node-directory").textContent = a.directoryTarget
    ? `Directory: ${a.directoryTarget}`
    : a.scope === "workspace"
      ? "All open workspace folders"
      : a.scope === "directory"
        ? "Choose a directory to scan"
        : "";
  element("node-choose-directory").hidden = a.scope !== "directory";
  element("node-context").textContent = a.input
    ? `Input: ${a.input.label} · ${a.input.file}`
    : a.scope === "workspace"
      ? "Input: all open workspace folders"
      : a.scope === "directory"
        ? `Input: directory · ${a.directoryTarget ?? "choose a folder"}`
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
  const resultQualifier = a.batch
    ? a.complete
      ? ""
      : ` · partial${a.cancelled ? " · cancelled" : ""}`
    : a.truncated
      ? " · limit reached"
      : "";
  element("node-count").textContent = a.completed
    ? `${a.totalMatches} ${a.totalMatches === 1 ? "match" : "matches"}${resultQualifier}`
    : "";
  const pageSize = a.pageSize ?? 0;
  const pageOffset = a.pageOffset ?? 0;
  const pageCount =
    pageSize > 0 ? Math.max(1, Math.ceil(a.totalMatches / pageSize)) : 0;
  const pageNumber = pageSize > 0 ? Math.floor(pageOffset / pageSize) + 1 : 0;
  const pageGroups = a.matchFiles.reduce(
    (count, file) => count + file.matches.length,
    0,
  );
  pageInfo.textContent = a.completed
    ? `Page ${pageNumber || 1}${pageCount ? ` of ${pageCount}` : ""} · ${pageGroups} matches · ${a.results.length} binding rows`
    : "";
  firstPage.hidden = !a.resultHandle;
  firstPage.disabled = a.running || pageOffset <= 0;
  previousPage.hidden = !a.resultHandle;
  previousPage.disabled = a.running || pageOffset <= 0;
  nextPage.hidden = !a.resultHandle;
  nextPage.disabled = a.running || !a.hasMore;
  lastPage.hidden = !a.resultHandle;
  lastPage.disabled = a.running || !a.hasMore;
  openCompleteResults.hidden = !a.resultFile;
  openCompleteResults.disabled = a.running;
  const cancelledFiles = (a.fileStatuses ?? []).filter(
    (file) => file.status === "cancelled",
  ).length;
  element("node-batch-summary").textContent = a.batch
    ? `${a.scope === "directory" ? "Directory" : "Workspace"} batch · ${a.completedFiles ?? Math.max(0, a.files - a.errors.length)} succeeded · ${a.failedFiles ?? a.errors.length} failed · ${cancelledFiles} cancelled · ${a.unattemptedFiles ?? 0} not attempted · ${a.coverageComplete ? "all files attempted" : "coverage incomplete"}`
    : "";
  element("node-batch-errors").replaceChildren();
  for (const error of a.errors ?? [])
    paragraph(
      element("node-batch-errors"),
      `${error.file}: ${error.message}`,
      "",
    );
  const selected = a.results.find((r) => r.nodeId === a.selected);
  element("node-selection").hidden = !selected;
  element("node-selected").textContent = selected
    ? `${selected.binding}: ${selected.name}`
    : "";
  element("node-followup").disabled = a.running || a.stale || !selected;
  const key = JSON.stringify(a.results);
  if (key !== resultRevision) {
    resultRevision = key;
    element("node-results").replaceChildren();
    for (const file of a.matchFiles) {
      const parent = group(
        element("node-results"),
        `${file.matches[0].anchor.displayFile} (${file.matches.length})`,
      );
      parent.dataset.file = file.file;
      for (const [index, row] of file.matches.entries()) {
        const details = group(
          parent,
          `Match [${index + 1}] · line ${row.anchor.line}`,
          false,
        );
        details.className = "action-match";
        details.dataset.match = row.id;
        const bindings = document.createElement("div");
        bindings.className = "match-bindings";
        bindings.setAttribute("role", "group");
        bindings.setAttribute("aria-label", `Bindings for match ${index + 1}`);
        details.append(bindings);
        for (const result of row.bindings)
          match(bindings, result, true, file.file);
        details.addEventListener("toggle", reportActionRendering);
      }
      parent.addEventListener("toggle", reportActionRendering);
    }
    if (!a.results.length)
      paragraph(
        element("node-results"),
        a.completed
          ? "No matching nodes. Change the action or its arguments."
          : "Choose an action, adjust Options, then Run.",
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
  reportActionRendering();
}
function reportActionRendering() {
  post("nodeRendered", {
    action: element("node-picker").textContent,
    arguments: [...document.querySelectorAll("[data-argument]")].map(
      (input) => input.dataset.argument,
    ),
    values: nodeValues(),
    canRun: !element("node-run").disabled,
    nodes: element("node-results").querySelectorAll(".node-match").length,
    groups: element("node-results").querySelectorAll(":scope > details").length,
    rows: [...element("node-results").querySelectorAll("[data-match]")].map(
      (row) => ({
        id: row.dataset.match,
        file: row.parentElement.dataset.file,
        expanded: row.open,
        bindings: [...row.querySelectorAll("[data-node]")].map(
          (button) => button.dataset.binding,
        ),
        nodeIds: [...row.querySelectorAll("[data-node]")].map(
          (button) => button.dataset.node,
        ),
      }),
    ),
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
post("indexProjects");
