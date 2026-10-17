import { sectionState } from "./inspector-sections.js";
import { renderSemantics } from "./inspector-semantics.js";
import { renderTree } from "./inspector-tree.js";

const api = acquireVsCodeApi();
const el = (id) => document.getElementById(id);
const post = (type, data = {}) => api.postMessage({ type, ...data });
const restoreSections = sectionState(api, (group) => {
  if (group.id === "inspector-section") post("ready");
});
restoreSections(document.querySelector("main"));
const tabs = ["ast", "properties"];
for (const [index, tab] of tabs.entries()) {
  const button = el(`${tab}-tab`);
  button.addEventListener("click", () => post("tab", { tab }));
  button.addEventListener("keydown", (event) => {
    const next =
      event.key === "ArrowRight"
        ? tabs[(index + 1) % tabs.length]
        : event.key === "ArrowLeft"
          ? tabs[(index + tabs.length - 1) % tabs.length]
          : event.key === "Home"
            ? tabs[0]
            : event.key === "End"
              ? tabs.at(-1)
              : undefined;
    if (!next) return;
    event.preventDefault();
    el(`${next}-tab`).focus();
    post("tab", { tab: next });
  });
}
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
  const treeFocused = el("tree").contains(document.activeElement);
  for (const tab of tabs) {
    const selected = state.tab === tab;
    el(`${tab}-tab`).setAttribute("aria-selected", String(selected));
    el(`${tab}-tab`).tabIndex = selected ? 0 : -1;
    el(`${tab}-panel`).hidden = !selected;
  }
  if (state.tab === "properties" && treeFocused) el("properties-tab").focus();
  el("name").textContent = node.name;
  el("kind").textContent = node.kind;
  el("signature").textContent = node.signature;
  el("location").hidden = !node.locationValid;
  el("location").textContent = `${node.file}:${node.line}:${node.column}`;
  el("source").textContent = node.excerpt;
  el("source").hidden = !node.excerpt;
  el("source-section").hidden = !node.locationValid && !node.excerpt;
  el("back").disabled = !state.back || state.running;
  el("root").textContent = state.rootLabel;
  el("root").disabled = !state.back || state.running;
  el("location").disabled = state.running;
  el("action").disabled = !state.canRunAction;
  el("error").textContent = state.error;
  el("notice").textContent = state.notice;
  el("notice").hidden = !state.notice;
  el("retry").hidden = !state.error;
  el("retry").disabled = state.running;
  fields("properties", node.properties);
  el("properties-group").hidden = !node.properties.length;
  renderSemantics(el("semantics"), node, state.semantics, post, state);
  restoreSections(document.querySelector("main"));
  fields("range", node.range);
  el("range-group").hidden = !node.range.length;
  const tree = renderTree(el("tree"), state, post);
  post("rendered", {
    nodeId: node.id,
    kind: el("kind").textContent,
    properties: [...el("properties").querySelectorAll("dt")].map(
      (item) => item.textContent,
    ),
    children: state.tree
      .filter((row) => row.parent === node.id)
      .map((row) => row.id),
    tree,
    tab: state.tab,
    panels: {
      ast: !el("ast-panel").hidden,
      properties: !el("properties-panel").hidden,
    },
    sections: [...document.querySelectorAll("details[data-section]")].map(
      (group) => ({ title: group.dataset.section, open: group.open }),
    ),
    text: document.querySelector("main").innerText.slice(0, 100000),
  });
});
post("ready");
