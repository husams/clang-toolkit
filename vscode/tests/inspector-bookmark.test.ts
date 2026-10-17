import { expect, it, vi } from "vitest";
import type { AstEntry } from "../src/ast-model.js";
import {
  type BookmarkPage,
  bookmarkTree,
  matchingNode,
  rebaseBookmark,
  rebuildTree,
} from "../src/inspector-bookmark.js";
import { InspectorTree } from "../src/inspector-tree.js";

const file = "/demo.cpp";
function node(
  id: string,
  kind: string,
  name = kind,
  symbol?: string,
  text = "",
  start?: number,
  end?: number,
): AstEntry {
  const point = (offset: number) => ({
    valid: true,
    file,
    line: 1,
    column: 1,
    offset: Buffer.byteLength(text.slice(0, offset)),
  });
  return {
    id,
    kind,
    name,
    file,
    line: 1,
    column: 1,
    excerpt: "",
    locationValid: true,
    raw: {
      binding: {
        ...(symbol ? { symbolIdentity: symbol } : {}),
        node: { [kind]: {} },
        ...(start !== undefined && end !== undefined
          ? {
              range: {
                expansionBegin: point(start),
                expansionEndExclusive: point(end),
              },
            }
          : {}),
      },
    },
  };
}
const page = (node: AstEntry, children: AstEntry[] = []): BookmarkPage => ({
  node,
  children,
});
function treeFor(pages: BookmarkPage[], selected: string) {
  const tree = new InspectorTree();
  for (const value of pages) tree.apply(value, undefined, false);
  tree.select(selected);
  return tree;
}
it("rebinds selected declarations and collapsed/expanded branches to fresh native IDs", async () => {
  const old = [
    node("root", "translationUnitDecl"),
    node("scope", "namespaceDecl", "demo", "ns"),
    node("class", "cxxRecordDecl", "demo::Order", "order"),
    node("method", "cxxMethodDecl", "demo::Order::run", "run"),
    node("other", "functionDecl", "other", "other"),
  ];
  const pages = [
    page(old[0]!, [old[1]!, old[4]!]),
    page(old[1]!, [old[2]!]),
    page(old[2]!, [old[3]!]),
    page(old[3]!),
    page(old[4]!),
  ];
  const tree = treeFor(pages, "method");
  for (const id of ["root", "scope", "method", "other"]) tree.expand(id, true);
  tree.expand("class", false);
  const bookmark = bookmarkTree(tree, "method", "", file)!;
  const fresh = old.map((item) => ({ ...item, id: `new-${item.id}` }));
  const loaded = new Map(
    [
      page(fresh[1]!, [fresh[2]!]),
      page(fresh[2]!, [fresh[3]!]),
      page(fresh[3]!),
      page(fresh[4]!),
    ].map((p) => [p.node.id, p]),
  );
  const load = vi.fn(async (id: string) => loaded.get(id)!);
  const result = await rebuildTree(
    bookmark,
    page(fresh[0]!, [fresh[1]!, fresh[4]!]),
    load,
    "",
    file,
    () => true,
  );
  expect(result?.selected.node.id).toBe("new-method");
  expect(
    result?.tree
      .rows(true)
      .map((row) => [row.node.id, row.expanded, row.selected]),
  ).toEqual([
    ["new-root", true, false],
    ["new-scope", true, false],
    ["new-class", false, false],
    ["new-method", true, true],
    ["new-other", true, false],
  ]);
  expect(load).toHaveBeenCalledTimes(4);
});
it("keeps the exact overload when sibling order changes", () => {
  const old = node("old", "functionDecl", "run", "run-double");
  const bookmark = bookmarkTree(treeFor([page(old)], "old"), "old", "", file)!;
  expect(
    matchingNode(
      bookmark,
      [
        node("integer", "functionDecl", "run", "run-int"),
        node("double", "functionDecl", "run", "run-double"),
      ],
      "",
      file,
    )?.id,
  ).toBe("double");
});
it("tracks a changed literal through UTF-16 edits and UTF-8 source ranges", async () => {
  const before = "// λ\nint f() { return 7; }\n",
    literal = before.indexOf("7");
  const oldRoot = node("root", "translationUnitDecl"),
    oldFunction = node("f", "functionDecl", "f", "f");
  const oldLiteral = node(
    "literal",
    "integerLiteral",
    undefined,
    undefined,
    before,
    literal,
    literal + 1,
  );
  const tree = treeFor(
    [
      page(oldRoot, [oldFunction]),
      page(oldFunction, [oldLiteral]),
      page(oldLiteral),
    ],
    "literal",
  );
  tree.expand("root", true);
  tree.expand("f", true);
  const bookmark = bookmarkTree(tree, "literal", before, file)!;
  rebaseBookmark(bookmark, [
    { rangeOffset: literal, rangeLength: 1, text: "99" },
    { rangeOffset: 0, rangeLength: 0, text: "// inserted\n" },
  ]);
  const after = "// inserted\n" + before.replace("7", "99"),
    start = after.indexOf("99");
  const freshRoot = node("new-root", "translationUnitDecl"),
    freshFunction = node("new-f", "functionDecl", "f", "f");
  const freshLiteral = node(
    "new-literal",
    "integerLiteral",
    undefined,
    undefined,
    after,
    start,
    start + 2,
  );
  const pages = new Map(
    [page(freshFunction, [freshLiteral]), page(freshLiteral)].map((p) => [
      p.node.id,
      p,
    ]),
  );
  const result = await rebuildTree(
    bookmark,
    page(freshRoot, [freshFunction]),
    async (id) => pages.get(id)!,
    after,
    file,
    () => true,
  );
  expect(result?.selected.node.id).toBe("new-literal");
});
it("selects the surviving parent when a deleted node's old position is occupied by another node", async () => {
  const text = "void gone();void keep();";
  const root = node("root", "translationUnitDecl"),
    scope = node("ns", "namespaceDecl", "demo", "ns");
  const gone = node("gone", "functionDecl", "gone", "gone", text, 0, 12),
    keep = node("keep", "functionDecl", "keep", "keep", text, 12, text.length);
  const tree = treeFor(
    [page(root, [scope]), page(scope, [gone, keep]), page(gone)],
    "gone",
  );
  tree.expand("root", true);
  tree.expand("ns", true);
  const bookmark = bookmarkTree(tree, "gone", text, file)!;
  rebaseBookmark(bookmark, [{ rangeOffset: 0, rangeLength: 12, text: "" }]);
  const freshRoot = node("fresh-root", "translationUnitDecl"),
    freshScope = node("fresh-ns", "namespaceDecl", "demo", "ns");
  const freshKeep = node(
    "fresh-keep",
    "functionDecl",
    "keep",
    "keep",
    text.slice(12),
    0,
    text.length - 12,
  );
  const load = vi.fn(async () => page(freshScope, [freshKeep]));
  const result = await rebuildTree(
    bookmark,
    page(freshRoot, [freshScope]),
    load,
    text.slice(12),
    file,
    () => true,
  );
  expect(result?.selected.node.id).toBe("fresh-ns");
  expect(load).toHaveBeenCalledOnce();
});
it("does not guess between indistinguishable declarations", () => {
  const old = node("old", "functionDecl", "f", "f");
  const bookmark = bookmarkTree(treeFor([page(old)], "old"), "old", "", file)!;
  expect(
    matchingNode(
      bookmark,
      [
        node("a", "functionDecl", "f", "f"),
        node("b", "functionDecl", "f", "f"),
      ],
      "",
      file,
    ),
  ).toBeUndefined();
});
it("reveals a saved action-result subtree inside the fresh file AST", async () => {
  const method = node("method", "cxxMethodDecl", "Order::run", "run");
  const bookmark = bookmarkTree(
    treeFor([page(method)], "method"),
    "method",
    "",
    file,
  )!;
  const root = node("root", "translationUnitDecl"),
    klass = node("class", "cxxRecordDecl", "Order", "order"),
    freshMethod = { ...method, id: "fresh-method" };
  const pages = new Map(
    [page(klass, [freshMethod]), page(freshMethod)].map((p) => [p.node.id, p]),
  );
  const result = await rebuildTree(
    bookmark,
    page(root, [klass]),
    async (id) => pages.get(id)!,
    "",
    file,
    () => true,
  );
  expect(result?.selected.node.id).toBe("fresh-method");
  expect(result?.tree.rows().map((row) => row.node.id)).toEqual([
    "root",
    "class",
    "fresh-method",
  ]);
});
it("abandons restoration when another edit or tab change supersedes it", async () => {
  const root = node("root", "translationUnitDecl"),
    fn = node("fn", "functionDecl", "f", "f");
  const tree = treeFor([page(root, [fn]), page(fn)], "fn");
  const bookmark = bookmarkTree(tree, "fn", "", file)!;
  let current = true;
  expect(
    await rebuildTree(
      bookmark,
      page(root, [fn]),
      async () => {
        current = false;
        return page(fn);
      },
      "",
      file,
      () => current,
    ),
  ).toBeUndefined();
});
it("recovers an undone deletion after other edits shift its source", () => {
  const old = node("old", "integerLiteral", undefined, undefined, "7", 0, 1);
  const bookmark = bookmarkTree(treeFor([page(old)], "old"), "old", "7", file)!;
  rebaseBookmark(bookmark, [{ rangeOffset: 0, rangeLength: 1, text: "" }]);
  rebaseBookmark(bookmark, [
    { rangeOffset: 0, rangeLength: 0, text: "// λ\n" },
  ]);
  rebaseBookmark(bookmark, [{ rangeOffset: 5, rangeLength: 0, text: "7" }]);
  const fresh = node(
    "fresh",
    "integerLiteral",
    undefined,
    undefined,
    "// λ\n7",
    5,
    6,
  );
  expect(matchingNode(bookmark, [fresh], "// λ\n7", file)?.id).toBe("fresh");
});
it("retains unchanged header statements without using the main file's text as their source", () => {
  const header = (id: string): AstEntry => ({
    ...node(id, "integerLiteral"),
    file: "/base.hpp",
    raw: {
      binding: {
        node: { integerLiteral: {} },
        range: {
          expansionBegin: {
            valid: true,
            file: "/base.hpp",
            line: 4,
            column: 8,
            offset: "42",
          },
          expansionEndExclusive: {
            valid: true,
            file: "/base.hpp",
            line: 4,
            column: 9,
            offset: "43",
          },
        },
      },
    },
  });
  const old = header("old"),
    fresh = header("fresh");
  const bookmark = bookmarkTree(
    treeFor([page(old)], "old"),
    "old",
    "// main file",
    file,
  )!;
  expect(
    matchingNode(bookmark, [fresh], "// changed main file", file)?.id,
  ).toBe("fresh");
});
it("preserves a unique structural node that has no source range", () => {
  const old = { ...node("old", "functionProtoTypeLoc"), locationValid: false };
  const bookmark = bookmarkTree(treeFor([page(old)], "old"), "old", "", file)!;
  expect(matchingNode(bookmark, [{ ...old, id: "fresh" }], "", file)?.id).toBe(
    "fresh",
  );
  expect(
    matchingNode(
      bookmark,
      [
        { ...old, id: "a" },
        { ...old, id: "b" },
      ],
      "",
      file,
    ),
  ).toBeUndefined();
});
