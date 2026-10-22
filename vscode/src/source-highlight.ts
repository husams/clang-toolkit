import { realpath } from "node:fs/promises";
import * as vscode from "vscode";
import type { Result } from "./model.js";
import { sourceOffsets, sourceTarget } from "./source-range.js";

export class SourceHighlight implements vscode.Disposable {
  private generation = 0;
  private editor: vscode.TextEditor | undefined;
  private range: vscode.Range | undefined;
  private expected: { uri: string; range: vscode.Range } | undefined;
  private collapsed: { uri: string; range: vscode.Range }[] = [];
  private readonly underline = vscode.window.createTextEditorDecorationType({
    textDecoration: "underline",
    rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
  });
  private readonly region: vscode.TextEditorDecorationType;
  private readonly changed = vscode.workspace.onDidChangeTextDocument(
    (event) => {
      if (
        event.contentChanges.length &&
        event.document === this.editor?.document
      )
        this.clear();
    },
  );

  constructor(extensionUri: vscode.Uri) {
    this.region = vscode.window.createTextEditorDecorationType({
      gutterIconPath: vscode.Uri.joinPath(
        extensionUri,
        "media",
        "match-region.svg",
      ),
      gutterIconSize: "100% 100%",
      isWholeLine: true,
      rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
    });
  }

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
    this.editor?.setDecorations(this.underline, []);
    this.editor?.setDecorations(this.region, []);
    this.editor = undefined;
    this.range = undefined;
    this.expected = undefined;
  }
  async reveal(result: Result, buffer?: string): Promise<void> {
    this.clear(true);
    const generation = this.generation;
    const target = sourceTarget(result);
    if (!target) return;
    const file = await realpath(target.file).catch(() => target.file);
    const documents = (
      await Promise.all(
        vscode.workspace.textDocuments
          .filter(
            (document) => !document.isClosed && document.uri.scheme === "file",
          )
          .map(async (document) => ({
            document,
            file: await realpath(document.uri.fsPath).catch(
              () => document.uri.fsPath,
            ),
          })),
      )
    )
      .filter((entry) => entry.file === file)
      .map((entry) => entry.document);
    if (buffer === undefined && documents.some((document) => document.isDirty))
      return;
    const existing =
      buffer !== undefined
        ? (documents.find((document) => document.getText() === buffer) ??
          documents[0])
        : undefined;
    const document =
      existing ??
      (await vscode.workspace.openTextDocument(vscode.Uri.file(target.file)));
    const matchesBuffer = () =>
      buffer !== undefined ? document.getText() === buffer : !document.isDirty;
    if (generation !== this.generation || !matchesBuffer()) return;
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
      !matchesBuffer()
    )
      return;
    editor.revealRange(
      range,
      vscode.TextEditorRevealType.InCenterIfOutsideViewport,
    );
    if (!range.isEmpty) {
      // Clang's end is exclusive: column zero belongs to the preceding line.
      const lastLine =
        range.end.line -
        (range.end.character === 0 && range.end.line > range.start.line
          ? 1
          : 0);
      if (lastLine === range.start.line) {
        editor.setDecorations(this.underline, [range]);
      } else {
        const lines: vscode.Range[] = [];
        for (let line = range.start.line; line <= lastLine; line++)
          lines.push(new vscode.Range(line, 0, line, 0));
        editor.setDecorations(this.region, lines);
      }
    }
    this.editor = editor;
    this.range = range;
    this.expected = undefined;
  }
  dispose(): void {
    this.clear();
    this.collapsed = [];
    this.changed.dispose();
    this.underline.dispose();
    this.region.dispose();
  }
}
