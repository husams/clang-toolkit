import * as vscode from "vscode";
import type { Result } from "./model.js";
import { sourceOffsets, sourceTarget } from "./source-range.js";

export class SourceHighlight implements vscode.Disposable {
  private generation = 0;
  private editor: vscode.TextEditor | undefined;
  private range: vscode.Range | undefined;
  private expected: { uri: string; range: vscode.Range } | undefined;
  private collapsed: { uri: string; range: vscode.Range }[] = [];
  private readonly decoration = vscode.window.createTextEditorDecorationType({
    backgroundColor: new vscode.ThemeColor(
      "editor.findMatchHighlightBackground",
    ),
    border: "1px solid",
    borderColor: new vscode.ThemeColor("editor.findMatchHighlightBorder"),
    rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
  });
  private readonly changed = vscode.workspace.onDidChangeTextDocument(
    (event) => {
      if (
        event.contentChanges.length &&
        event.document === this.editor?.document
      )
        this.clear();
    },
  );

  ownsSelection(
    editor: vscode.TextEditor,
    selection: vscode.Selection,
    kind?: vscode.TextEditorSelectionChangeKind,
  ): boolean {
    const uri = editor.document.uri.toString();
    if (
      kind === vscode.TextEditorSelectionChangeKind.Keyboard ||
      kind === vscode.TextEditorSelectionChangeKind.Mouse
    ) {
      this.collapsed = this.collapsed.filter((entry) => entry.uri !== uri);
    } else {
      const index = this.collapsed.findIndex(
        (entry) => entry.uri === uri && entry.range.isEqual(selection),
      );
      if (index >= 0) {
        this.collapsed.splice(index, 1);
        return true;
      }
    }
    return Boolean(
      (this.expected?.uri === uri && this.expected.range.isEqual(selection)) ||
        (this.editor === editor && this.range?.isEqual(selection)),
    );
  }
  clear(collapseSelection = false): void {
    this.generation++;
    if (
      collapseSelection &&
      this.range &&
      !this.range.isEmpty &&
      this.editor?.selection.isEqual(this.range)
    ) {
      const selection = new vscode.Selection(
        this.editor.selection.active,
        this.editor.selection.active,
      );
      // VS Code reports our collapse asynchronously as a Command event.
      this.collapsed.push({
        uri: this.editor.document.uri.toString(),
        range: selection,
      });
      this.collapsed = this.collapsed.slice(-8);
      this.editor.selection = selection;
    }
    this.editor?.setDecorations(this.decoration, []);
    this.editor = undefined;
    this.range = undefined;
    this.expected = undefined;
  }
  async reveal(result: Result): Promise<void> {
    this.clear(true);
    const generation = this.generation;
    const target = sourceTarget(result);
    if (!target) return;
    const document = await vscode.workspace.openTextDocument(
      vscode.Uri.file(target.file),
    );
    if (generation !== this.generation || document.isDirty) return;
    const version = document.version;
    const offsets = sourceOffsets(target, document.getText());
    if (!offsets) return;
    const range = new vscode.Range(
      document.positionAt(offsets.start),
      document.positionAt(offsets.end),
    );
    const visible = vscode.window.visibleTextEditors.find(
      (editor) => editor.document === document,
    );
    this.expected = { uri: document.uri.toString(), range };
    const editor = await vscode.window.showTextDocument(document, {
      viewColumn: visible?.viewColumn ?? vscode.ViewColumn.One,
      selection: range,
      preserveFocus: true,
      preview: false,
    });
    if (
      generation !== this.generation ||
      document.version !== version ||
      document.isDirty
    )
      return;
    editor.revealRange(
      range,
      vscode.TextEditorRevealType.InCenterIfOutsideViewport,
    );
    editor.setDecorations(this.decoration, range.isEmpty ? [] : [range]);
    this.editor = editor;
    this.range = range;
    this.expected = undefined;
  }
  dispose(): void {
    this.clear();
    this.collapsed = [];
    this.changed.dispose();
    this.decoration.dispose();
  }
}
