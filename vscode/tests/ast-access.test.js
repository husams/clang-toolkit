import { beforeEach, expect, it, vi } from "vitest";
import * as vscode from "vscode";
import { SearchAstAccess } from "../src/ast-access.js";

const mock = vi.hoisted(() => ({
  services: [],
  changed: undefined,
  resolve: undefined,
  disk: undefined,
  nextSearch: undefined,
}));
vi.mock("node:fs/promises", () => ({
  realpath: (file) =>
    file.startsWith("/alias/")
      ? new Promise((resolve) => {
          mock.resolve = resolve;
        })
      : Promise.resolve(file),
}));
vi.mock("../src/console-service.js", () => ({
  findPython: async () => "python",
}));
vi.mock("../src/action-service.js", () => ({
  ActionService: class {
    constructor() {
      this.dispose = vi.fn();
      this.inspect = vi.fn(async () => ({
        root: { id: "root", file: "/real/source.cpp", label: "File root" },
      }));
      this.search = mock.nextSearch ?? vi.fn(async () => searchReport);
      this.cancel = vi.fn();
      mock.services.push(this);
    }
  },
}));
vi.mock("vscode", () => ({
  Uri: {
    file: (file) => ({ fsPath: file }),
    joinPath: (base, ...parts) => ({
      fsPath: [base.fsPath, ...parts].join("/"),
    }),
  },
  workspace: {
    isTrusted: true,
    textDocuments: [],
    createFileSystemWatcher: () => ({
      dispose: vi.fn(),
      onDidChange: (listener) => {
        mock.disk = listener;
        return { dispose() {} };
      },
      onDidCreate: () => ({ dispose() {} }),
      onDidDelete: () => ({ dispose() {} }),
    }),
    onDidChangeTextDocument: (listener) => {
      mock.changed = listener;
      return { dispose() {} };
    },
    onDidChangeConfiguration: () => ({ dispose() {} }),
    getWorkspaceFolder: () => ({ uri: { fsPath: "/real" } }),
    getConfiguration: () => ({ get: (_key, fallback) => fallback }),
  },
}));

beforeEach(() => {
  mock.services = [];
  mock.changed = undefined;
  mock.resolve = undefined;
  mock.disk = undefined;
  mock.nextSearch = undefined;
  vscode.workspace.textDocuments.length = 0;
});

const searchReport = {
  results: [
    {
      id: "found",
      nodeId: "matched-native-node",
      translationUnit: "/real/source.cpp",
      name: "Order",
    },
  ],
  errors: [],
  output: [],
  files: 1,
  truncated: false,
};
const searchRequest = {
  action: {
    id: "classes",
    title: "Classes",
    description: "Find classes",
    kind: "symbols",
    parameters: [],
  },
  values: {},
  kinds: ["classes"],
  files: ["/real/source.cpp"],
  directory: "/real",
  compileArguments: [],
  timeoutMs: 30000,
  maxResults: 10,
};

it("inspects multiple search selections with their retained node IDs in the original worker", async () => {
  const access = new SearchAstAccess({ fsPath: "/extension" });
  await access.search(searchRequest, "python").completion;
  const result = searchReport.results[0];
  const first = access.matched(result);
  await first.inspect();
  await access.matched(result).inspect();
  expect(mock.services).toHaveLength(1);
  expect(mock.services[0].inspect).toHaveBeenCalledWith(
    expect.any(Object),
    "matched-native-node",
  );
  expect(first.session().service).toBe(mock.services[0]);
  expect(mock.services[0].dispose).not.toHaveBeenCalled();
  access.dispose();
});

it("preserves old search ownership after failure and releases it only after a successful replacement", async () => {
  const access = new SearchAstAccess({ fsPath: "/extension" });
  await access.search(searchRequest, "python").completion;
  const old = access.matched(searchReport.results[0]);
  mock.nextSearch = vi.fn().mockRejectedValue(new Error("Search cancelled"));
  await expect(
    access.search(searchRequest, "python").completion,
  ).rejects.toThrow("Search cancelled");
  expect(mock.services[0].dispose).not.toHaveBeenCalled();
  await old.inspect();
  mock.nextSearch = undefined;
  await access.search(searchRequest, "python").completion;
  expect(mock.services[0].dispose).toHaveBeenCalledOnce();
  await expect(old.inspect()).rejects.toThrow(/changed|expired/);
  access.dispose();
});

it("invalidates retained search results on edits instead of locating a replacement node", async () => {
  const access = new SearchAstAccess({ fsPath: "/extension" });
  await access.search(searchRequest, "python").completion;
  const selected = access.matched(searchReport.results[0]);
  mock.changed({
    document: { uri: { fsPath: "/real/source.cpp" } },
    contentChanges: [{ text: "changed" }],
  });
  expect(mock.services[0].dispose).toHaveBeenCalledOnce();
  await expect(selected.inspect()).rejects.toThrow(/changed|expired/);
  expect(mock.services[0].inspect).not.toHaveBeenCalled();
  access.dispose();
});

it("transfers a search worker to Actions without closing it when search is reset", async () => {
  const access = new SearchAstAccess({ fsPath: "/extension" });
  await access.search(searchRequest, "python").completion;
  const selected = access.matched(searchReport.results[0]);
  await selected.inspect();
  selected.transfer();
  access.close();
  expect(mock.services[0].dispose).not.toHaveBeenCalled();
  access.dispose();
});

it("does not close retained matches when their editor tab is closed", async () => {
  const access = new SearchAstAccess({ fsPath: "/extension" });
  await access.search(searchRequest, "python").completion;
  access.closeInspection();
  await access.matched(searchReport.results[0]).inspect();
  expect(mock.services[0].dispose).not.toHaveBeenCalled();
  access.dispose();
});

it("discards late search completion after a source edit", async () => {
  let finish;
  mock.nextSearch = vi.fn(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const access = new SearchAstAccess({ fsPath: "/extension" });
  const pending = access.search(searchRequest, "python").completion;
  mock.changed({
    document: { uri: { fsPath: "/real/source.cpp" } },
    contentChanges: [{ text: "changed" }],
  });
  finish(searchReport);
  await expect(pending).rejects.toThrow(/changed/);
  expect(() => access.matched(searchReport.results[0])).toThrow(/expired/);
  expect(mock.services[0].dispose).toHaveBeenCalled();
  access.dispose();
});

it("keeps the previous matches if cancellation races a successful worker report", async () => {
  const access = new SearchAstAccess({ fsPath: "/extension" });
  await access.search(searchRequest, "python").completion;
  const old = access.matched(searchReport.results[0]);
  let finish;
  mock.nextSearch = vi.fn(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const running = access.search(searchRequest, "python");
  running.cancel();
  finish(searchReport);
  await expect(running.completion).rejects.toThrow(/cancelled/);
  expect(mock.services[1].cancel).toHaveBeenCalledOnce();
  expect(mock.services[0].dispose).not.toHaveBeenCalled();
  await old.inspect();
  access.dispose();
});

it("does not let a delayed old edit notification close a replacement buffer context", async () => {
  const invalidated = vi.fn(),
    access = new SearchAstAccess({ fsPath: "/extension" }, invalidated, true);
  const old = await access.open(undefined, "/real/source.cpp");
  await old.inspect();
  mock.changed({
    document: { uri: { fsPath: "/alias/source.cpp" } },
    contentChanges: [{ text: "changed" }],
  });
  expect(mock.resolve).toBeTypeOf("function");
  access.close();
  const fresh = await access.open(undefined, "/real/source.cpp");
  await fresh.inspect();
  mock.resolve("/real/source.cpp");
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(invalidated).not.toHaveBeenCalled();
  expect(fresh.session().service).toBe(mock.services[1]);
  expect(mock.services[1].dispose).not.toHaveBeenCalled();
  access.dispose();
});

it("invalidates a known source synchronously so rebuilding cannot race its edit", async () => {
  const invalidated = vi.fn(),
    access = new SearchAstAccess({ fsPath: "/extension" }, invalidated, true);
  const context = await access.open(undefined, "/real/source.cpp");
  await context.inspect();
  mock.changed({
    document: { uri: { fsPath: "/real/source.cpp" } },
    contentChanges: [{ text: "changed" }],
  });
  expect(invalidated).toHaveBeenCalledOnce();
  expect(invalidated).toHaveBeenCalledWith("edit");
  expect(mock.services[0].dispose).toHaveBeenCalledOnce();
  expect(() => context.session()).toThrow("Source or settings changed");
  access.dispose();
});

it("keeps an unsaved overlay alive when delayed disk events arrive, but invalidates after saving", async () => {
  const document = {
      uri: { fsPath: "/real/source.cpp", scheme: "file" },
      isDirty: true,
      isClosed: false,
      version: 2,
      getText: () => "struct Draft {};",
    },
    invalidated = vi.fn(),
    access = new SearchAstAccess({ fsPath: "/extension" }, invalidated, true);
  vscode.workspace.textDocuments.push(document);
  const context = await access.open(undefined, document.uri.fsPath);
  await context.inspect();
  mock.disk(document.uri);
  expect(invalidated).not.toHaveBeenCalled();
  expect(context.session().settings.buffers).toEqual({
    "/real/source.cpp": "struct Draft {};",
  });
  document.isDirty = false;
  mock.disk(document.uri);
  expect(invalidated).toHaveBeenCalledOnce();
  expect(() => context.session()).toThrow("Source or settings changed");
  access.dispose();
});
