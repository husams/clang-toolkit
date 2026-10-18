import { GraphView } from "./graph-view.js";

const api = acquireVsCodeApi();
const graph = new GraphView(document.getElementById("graph"), api, true);
window.addEventListener("message", ({ data }) => {
  if (data.type === "graph") graph.update({ model: data.model }, data.uiState);
});
api.postMessage({ type: "ready" });
