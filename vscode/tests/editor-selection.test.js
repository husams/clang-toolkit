import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { EditorSelectionSync } from "../src/editor-selection.js";

const mock = vi.hoisted(() => ({
  changed: undefined,
  activeChanged: undefined,
  editor: undefined,
}));
vi.mock("vscode", () => ({
  workspace: { isTrusted: true },
  window: {
    get activeTextEditor() {
      return mock.editor;
    },
    onDidChangeActiveTextEditor: (listener) => {
      mock.activeChanged = listener;
      return { dispose() {} };
    },
    onDidChangeTextEditorSelection: (listener) => {
      mock.changed = listener;
      return { dispose() {} };
    },
  },
}));
beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

function setup() {
  const document = {
      uri: { scheme: "file", fsPath: "/source.cpp" },
      isDirty: true,
      isClosed: false,
      version: 2,
      getText: () => "// λ😀\nint draft;",
      offsetAt: (position) => position.character,
    },
    select = vi.fn(async () => undefined),
    highlight = { ownsSelection: vi.fn(() => false), clear: vi.fn() },
    sync = new EditorSelectionSync(highlight, select, vi.fn()),
    editor = { document, selection: undefined };
  mock.editor = editor;
  const move = (offset, kind = 1) => {
    const position = { character: offset },
      selection = {
        start: position,
        end: position,
        isEqual: (other) => other.start.character === offset,
      };
    editor.selection = selection;
    mock.changed({ textEditor: editor, selections: [selection], kind });
  };
  return { document, select, sync, move, highlight };
}

it("looks up a cursor in the current unsaved buffer using its UTF-8 offset", async () => {
  const { move, select, sync } = setup();
  move(11);
  await vi.advanceTimersByTimeAsync(180);
  expect(select).toHaveBeenCalledOnce();
  const [selection, current] = select.mock.calls[0];
  expect(selection).toEqual({
    file: "/source.cpp",
    start: Buffer.byteLength("// λ😀\nint "),
    end: Buffer.byteLength("// λ😀\nint "),
  });
  expect(current()).toBe(true);
  sync.dispose();
});

it("drops a cursor lookup if the unsaved buffer changes before the debounce", async () => {
  const { move, document, select, sync } = setup();
  move(11);
  document.version++;
  await vi.advanceTimersByTimeAsync(180);
  expect(select).not.toHaveBeenCalled();
  sync.dispose();
});

it("invalidates an in-flight lookup when a later cursor or explicit cancellation arrives", async () => {
  const { move, select, sync } = setup();
  move(11);
  await vi.advanceTimersByTimeAsync(180);
  const previous = select.mock.calls[0][1];
  move(12);
  expect(previous()).toBe(false);
  await vi.advanceTimersByTimeAsync(180);
  const current = select.mock.calls[1][1];
  expect(current()).toBe(true);
  sync.cancel();
  expect(current()).toBe(false);
  sync.dispose();
});

it("ignores selections made by the inspector and non-user editor updates", async () => {
  const { move, select, sync, highlight } = setup();
  highlight.ownsSelection.mockReturnValue(true);
  move(11);
  highlight.ownsSelection.mockReturnValue(false);
  mock.changed({
    textEditor: mock.editor,
    selections: [mock.editor.selection],
  });
  await vi.advanceTimersByTimeAsync(180);
  expect(select).not.toHaveBeenCalled();
  expect(highlight.clear).not.toHaveBeenCalled();
  sync.dispose();
});
