import { EventEmitter } from "node:events";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import * as vscode from "vscode";
import { SymbolNavigation } from "../src/symbol-navigation.js";

const mock = vi.hoisted(() => ({
  events: {},
  commands: {},
  children: [],
  requests: [],
  links: undefined,
  definitions: undefined,
  response: undefined,
  enabled: true,
  hold: false,
}));
vi.mock("../src/console-service.js", () => ({
  findPython: async () => "python",
}));
vi.mock("node:child_process", () => ({
  spawn: () => {
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.stderr = new EventEmitter();
    child.stdin = new EventEmitter();
    child.stdin.end = (json) => {
      const request = JSON.parse(json);
      mock.requests.push(request);
      child.finish = () => {
        child.stdout.emit(
          "data",
          Buffer.from(JSON.stringify(mock.response(request))),
        );
        child.emit("close", 0);
      };
      if (!mock.hold) queueMicrotask(child.finish);
    };
    child.kill = vi.fn(() => {
      queueMicrotask(() => child.emit("close", null));
    });
    mock.children.push(child);
    return child;
  },
}));
vi.mock("vscode", () => {
  class Position {
    constructor(line, character) {
      this.line = line;
      this.character = character;
    }
    isEqual(other) {
      return this.line === other.line && this.character === other.character;
    }
  }
  class Range {
    constructor(start, end) {
      this.start = start;
      this.end = end;
    }
    contains(position) {
      return (
        position.line === this.start.line &&
        position.character >= this.start.character &&
        position.character <= this.end.character
      );
    }
  }
  const uri = (path) => ({
    scheme: "file",
    fsPath: path,
    toString: () => `file://${path}`,
  });
  const subscribe = (name) => (listener) => {
    mock.events[name] = listener;
    return { dispose() {} };
  };
  return {
    Position,
    Range,
    Location: class {
      constructor(uri, position) {
        this.uri = uri;
        this.range = new Range(position, position);
      }
    },
    DocumentLink: class {
      constructor(range, target) {
        this.range = range;
        this.target = target;
      }
    },
    Uri: {
      file: uri,
      joinPath: (base, ...parts) => uri([base.fsPath, ...parts].join("/")),
      parse: (value) => ({ toString: () => value }),
    },
    DecorationRangeBehavior: { ClosedClosed: 0 },
    languages: {
      registerDocumentLinkProvider: (_selector, provider) => {
        mock.links = provider;
        return { dispose() {} };
      },
      registerDefinitionProvider: (_selector, provider) => {
        mock.definitions = provider;
        return { dispose() {} };
      },
    },
    commands: {
      registerCommand: (name, handler) => {
        mock.commands[name] = handler;
        return { dispose() {} };
      },
      executeCommand: vi.fn(),
    },
    window: {
      visibleTextEditors: [],
      createTextEditorDecorationType: vi.fn(() => ({ dispose() {} })),
      onDidChangeVisibleTextEditors: subscribe("visible"),
      showTextDocument: vi.fn(),
    },
    workspace: {
      isTrusted: true,
      textDocuments: [],
      getWorkspaceFolder: () => ({ uri: uri("/project") }),
      getConfiguration: () => ({
        get: (key, fallback) =>
          key === "symbolNavigation" ? mock.enabled : fallback,
      }),
      onDidOpenTextDocument: subscribe("open"),
      onDidCloseTextDocument: subscribe("close"),
      onDidChangeTextDocument: subscribe("edit"),
      onDidSaveTextDocument: subscribe("save"),
      onDidChangeConfiguration: subscribe("configuration"),
      onDidGrantWorkspaceTrust: subscribe("trust"),
      createFileSystemWatcher: () => ({
        dispose() {},
        onDidChange: subscribe("disk"),
        onDidCreate: subscribe("create"),
        onDidDelete: subscribe("delete"),
      }),
      openTextDocument: vi.fn(async (uri) => ({
        uri,
        lineCount: 1,
        lineAt: () => ({ text: "/* 😀 */ int target;" }),
      })),
    },
  };
});
let navigation;
const cancellation = { isCancellationRequested: false };
beforeEach(() => {
  vi.useFakeTimers();
  mock.events = {};
  mock.commands = {};
  mock.children = [];
  mock.requests = [];
  mock.enabled = true;
  mock.hold = false;
  vscode.workspace.isTrusted = true;
  vscode.workspace.textDocuments = [];
  vscode.window.visibleTextEditors = [];
  vi.clearAllMocks();
  mock.response = (request) =>
    request.mode === "scan"
      ? {
          references: [
            {
              start: Buffer.byteLength("/* 😀 */ "),
              end: Buffer.byteLength("/* 😀 */ target"),
              usr: "exact-overload",
              name: "target",
              target: { file: "/header.hpp", line: 1, column: 1 },
            },
          ],
        }
      : {
          targets: [
            {
              file: "/another-project/definition.cpp",
              line: 1,
              column: Buffer.byteLength("/* 😀 */ int ") + 1,
            },
          ],
        };
});
afterEach(() => {
  navigation?.dispose();
  vi.useRealTimers();
});
function setup() {
  let text = "/* 😀 */ target();";
  const document = {
    uri: vscode.Uri.file("/project/main.cpp"),
    languageId: "cpp",
    version: 1,
    isClosed: false,
    isDirty: true,
    getText: () => text,
    positionAt: (offset) => new vscode.Position(0, offset),
  };
  const editor = { document, setDecorations: vi.fn() };
  vscode.workspace.textDocuments = [document];
  vscode.window.visibleTextEditors = [editor];
  navigation = new SymbolNavigation(vscode.Uri.file("/extension"), vi.fn());
  return {
    document,
    editor,
    edit: (source) => {
      text = source;
      document.version++;
      mock.events.edit({ document, contentChanges: [{}] });
    },
  };
}
it("scans on open and underlines references with UTF-16 ranges without a command", async () => {
  const { document, editor } = setup();
  await vi.advanceTimersByTimeAsync(200);
  expect(mock.requests).toHaveLength(1);
  expect(mock.requests[0].buffers[document.uri.fsPath]).toBe(
    document.getText(),
  );
  const ranges = editor.setDecorations.mock.calls.at(-1)[1];
  expect(ranges[0].start.character).toBe("/* 😀 */ ".length);
  const links = await mock.links.provideDocumentLinks(document, cancellation);
  expect(links).toHaveLength(1);
  expect(mock.requests).toHaveLength(1);
  expect(links[0].target.toString()).toContain(
    "command:ctk.openSymbolDefinition?",
  );
});
it("resolves an exact USR outside the workspace for F12 and clickable links", async () => {
  const { document } = setup();
  const links = await mock.links.provideDocumentLinks(document, cancellation);
  const locations = await mock.definitions.provideDefinition(
    document,
    links[0].range.start,
    cancellation,
  );
  expect(mock.requests.at(-1).usr).toBe("exact-overload");
  expect(locations[0].uri.fsPath).toBe("/another-project/definition.cpp");
  expect(locations[0].range.start.character).toBe("/* 😀 */ int ".length);
  const args = JSON.parse(
    decodeURIComponent(links[0].target.toString().split("?")[1]),
  );
  await mock.commands["ctk.openSymbolDefinition"](...args);
  expect(vscode.window.showTextDocument).toHaveBeenCalledWith(
    expect.objectContaining({ fsPath: "/another-project/definition.cpp" }),
    expect.any(Object),
  );
});
it("clears stale underlines immediately and coalesces edits into one new scan", async () => {
  const { document, editor, edit } = setup();
  await vi.advanceTimersByTimeAsync(200);
  const links = await mock.links.provideDocumentLinks(document, cancellation);
  const args = JSON.parse(
    decodeURIComponent(links[0].target.toString().split("?")[1]),
  );
  edit("/* 😀 */ edited();");
  edit("/* 😀 */ latest();");
  expect(editor.setDecorations.mock.calls.at(-1)[1]).toEqual([]);
  await mock.commands["ctk.openSymbolDefinition"](...args);
  expect(vscode.window.showTextDocument).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(200);
  expect(mock.requests).toHaveLength(2);
  expect(mock.requests[1].buffers[document.uri.fsPath]).toBe(
    document.getText(),
  );
});
it("kills an in-flight scan when the file closes and ignores its late response", async () => {
  mock.hold = true;
  const { document, editor } = setup();
  await vi.advanceTimersByTimeAsync(200);
  document.isClosed = true;
  mock.events.close(document);
  expect(mock.children[0].kill).toHaveBeenCalled();
  mock.children[0].finish();
  await vi.advanceTimersByTimeAsync(0);
  expect(editor.setDecorations.mock.calls.at(-1)[1]).toEqual([]);
});
it("does not spawn workers for untrusted workspaces or when disabled", async () => {
  vscode.workspace.isTrusted = false;
  const { document } = setup();
  await vi.advanceTimersByTimeAsync(300);
  expect(mock.children).toHaveLength(0);
  vscode.workspace.isTrusted = true;
  mock.enabled = false;
  mock.events.configuration({ affectsConfiguration: () => true });
  expect(await mock.links.provideDocumentLinks(document, cancellation)).toEqual(
    [],
  );
  expect(mock.children).toHaveLength(0);
});
it("keeps the Clang declaration usable when global lookup fails", async () => {
  const { document } = setup();
  const response = mock.response;
  mock.response = (request) =>
    request.mode === "resolve"
      ? { error: "index unavailable" }
      : response(request);
  const links = await mock.links.provideDocumentLinks(document, cancellation);
  const locations = await mock.definitions.provideDefinition(
    document,
    links[0].range.start,
    cancellation,
  );
  expect(locations[0].uri.fsPath).toBe("/header.hpp");
});
it("cancels all background processes on disposal", async () => {
  mock.hold = true;
  setup();
  await vi.advanceTimersByTimeAsync(200);
  navigation.dispose();
  expect(mock.children[0].kill).toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(300);
  expect(mock.children).toHaveLength(1);
});

it("preserves a definition from the unsaved native snapshot during resolution", async () => {
  const response = mock.response;
  mock.response = (request) => {
    const result = response(request);
    if (request.mode === "scan") result.references[0].nativeDefinition = true;
    return result;
  };
  const { document } = setup();
  const links = await mock.links.provideDocumentLinks(document, cancellation);
  await mock.definitions.provideDefinition(
    document,
    links[0].range.start,
    cancellation,
  );
  expect(mock.requests.at(-1).nativeDefinition).toBe(true);
});

it("source edits replace only that source scan", async () => {
  const { document, edit } = setup();
  const other = { ...document, uri: vscode.Uri.file("/project/other.cpp") };
  vscode.workspace.textDocuments.push(other);
  mock.events.open(other);
  await vi.advanceTimersByTimeAsync(200);
  expect(mock.requests).toHaveLength(2);
  edit("/* 😀 */ replacement();");
  await vi.advanceTimersByTimeAsync(200);
  expect(mock.requests).toHaveLength(3);
  expect(mock.requests.at(-1).file).toBe(document.uri.fsPath);
});

it.each(["h", "hh", "hpp", "hxx", "i", "ii"])(
  "scans .%s files even when VS Code reports plain text",
  async (extension) => {
    const { document } = setup();
    mock.events.close(document);
    document.uri = vscode.Uri.file(`/project/input.${extension}`);
    document.languageId = "plaintext";
    mock.events.open(document);
    await vi.advanceTimersByTimeAsync(200);
    const links = await mock.links.provideDocumentLinks(document, cancellation);
    expect(links).toHaveLength(1);
    expect(mock.requests[0].file).toBe(document.uri.fsPath);
  },
);
