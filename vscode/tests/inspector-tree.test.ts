import { describe, expect, it } from "vitest";
import {
  type AstEntry,
  type AstPage,
  astInspectionSchema,
} from "../src/ast-model.js";
import { InspectorTree } from "../src/inspector-tree.js";

const node = (id: string): AstEntry => ({
  id,
  name: id,
  kind: "Node",
  file: "/demo.cpp",
  line: 1,
  column: 1,
  excerpt: "",
  raw: {},
  locationValid: true,
});
const page = (id: string, children: string[]): AstPage => ({
  node: node(id),
  children: children.map(node),
});
describe("AST outline state", () => {
  it("distinguishes unloaded children from leaves and preserves cached branches when collapsed", () => {
    const tree = new InspectorTree();
    tree.apply(page("file", ["function", "sibling"]));
    expect(
      tree
        .rows()
        .map((row) => [row.node.id, row.depth, row.loaded, row.expandable]),
    ).toEqual([
      ["file", 0, true, true],
      ["function", 1, false, true],
      ["sibling", 1, false, true],
    ]);
    tree.apply(page("function", ["body"]), undefined, false);
    tree.expand("function", true);
    expect(tree.rows().find((row) => row.node.id === "body")?.parent).toBe(
      "function",
    );
    expect(tree.rows().find((row) => row.selected)?.node.id).toBe("file");
    tree.expand("function", false);
    expect(tree.rows().map((row) => row.node.id)).not.toContain("body");
    expect(tree.loaded("function")).toBe(true);
    tree.expand("function", true);
    tree.apply(page("body", []));
    expect(tree.rows().find((row) => row.node.id === "body")).toMatchObject({
      loaded: true,
      expandable: false,
      selected: true,
    });
    tree.clearSelection();
    expect(tree.rows().some((row) => row.selected)).toBe(false);
  });
  it("reveals cursor ancestors while preserving other expanded branches and exact native IDs", () => {
    const tree = new InspectorTree();
    tree.apply(page("file", ["first", "second"]));
    tree.apply(page("first", ["old-child"]));
    const path = [
      page("file", ["first", "second"]),
      page("second", ["body"]),
      page("body", ["literal"]),
      page("literal", []),
    ];
    tree.apply(path[3]!, path);
    expect(tree.rows().map((row) => row.node.id)).toEqual([
      "file",
      "first",
      "old-child",
      "second",
      "body",
      "literal",
    ]);
    expect(
      tree
        .rows()
        .filter((row) => row.selected)
        .map((row) => row.node.id),
    ).toEqual(["literal"]);
    tree.expand("second", false);
    tree.apply(path[3]!);
    expect(tree.rows().find((row) => row.node.id === "literal")?.selected).toBe(
      true,
    );
    tree.reset();
    expect(tree.rows()).toEqual([]);
  });
  it("rejects disconnected source paths at the worker boundary", () => {
    const selected = page("leaf", []);
    const result = {
      ...selected,
      parseCount: 1,
      root: { id: "root", file: "/demo.cpp", label: "File root" },
    };
    expect(
      astInspectionSchema.safeParse({
        ...result,
        path: [page("root", ["leaf"]), selected],
      }).success,
    ).toBe(true);
    expect(
      astInspectionSchema.safeParse({
        ...result,
        path: [page("root", ["other"]), selected],
      }).success,
    ).toBe(false);
    expect(
      astInspectionSchema.safeParse({ ...result, path: [page("other", [])] })
        .success,
    ).toBe(false);
  });
});
