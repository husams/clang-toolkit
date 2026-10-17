import { beforeEach, expect, it, vi } from "vitest";
import * as vscode from "vscode";
import { SearchAstAccess } from "../src/ast-access.js";

const mock = vi.hoisted(() => ({
  services: [],
  changed: undefined,
  resolve: undefined,
  disk: undefined,
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
  vscode.workspace.textDocuments.length = 0;
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
