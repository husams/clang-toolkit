const api = acquireVsCodeApi();
const el = (id) => document.getElementById(id);
const post = (type, data = {}) => api.postMessage({ type, ...data });
for (const [id, type] of [
  ["back", "back"],
  ["root", "root"],
  ["location", "source"],
  ["retry", "retry"],
  ["action", "action"],
])
  el(id).addEventListener("click", () => post(type));
function fields(id, values) {
  const list = el(id);
  list.replaceChildren();
  for (const field of values) {
    const label = document.createElement("dt"),
      value = document.createElement("dd");
    label.textContent = field.label;
    value.textContent = field.value;
    list.append(label, value);
  }
  if (!values.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No additional AST properties.";
    list.append(empty);
  }
}
window.addEventListener("message", ({ data }) => {
  if (data.type !== "state") return;
  const state = data.state,
    node = state.node;
  el("empty").hidden = Boolean(node);
  el("inspector").hidden = !node;
  if (!node) return;
  el("name").textContent = node.name;
  el("kind").textContent = node.kind;
  el("signature").textContent = node.signature;
  el("location").hidden = !node.locationValid;
  el("location").textContent = `${node.file}:${node.line}:${node.column}`;
  el("source").textContent = node.excerpt;
  el("source").hidden = !node.excerpt;
  el("back").disabled = !state.back || state.running;
  el("back").parentElement.hidden = !state.back;
  el("root").hidden = !state.back;
  el("root").textContent = state.rootLabel;
  el("root").disabled = state.running;
  el("location").disabled = state.running;
  el("action").disabled = !state.canRunAction;
  el("error").textContent = state.error;
  el("notice").textContent = state.notice;
  el("notice").hidden = !state.notice;
  el("retry").hidden = !state.error;
  el("retry").disabled = state.running;
  fields("properties", node.properties);
  fields("range", node.range);
  el("range-group").hidden = !node.range.length;
  el("loading").hidden = !state.running;
  el("no-children").hidden =
    state.running || state.children === undefined || state.children.length > 0;
  el("children").replaceChildren();
  for (const child of state.children ?? []) {
    const li = document.createElement("li"),
      button = document.createElement("button"),
      kind = document.createElement("span"),
      name = document.createElement("span");
    button.className = "child";
    button.dataset.node = child.id;
    button.setAttribute("aria-label", `Inspect ${child.kind}: ${child.name}`);
    kind.className = "child-kind";
    kind.textContent = child.kind;
    name.className = "muted";
    name.textContent = child.name === child.kind ? "" : child.name;
    button.title = child.locationValid
      ? `${child.file}:${child.line}:${child.column}`
      : child.kind;
    button.disabled = state.running;
    button.append(kind, name);
    button.addEventListener("click", () => post("child", { id: child.id }));
    li.append(button);
    el("children").append(li);
  }
  post("rendered", {
    kind: el("kind").textContent,
    properties: [...el("properties").querySelectorAll("dt")].map(
      (item) => item.textContent,
    ),
    children: [...el("children").querySelectorAll("button")].map(
      (item) => item.dataset.node,
    ),
    text: document.querySelector("main").innerText.slice(0, 100000),
  });
});
post("ready");
