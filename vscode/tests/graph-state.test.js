import { describe, expect, it } from "vitest";
import { GraphState } from "../media/graph-state.js";

const model = (size = 4) => ({
  key: "fixture",
  kind: "callgraph",
  root: "0",
  name: "submit",
  nodes: Array.from({ length: size }, (_, i) => ({
    id: String(i),
    name: i ? `function_${i}` : "submit",
  })),
  edges: Array.from({ length: size - 1 }, (_, i) => ({
    id: String(i),
    from: String(Math.floor(i / 3)),
    to: String(i + 1),
  })),
});
const camera = { scale: 0.24, ax: 0.12, ay: 0.72 };
describe("graph exploration state", () => {
  it("keeps every opened branch while breadcrumb navigation restores each camera", () => {
    const s = new GraphState(model(302));
    s.expandAll();
    expect(s.visible().nodes).toHaveLength(302);
    s.visit("1", camera);
    s.visit("4", { ...camera, scale: 0.8 });
    s.visit("13", { ...camera, scale: 1.2 });
    const opened = s.snapshot().expanded;
    expect(s.visit("1", { ...camera, scale: 2 })).toEqual({
      ...camera,
      scale: 0.8,
    });
    expect(s.trail).toEqual(["0", "1"]);
    expect(s.visit("0", camera)).toEqual(camera);
    expect(s.snapshot().expanded).toEqual(opened);
    expect(s.visible().nodes).toHaveLength(302);
  });
  it("retains nested expansion when a branch is collapsed then reopened", () => {
    const s = new GraphState(model(302));
    s.expandAll();
    s.toggle("1");
    expect(s.visible().nodes.length).toBeLessThan(302);
    s.toggle("1");
    expect(s.visible().nodes).toHaveLength(302);
  });
  it("search reveals a hidden path without closing other branches", () => {
    const s = new GraphState(model(302));
    s.toggle("2");
    const previous = s.snapshot().expanded.out;
    expect(s.reveal("100")).toBe(true);
    expect(s.paths().has("100")).toBe(true);
    for (const id of previous) expect(s.expanded.out.has(id)).toBe(true);
  });
  it("handles shared callees, recursion, and thousands of nodes without a display cap", () => {
    const graph = model(3001);
    graph.edges.push(
      { id: "shared", from: "2", to: "4" },
      { id: "recursive", from: "4", to: "0" },
    );
    const s = new GraphState(graph);
    s.expandAll();
    expect(s.visible().nodes).toHaveLength(3001);
    expect(s.visible().edges).toHaveLength(3002);
    expect(s.visible().nodes.filter((n) => n.id === "4")).toHaveLength(1);
  });
  it("restores saved cameras and expansions and rejects invalid camera values", () => {
    const graph = model(302),
      s = new GraphState(graph);
    s.expandAll();
    s.visit("1", camera);
    s.visit("4", camera);
    const saved = JSON.parse(JSON.stringify(s.snapshot(camera)));
    saved.cameras["out:4"] = { scale: "bad", ax: 0, ay: 0 };
    const restored = new GraphState(graph, saved);
    expect(restored.visible().nodes).toHaveLength(302);
    expect(restored.trail).toEqual(["0", "1", "4"]);
    expect(restored.cameras["out:4"]).toBeUndefined();
    expect(restored.visit("0", camera)).toEqual(camera);
  });
  it("defaults to downstream calls and keeps caller expansion separate", () => {
    const graph = model(8);
    graph.edges.push({ id: "caller", from: "7", to: "0" });
    const s = new GraphState(graph);
    expect(s.visible().nodes.map((n) => n.id)).toEqual(["0", "1", "2", "3"]);
    s.direction = "in";
    expect(s.visible().nodes.map((n) => n.id)).toEqual(["0", "7"]);
  });
});
