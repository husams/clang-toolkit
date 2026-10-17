import * as vscode from "vscode";
import type { Result } from "./model.js";
import { sourceOffsets, sourceTarget } from "./source-range.js";

export class SourceHighlight implements vscode.Disposable {
  private generation = 0;
  private editor: vscode.TextEditor | undefined;
  private range: vscode.Range | undefined;
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

  private clear(collapseSelection = false): void {
    this.generation++;
    if (
      collapseSelection &&
      this.range &&
      this.editor?.selection.isEqual(this.range)
    )
      this.editor.selection = new vscode.Selection(
        this.editor.selection.active,
        this.editor.selection.active,
      );
    this.editor?.setDecorations(this.decoration, []);
    this.editor = undefined;
    this.range = undefined;
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
    const editor = await vscode.window.showTextDocument(document, {
      viewColumn: visible?.viewColumn ?? vscode.ViewColumn.One,
      selection: range,
      preserveFocus: true,
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
  }
  dispose(): void {
    this.clear();
    this.changed.dispose();
    this.decoration.dispose();
  }
}
