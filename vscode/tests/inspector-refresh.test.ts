import { expect, it, vi } from "vitest";
import type * as vscode from "vscode";
import { DetailsView, type InspectorState } from "../src/details-view.js";
import { InspectorTree } from "../src/inspector-tree.js";

vi.mock("vscode", () => ({
  StatusBarAlignment: { Left: 1 },
  window: {
    createStatusBarItem: () => ({
      text: "",
      show: vi.fn(),
      hide: vi.fn(),
      dispose: vi.fn(),
    }),
  },
  workspace: { asRelativePath: (file: string) => file },
}));

function state(id: string): InspectorState {
  const node = {
    id,
    name: id,
    kind: "CXXRecordDecl",
    file: "/example.cpp",
    line: 1,
    column: 1,
    excerpt: "struct Example {};",
    raw: {},
  };
  const page = { node, nativeId: id, children: [] };
  const tree = new InspectorTree();
  tree.apply(page);
  return {
    current: page,
    history: [],
    cache: new Map([[id, page]]),
    tree,
    load: vi.fn(),
    prepareAction: vi.fn(),
    contextId: id,
    rootLabel: "File AST",
    tab: "properties",
    error: "",
    notice: "",
    operation: undefined,
  };
}
function view() {
  return new DetailsView({} as vscode.Uri, vi.fn(), vi.fn());
}
function pendingFailure() {
  let reject: (error: Error) => void = () => {};
  const promise = new Promise<InspectorState>((_resolve, decline) => {
    reject = decline;
  });
  return { promise, reject };
}
it("keeps valid facts throughout a failed replacement and enables fresh handles after a retry", async () => {
  const details = view(),
    previous = state("valid");
  await details.restore(previous, () => true);
  const before = details.snapshot();
  const pending = pendingFailure();
  const refresh = details.refreshFile(
    previous.current!.node,
    previous,
    () => pending.promise,
    () => true,
  );
  expect(details.snapshot()).toMatchObject({
    node: before.node,
    tree: before.tree,
    running: true,
    canRunAction: false,
  });
  pending.reject(new Error("Clang reported errors while parsing example.cpp"));
  await expect(refresh).rejects.toThrow("Clang reported errors");
  details.setRefreshError("/example.cpp", details.snapshot().error, true);
  expect(details.snapshot()).toMatchObject({
    node: before.node,
    tree: before.tree,
    tab: "properties",
    contextId: "valid",
    running: false,
    canRunAction: false,
    inspectionStatus: { text: "$(warning) CTK · AST refresh failed" },
  });
  await details.receive({ type: "child", id: "valid" });
  await details.selectSource({ file: "/example.cpp", start: 0, end: 0 });
  expect(previous.load).not.toHaveBeenCalled();
  await expect(details.actionTarget()).rejects.toThrow("current AST node");
  const fresh = state("fresh");
  await details.refreshFile(
    previous.current!.node,
    previous,
    async () => fresh,
    () => true,
  );
  details.setRefreshError("/example.cpp");
  expect(details.snapshot()).toMatchObject({
    node: { id: "fresh" },
    contextId: "fresh",
    tab: "properties",
    error: "",
    canRunAction: true,
    inspectionStatus: { text: "" },
  });
  details.dispose();
});
it("discards a late parse failure after switching the inspector to another file", async () => {
  const details = view(),
    previous = state("first"),
    second = state("second"),
    pending = pendingFailure();
  const refresh = details.refreshFile(
    previous.current!.node,
    previous,
    () => pending.promise,
    () => true,
  );
  await details.restore(second, () => true);
  pending.reject(new Error("Late failure"));
  expect(await refresh).toBeUndefined();
  expect(details.snapshot()).toMatchObject({
    node: { id: "second" },
    contextId: "second",
    running: false,
    error: "",
    canRunAction: true,
  });
  details.dispose();
});
it("clears a stale parse warning on edit without restoring invalid native handles", async () => {
  const details = view(),
    previous = state("valid");
  await expect(
    details.refreshFile(
      previous.current!.node,
      previous,
      async () => {
        throw new Error("Old saved-file failure");
      },
      () => true,
    ),
  ).rejects.toThrow("Old saved-file failure");
  details.setRefreshError("/example.cpp", "Old saved-file failure", true);
  details.setRefreshError("/example.cpp");
  expect(details.snapshot()).toMatchObject({
    error: "",
    node: { id: "valid" },
    canRunAction: false,
    inspectionStatus: { text: "", tooltip: undefined },
  });
  await expect(details.actionTarget()).rejects.toThrow("current AST node");
  details.setRefreshError("/other.cpp", "Another file's error", true);
  details.setRefreshError("/example.cpp");
  expect(String(details.snapshot().inspectionStatus.tooltip)).toContain(
    "Another file's error",
  );
  details.dispose();
});
it("tracks background errors independently and clears each when its file recovers or closes", async () => {
  const details = view();
  await details.restore(state("current"), () => true);
  details.setRefreshError("/other.cpp", "First parse failure", true);
  details.setRefreshError("/last.cpp", "Second parse failure", false);
  expect(String(details.snapshot().inspectionStatus.tooltip)).toContain(
    "/last.cpp",
  );
  expect(details.snapshot().canRunAction).toBe(true);
  details.setRefreshError("/last.cpp");
  expect(String(details.snapshot().inspectionStatus.tooltip)).toContain(
    "First parse failure",
  );
  details.setRefreshError("/other.cpp");
  expect(details.snapshot().inspectionStatus.text).toBe("");
  details.dispose();
});
it("refreshes a base link into a fresh buffer context even when the previous native loader is gone", async () => {
  const previous = state("old-type"),
    fresh = state("fresh-type");
  previous.current!.semantics = {
    referencedDeclaration: {
      name: "demo::Base",
      symbol: "base-usr",
      nodeId: "old-base",
    },
  };
  previous.load = undefined;
  previous.prepareAction = undefined;
  previous.error = "Source or settings changed";
  const base = { ...fresh.current!.node, id: "fresh-base", name: "demo::Base" };
  fresh.load = vi.fn(async () => ({
    node: { ...base, locationValid: true },
    children: [],
    parseCount: 1,
    root: { id: "root", file: "/example.cpp", label: "File root" },
  }));
  const open = vi.fn(),
    refresh = vi.fn(async () => {
      await details.restore(fresh, () => true);
      return "fresh-base";
    });
  const details = new DetailsView({} as vscode.Uri, open, vi.fn(), refresh);
  await details.restore(previous, () => true);
  await details.receive({ type: "related", id: "old-base" });
  expect(refresh).toHaveBeenCalledExactlyOnceWith({
    name: "demo::Base",
    symbol: "base-usr",
  });
  expect(details.snapshot()).toMatchObject({
    node: { id: "fresh-base" },
    error: "",
    contextId: "fresh-type",
  });
  expect(open).toHaveBeenCalledExactlyOnceWith(
    expect.objectContaining({ id: "fresh-base" }),
  );
  details.dispose();
});

it("restores a saved graph presentation without reviving native AST handles", async () => {
  const details = view(),
    previous = state("old-native-session");
  await details.restore(previous, () => true);
  const model = {
      key: "saved-native-graph",
      kind: "callgraph" as const,
      root: "submit",
      name: "submit",
      complete: true,
      warnings: [],
      nodes: [
        {
          id: "submit",
          name: "submit",
          file: "/orders.cpp",
          line: 10,
          column: 1,
          detail: "int submit()",
        },
      ],
      edges: [],
    },
    uiState = JSON.stringify({
      trail: [model.root],
      expanded: { out: [model.root], in: [] },
      view: { scale: 0.4, ax: 0.25, ay: 0.5 },
    });
  details.showSavedGraph(model, uiState);
  expect(details.snapshot()).toMatchObject({
    tab: "callgraph",
    canRunAction: false,
    node: { name: "submit" },
    graph: { model, uiState },
  });
  expect(previous.load).not.toHaveBeenCalled();
  await expect(details.actionTarget()).rejects.toThrow();
});
