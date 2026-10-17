import * as vscode from "vscode";
import type { SourceSelection } from "./ast-model.js";
import type { SourceHighlight } from "./source-highlight.js";
import { selectedSource } from "./source-range.js";

export class EditorSelectionSync implements vscode.Disposable {
  private generation = 0;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private readonly listener: vscode.Disposable;
  private readonly activeEditor = vscode.window.onDidChangeActiveTextEditor(
    () => this.cancel(),
  );
  constructor(
    highlight: SourceHighlight,
    select: (
      selection: SourceSelection,
      current: () => boolean,
    ) => Promise<void>,
    failed: (error: unknown) => void,
  ) {
    this.listener = vscode.window.onDidChangeTextEditorSelection((event) => {
      const editor = event.textEditor,
        selection = event.selections[0];
      if (
        !selection ||
        highlight.ownsSelection(editor, selection, event.kind) ||
        !event.kind
      )
        return;
      this.cancel();
      const document = editor.document;
      if (
        !vscode.workspace.isTrusted ||
        document.uri.scheme !== "file" ||
        !/\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i.test(document.uri.fsPath)
      )
        return;
      const source = selectedSource(
        document.uri.fsPath,
        document.getText(),
        document.offsetAt(selection.start),
        document.offsetAt(selection.end),
      );
      if (!source) return;
      highlight.clear();
      const version = document.version,
        generation = this.generation;
      const current = () =>
        generation === this.generation &&
        !document.isClosed &&
        document.version === version &&
        editor.selection.isEqual(selection) &&
        vscode.window.activeTextEditor === editor;
      this.timer = setTimeout(() => {
        this.timer = undefined;
        if (!current()) return;
        void select(source, current).catch(failed);
      }, 180);
    });
  }
  cancel(): void {
    this.generation++;
    clearTimeout(this.timer);
    this.timer = undefined;
  }
  dispose(): void {
    this.cancel();
    this.listener.dispose();
    this.activeEditor.dispose();
  }
}
