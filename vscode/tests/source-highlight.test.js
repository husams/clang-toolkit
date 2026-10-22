import { beforeEach, expect, it, vi } from "vitest";
import * as vscode from "vscode";
import { SourceHighlight } from "../src/source-highlight.js";

const mock = vi.hoisted(() => ({
  documents: [],
  open: vi.fn(),
  show: vi.fn(),
  changed: undefined,
  decorations: [],
}));
vi.mock("node:fs/promises", () => ({
  realpath: async (file) => file.replace("/alias/", "/real/"),
}));
vi.mock("vscode", () => ({
  ThemeColor: class {},
  DecorationRangeBehavior: { ClosedClosed: 0 },
  ViewColumn: { One: 1 },
  TextEditorRevealType: { InCenterIfOutsideViewport: 1 },
  Uri: {
    file: (file) => ({ scheme: "file", fsPath: file }),
    joinPath: (uri, ...parts) => ({ fsPath: [uri.fsPath, ...parts].join("/") }),
  },
  Range: class {
    constructor(start, end, endLine, endCharacter) {
      this.start =
        typeof start === "number" ? { line: start, character: end } : start;
      this.end =
        typeof start === "number"
          ? { line: endLine, character: endCharacter }
          : end;
      this.isEmpty =
        this.start.line === this.end.line &&
        this.start.character === this.end.character;
    }
    isEqual(other) {
      return (
        this.start.line === other.start.line &&
        this.start.character === other.start.character &&
        this.end.line === other.end.line &&
        this.end.character === other.end.character
      );
    }
  },
  Selection: class {
    constructor(start, end) {
      this.start = start;
      this.end = this.active = end;
    }
    isEqual(other) {
      return (
        this.start.line === other.start.line &&
        this.start.character === other.start.character &&
        this.end.line === other.end.line &&
        this.end.character === other.end.character
      );
    }
  },
  window: {
    createTextEditorDecorationType: (options) => {
      const decoration = { options, dispose: vi.fn() };
      mock.decorations.push(decoration);
      return decoration;
    },
    get visibleTextEditors() {
      return [];
    },
    showTextDocument: (...args) => mock.show(...args),
  },
  workspace: {
    getConfiguration: () => ({ get: (_key, fallback) => fallback }),
    onDidChangeConfiguration: () => ({ dispose() {} }),
    get textDocuments() {
      return mock.documents;
    },
    onDidChangeTextDocument: (listener) => {
      mock.changed = listener;
      return { dispose: vi.fn() };
    },
    openTextDocument: (...args) => mock.open(...args),
  },
}));

const text = "struct Base { int draft; };",
  file = "/real/source.cpp",
  node = {
    id: "base",
    name: "Base",
    kind: "CXXRecordDecl",
    file,
    line: 1,
    column: 1,
    excerpt: text,
    raw: {
      binding: {
        range: {
          expansionBegin: { valid: true, file, line: 1, column: 1, offset: 0 },
          expansionEndExclusive: {
            valid: true,
            file,
            line: 1,
            column: text.length + 1,
            offset: text.length,
          },
        },
      },
    },
  };

beforeEach(() => {
  vi.clearAllMocks();
  mock.documents = [];
  mock.decorations = [];
});

const extensionUri = { fsPath: "/extension" };

function editor(contents = text) {
  const document = {
    uri: {
      scheme: "file",
      fsPath: "/alias/source.cpp",
      toString: () => "file:///alias/source.cpp",
    },
    isClosed: false,
    isDirty: true,
    version: 2,
    getText: () => contents,
    positionAt: (offset) => {
      const lines = contents.slice(0, offset).split("\n");
      return { line: lines.length - 1, character: lines.at(-1).length };
    },
  };
  const result = {
    document,
    revealRange: vi.fn(),
    setDecorations: vi.fn(),
  };
  mock.documents = [document];
  mock.show.mockImplementation(async (_document, options) => {
    result.selection = new vscode.Selection(
      options.selection.start,
      options.selection.end,
    );
    return result;
  });
  return result;
}

it("reuses a dirty editor alias and highlights its verified buffer without opening the disk copy", async () => {
  const target = editor(),
    highlight = new SourceHighlight(extensionUri);
  await highlight.reveal(node, text);
  expect(mock.open).not.toHaveBeenCalled();
  expect(mock.show).toHaveBeenCalledWith(
    target.document,
    expect.objectContaining({ preserveFocus: true }),
  );
  expect(target.revealRange).toHaveBeenCalledOnce();
  expect(target.setDecorations.mock.calls[0][1][0]).toMatchObject({
    start: { character: 0 },
    end: { character: text.length },
  });
  highlight.dispose();
});

it("refuses ranges from a stale snapshot or a saved-file parse in an unsaved editor", async () => {
  editor();
  const highlight = new SourceHighlight(extensionUri);
  await highlight.reveal(node, "struct Base { int saved; };");
  await highlight.reveal(node);
  expect(mock.show).not.toHaveBeenCalled();
  expect(mock.open).not.toHaveBeenCalled();
  highlight.dispose();
});

it("drops a pending highlight if the buffer changes while its editor is being revealed", async () => {
  const target = editor(),
    highlight = new SourceHighlight(extensionUri);
  mock.show.mockImplementation(async () => {
    target.document.version++;
    return target;
  });
  await highlight.reveal(node, text);
  expect(target.revealRange).not.toHaveBeenCalled();
  expect(target.setDecorations).not.toHaveBeenCalled();
  highlight.dispose();
});

function match(contents, start = 0, end = contents.length) {
  const result = structuredClone(node);
  result.raw.binding.range.expansionBegin.offset = start;
  result.raw.binding.range.expansionEndExclusive.offset = end;
  return result;
}

it("underlines only the matched characters for a single-line match", async () => {
  const target = editor(),
    highlight = new SourceHighlight(extensionUri);
  await highlight.reveal(match(text, 7, 11), text);
  expect(target.setDecorations).toHaveBeenCalledWith(mock.decorations[0], [
    expect.objectContaining({
      start: { line: 0, character: 7 },
      end: { line: 0, character: 11 },
    }),
  ]);
  expect(mock.decorations[0].options).toMatchObject({
    textDecoration: "underline solid",
  });
  expect(target.setDecorations).not.toHaveBeenCalledWith(
    mock.decorations[1],
    expect.anything(),
  );
  highlight.dispose();
});

it.each([false, true])(
  "marks every line of a block, including blank lines, with an exclusive end at next line: %s",
  async (nextLineEnd) => {
    const contents = "struct Base {\n\n  int draft;\n};\nint after;";
    const target = editor(contents),
      highlight = new SourceHighlight(extensionUri);
    const end = contents.indexOf("int after;") - (nextLineEnd ? 0 : 1);
    await highlight.reveal(match(contents, 0, end), contents);
    expect(target.setDecorations).toHaveBeenCalledWith(mock.decorations[1], [
      new vscode.Range(0, 0, 0, 0),
      new vscode.Range(1, 0, 1, 0),
      new vscode.Range(2, 0, 2, 0),
      new vscode.Range(3, 0, 3, 0),
    ]);
    expect(mock.decorations[1].options).toMatchObject({
      gutterIconPath: { fsPath: "/extension/media/match-region.svg" },
      gutterIconSize: "100% 100%",
      isWholeLine: true,
    });
    expect(target.setDecorations).not.toHaveBeenCalledWith(
      mock.decorations[0],
      expect.anything(),
    );
    highlight.dispose();
  },
);

it("replaces a block marker when selecting a single-line result and clears it on edits", async () => {
  const contents = "struct Base {\n  int draft;\n};";
  const target = editor(contents),
    highlight = new SourceHighlight(extensionUri);
  await highlight.reveal(match(contents), contents);
  target.setDecorations.mockClear();
  await highlight.reveal(match(contents, 16, 25), contents);
  expect(target.setDecorations.mock.calls.slice(0, 2)).toEqual([
    [mock.decorations[0], []],
    [mock.decorations[1], []],
  ]);
  expect(target.setDecorations.mock.calls.at(-1)[0]).toBe(mock.decorations[0]);
  target.setDecorations.mockClear();
  mock.changed({ document: target.document, contentChanges: [{}] });
  expect(target.setDecorations.mock.calls).toEqual([
    [mock.decorations[0], []],
    [mock.decorations[1], []],
  ]);
  highlight.dispose();
  for (const decoration of mock.decorations)
    expect(decoration.dispose).toHaveBeenCalledOnce();
});

it("clears the previous editor's marker when a result opens another file", async () => {
  const contents = "struct Base {\n  int draft;\n};";
  const first = editor(contents),
    highlight = new SourceHighlight(extensionUri);
  await highlight.reveal(match(contents), contents);
  first.setDecorations.mockClear();
  const second = editor();
  second.document.uri = {
    scheme: "file",
    fsPath: "/real/other.cpp",
    toString: () => "file:///real/other.cpp",
  };
  const result = match(text);
  result.raw.binding.range.expansionBegin.file = "/real/other.cpp";
  result.raw.binding.range.expansionEndExclusive.file = "/real/other.cpp";
  await highlight.reveal(result, text);
  expect(first.setDecorations.mock.calls).toEqual([
    [mock.decorations[0], []],
    [mock.decorations[1], []],
  ]);
  expect(second.setDecorations).toHaveBeenCalledWith(
    mock.decorations[0],
    expect.arrayContaining([expect.any(vscode.Range)]),
  );
  highlight.dispose();
});
