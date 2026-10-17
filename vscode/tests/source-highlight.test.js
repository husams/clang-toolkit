import { beforeEach, expect, it, vi } from "vitest";
import { SourceHighlight } from "../src/source-highlight.js";

const mock = vi.hoisted(() => ({
  documents: [],
  open: vi.fn(),
  show: vi.fn(),
}));
vi.mock("node:fs/promises", () => ({
  realpath: async (file) => file.replace("/alias/", "/real/"),
}));
vi.mock("vscode", () => ({
  ThemeColor: class {},
  DecorationRangeBehavior: { ClosedClosed: 0 },
  ViewColumn: { One: 1 },
  TextEditorRevealType: { InCenterIfOutsideViewport: 1 },
  Uri: { file: (file) => ({ scheme: "file", fsPath: file }) },
  Range: class {
    constructor(start, end) {
      this.start = start;
      this.end = end;
      this.isEmpty = start.character === end.character;
    }
  },
  window: {
    createTextEditorDecorationType: () => ({ dispose: vi.fn() }),
    get visibleTextEditors() {
      return [];
    },
    showTextDocument: (...args) => mock.show(...args),
  },
  workspace: {
    get textDocuments() {
      return mock.documents;
    },
    onDidChangeTextDocument: () => ({ dispose: vi.fn() }),
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
});

function editor() {
  const document = {
    uri: {
      scheme: "file",
      fsPath: "/alias/source.cpp",
      toString: () => "file:///alias/source.cpp",
    },
    isClosed: false,
    isDirty: true,
    version: 2,
    getText: () => text,
    positionAt: (character) => ({ line: 0, character }),
  };
  const result = {
    document,
    revealRange: vi.fn(),
    setDecorations: vi.fn(),
  };
  mock.documents = [document];
  mock.show.mockResolvedValue(result);
  return result;
}

it("reuses a dirty editor alias and highlights its verified buffer without opening the disk copy", async () => {
  const target = editor(),
    highlight = new SourceHighlight();
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
  const highlight = new SourceHighlight();
  await highlight.reveal(node, "struct Base { int saved; };");
  await highlight.reveal(node);
  expect(mock.show).not.toHaveBeenCalled();
  expect(mock.open).not.toHaveBeenCalled();
  highlight.dispose();
});

it("drops a pending highlight if the buffer changes while its editor is being revealed", async () => {
  const target = editor(),
    highlight = new SourceHighlight();
  mock.show.mockImplementation(async () => {
    target.document.version++;
    return target;
  });
  await highlight.reveal(node, text);
  expect(target.revealRange).not.toHaveBeenCalled();
  expect(target.setDecorations).not.toHaveBeenCalled();
  highlight.dispose();
});
