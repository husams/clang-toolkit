import { expect, it } from "vitest";
import { graphSchema } from "../src/graph-model.js";

it("rejects dangling edges, duplicate identities, and missing graph roots", () => {
  const graph = {
    key: "native",
    kind: "callgraph",
    root: "1",
    name: "submit",
    complete: true,
    warnings: [],
    nodes: [{ id: "1", name: "submit", file: "demo.cpp", line: 1, column: 1 }],
    edges: [],
  };
  expect(graphSchema.parse(graph).root).toBe("1");
  expect(() => graphSchema.parse({ ...graph, root: "2" })).toThrow();
  expect(() =>
    graphSchema.parse({ ...graph, nodes: [...graph.nodes, ...graph.nodes] }),
  ).toThrow();
  expect(() =>
    graphSchema.parse({
      ...graph,
      edges: [{ id: "edge", from: "1", to: "2" }],
    }),
  ).toThrow();
});
