const api = acquireVsCodeApi();
const element = (id) => document.getElementById(id);
let state;
function values() {
  return Object.fromEntries(
    [...document.querySelectorAll("[data-parameter]")].map((input) => [
      input.dataset.parameter,
      input.value,
    ]),
  );
}
element("action").addEventListener("click", () =>
  api.postMessage({ type: "chooseAction" }),
);
function update(type) {
  api.postMessage({
    type,
    values: values(),
    scope: element("scope").value,
    kinds: [...document.querySelectorAll("#kinds input:checked")].map(
      (input) => input.value,
    ),
    source: element("source").value,
  });
}
element("run").addEventListener("click", () => update("run"));
document.addEventListener("input", (event) => {
  if (event.target.matches("input, select, textarea")) update("update");
});
element("stop").addEventListener("click", () =>
  api.postMessage({ type: "stop" }),
);
element("output").addEventListener("click", () =>
  api.postMessage({ type: "showOutput" }),
);
element("edit").addEventListener("click", () =>
  api.postMessage({ type: "editBlock", source: element("source").value }),
);
function render(next) {
  state = next;
  element("action").textContent = `${state.action.title} ▾`;
  element("scope").value = state.scope;
  element("target").textContent =
    state.target || "Select a C++ file or use Workspace scope.";
  element("fields").replaceChildren();
  for (const p of state.action.parameters) {
    const label = document.createElement("label");
    label.htmlFor = `parameter-${p.name}`;
    label.textContent = `${p.label}${p.required ? " (required)" : ""}`;
    const input = document.createElement(
      p.kind === "choice" ? "select" : "input",
    );
    input.id = label.htmlFor;
    input.dataset.parameter = p.name;
    if (p.kind === "choice")
      for (const value of p.choices) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        input.append(option);
      }
    input.value = state.values[p.name] ?? p.default ?? "";
    element("fields").append(label, input);
  }
  element("block").hidden = state.action.id !== "custom";
  element("source").value = state.source;
  element("kinds").hidden = state.action.kind !== "symbols";
  for (const input of document.querySelectorAll("#kinds input"))
    input.checked = state.kinds.includes(input.value);
  for (const input of document.querySelectorAll(
    "button, input, textarea, select",
  ))
    input.disabled = state.running && input.id !== "stop";
  element("stop").hidden = !state.running;
  element("status").textContent = state.status;
  element("output").hidden = !(
    state.errors.length ||
    (state.completed && state.action.kind === "script")
  );
  element("errors").replaceChildren();
  for (const error of state.errors) {
    const p = document.createElement("p");
    p.textContent = error;
    element("errors").append(p);
  }
  element("results").replaceChildren();
  const groups = new Map();
  for (const result of state.results) {
    if (!groups.has(result.file)) {
      const details = document.createElement("details");
      details.open = true;
      const summary = document.createElement("summary");
      summary.textContent = result.displayFile;
      details.append(summary);
      groups.set(result.file, details);
      element("results").append(details);
    }
    const button = document.createElement("button");
    button.className = "match";
    button.title = `${result.file}:${result.line}:${result.column}`;
    const name = document.createElement("span");
    name.className = "name";
    const kind = document.createElement("span");
    kind.className = "kind";
    kind.textContent = `${result.kind} · `;
    name.append(
      kind,
      document.createTextNode(`${result.name} · line ${result.line}`),
    );
    const excerpt = document.createElement("span");
    excerpt.className = "excerpt";
    excerpt.textContent = result.excerpt;
    button.append(name, excerpt);
    button.addEventListener("click", () => {
      for (const item of document.querySelectorAll(".match"))
        item.classList.remove("selected");
      button.classList.add("selected");
      api.postMessage({ type: "openResult", id: result.id });
    });
    groups.get(result.file).append(button);
  }
  if (!state.results.length) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = state.completed
      ? "No matching declarations. Adjust the analysis inputs or scope."
      : "Run an analysis to see matching C++ declarations.";
    element("results").append(p);
  }
  api.postMessage({
    type: "rendered",
    action: state.action.id,
    matches: document.querySelectorAll(".match").length,
    groups: groups.size,
  });
}
window.addEventListener("message", ({ data }) => {
  if (data.type === "state") render(data.state);
  if (data.type === "progress") element("status").textContent = data.text;
});
api.postMessage({ type: "ready" });
