import { beforeEach, expect, it, vi } from "vitest";
import { PinnedQueries } from "../src/pinned-queries.js";

const mock = vi.hoisted(() => ({
  text: "int target;",
  panels: [],
  columns: [],
  serializer: undefined,
}));
vi.mock("node:fs/promises", () => ({
  realpath: async (file) => file,
  readFile: async () => mock.text,
}));
vi.mock("vscode", () => ({
  Uri: {
    joinPath: (uri, ...parts) => ({
      fsPath: [uri.fsPath, ...parts].join("/"),
    }),
  },
  ViewColumn: { Beside: 2 },
  workspace: { textDocuments: [], asRelativePath: (file) => file },
  window: {
    registerWebviewPanelSerializer: (_id, serializer) => {
      mock.serializer = serializer;
      return { dispose() {} };
    },
    showInformationMessage: vi.fn(),
    showWarningMessage: vi.fn(),
    createWebviewPanel: (_kind, _title, column) => {
      mock.columns.push(column);
      const panel = {
        viewColumn: 7,
        dispose: vi.fn(),
        onDidDispose: vi.fn(),
        webview: {
          asWebviewUri: (uri) => uri.fsPath,
          postMessage: vi.fn(),
          onDidReceiveMessage: (callback) => {
            panel.receive = callback;
            return { dispose() {} };
          },
        },
      };
      mock.panels.push(panel);
      return panel;
    },
  },
}));
const result = {
  id: "target",
  nodeId: "expired-handle",
  name: "target",
  kind: "VarDecl",
  file: "/source.cpp",
  line: 1,
  column: 1,
  excerpt: "int target;",
  raw: {},
};
beforeEach(() => {
  mock.text = "int target;";
  mock.panels = [];
  mock.columns = [];
  vi.clearAllMocks();
});

it("keeps each pinned query independent and navigable after another query is pinned", async () => {
  const reveal = vi.fn(),
    pins = new PinnedQueries({ fsPath: "/extension" }, reveal);
  await pins.pin("First query", "varDecl()", [result]);
  await pins.pin("Second query", "functionDecl()", [
    { ...result, id: "second", name: "other" },
  ]);
  await mock.panels[0].receive({ type: "ready" });
  const snapshot = mock.panels[0].webview.postMessage.mock.calls[0][0].snapshot;
  expect(snapshot.title).toBe("First query");
  expect(snapshot.results[0].nodeId).toBeUndefined();
  await mock.panels[0].receive({ type: "open", index: 0 });
  expect(reveal).toHaveBeenCalledWith(
    expect.objectContaining({ name: "target" }),
    "int target;",
  );
  expect(mock.panels[1].title).toBe("Second query");
  expect(mock.columns).toEqual([2, 7]);
  pins.dispose();
});

it("refuses stale source navigation and invalid indices without using expired AST handles", async () => {
  const reveal = vi.fn(),
    pins = new PinnedQueries({ fsPath: "/extension" }, reveal);
  await pins.pin("Query", "varDecl()", [result]);
  mock.text = "int changed;";
  await mock.panels[0].receive({ type: "open", index: 0 });
  await mock.panels[0].receive({ type: "open", index: -1 });
  expect(reveal).not.toHaveBeenCalled();
  pins.dispose();
});

it("rejects malformed serialized tabs on reload", async () => {
  const pins = new PinnedQueries({ fsPath: "/extension" }, vi.fn());
  const panel = { dispose: vi.fn() };
  await mock.serializer.deserializeWebviewPanel(panel, { results: "invalid" });
  expect(panel.dispose).toHaveBeenCalledOnce();
  pins.dispose();
});

it("does not archive stale results against a new source fingerprint", async () => {
  const pins = new PinnedQueries({ fsPath: "/extension" }, vi.fn());
  await pins.pin("Stale query", "varDecl()", [result], () => false);
  expect(mock.panels).toHaveLength(0);
  pins.dispose();
});

it("passes selection, expansion and scroll through the serializer on reload", async () => {
  const pins = new PinnedQueries({ fsPath: "/extension" }, vi.fn());
  await pins.pin("Query", "varDecl()", [result]);
  const panel = mock.panels[0];
  await panel.receive({ type: "ready" });
  const snapshot = {
    ...panel.webview.postMessage.mock.calls[0][0].snapshot,
    selected: 0,
    scroll: 240,
    expanded: ["/source.cpp"],
    queryExpanded: true,
  };
  await mock.serializer.deserializeWebviewPanel(panel, snapshot);
  await panel.receive({ type: "ready" });
  expect(panel.webview.postMessage.mock.calls.at(-1)[0].snapshot).toMatchObject(
    {
      selected: 0,
      scroll: 240,
      expanded: ["/source.cpp"],
      queryExpanded: true,
    },
  );
  pins.dispose();
});
