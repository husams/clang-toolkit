import { realpath } from "node:fs/promises";
import * as vscode from "vscode";

const cxx = /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i;

export class FileInspectionSync implements vscode.Disposable {
  private document: vscode.TextDocument | undefined;
  private file: string | undefined;
  private generation = 0;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private loading = false;
  private paused = 0;
  private readonly listeners: vscode.Disposable[];
  constructor(
    private readonly load: (
      editor: vscode.TextEditor,
      current: () => boolean,
      force: boolean,
    ) => Promise<void>,
    private readonly failed: (error: unknown) => void,
    private readonly hasContext: () => boolean = () => true,
  ) {
    this.listeners = [
      vscode.window.onDidChangeActiveTextEditor((editor) =>
        this.observe(editor),
      ),
      vscode.workspace.onDidSaveTextDocument((document) => {
        const editor = vscode.window.activeTextEditor;
        if (editor?.document === document) this.observe(editor, true);
      }),
      vscode.workspace.onDidCloseTextDocument((document) => {
        if (this.document === document) {
          this.cancel();
          this.document = undefined;
          this.file = undefined;
        }
      }),
      vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("ctk"))
          this.observe(vscode.window.activeTextEditor, true);
      }),
      vscode.workspace.onDidGrantWorkspaceTrust(() =>
        this.observe(vscode.window.activeTextEditor, true),
      ),
    ];
    this.observe(vscode.window.activeTextEditor);
  }
  private observe(editor: vscode.TextEditor | undefined, force = false): void {
    if (this.paused) return;
    if (
      editor?.document.uri.scheme !== "file" ||
      !cxx.test(editor.document.uri.fsPath)
    ) {
      this.cancel();
      return;
    }
    const document = editor.document;
    if (!force && this.document === document && this.hasContext()) return;
    this.cancel();
    if (!vscode.workspace.isTrusted) return;
    this.document = document;
    const generation = this.generation,
      version = document.version;
    const current = () =>
      generation === this.generation &&
      !document.isClosed &&
      document.version === version &&
      vscode.window.activeTextEditor?.document === document;
    this.timer = setTimeout(() => {
      this.timer = undefined;
      if (!current()) {
        this.document = undefined;
        return;
      }
      this.loading = true;
      void (async () => {
        const file = await realpath(document.uri.fsPath);
        if (!current()) return;
        // VS Code may hold /var and /private/var editors for the same file.
        if (!force && this.file === file && this.hasContext()) return;
        this.file = file;
        await this.load(editor, current, force);
      })()
        .catch(this.failed)
        .finally(() => {
          if (generation === this.generation) {
            this.loading = false;
            if (!current()) this.document = undefined;
          }
        });
    }, 180);
  }
  private cancel(): void {
    this.generation++;
    if (this.timer || this.loading) this.document = undefined;
    clearTimeout(this.timer);
    this.timer = undefined;
    this.loading = false;
  }
  pause(): void {
    this.paused++;
    this.cancel();
  }
  refresh(force = true): void {
    this.document = undefined;
    this.file = undefined;
    this.observe(vscode.window.activeTextEditor, force);
  }
  resume(): void {
    this.paused--;
    if (!this.paused) {
      this.document = vscode.window.activeTextEditor?.document;
      this.file = this.document?.uri.fsPath;
      const document = this.document,
        generation = this.generation;
      if (document?.uri.scheme === "file")
        void realpath(document.uri.fsPath)
          .then((file) => {
            if (generation === this.generation && document === this.document)
              this.file = file;
          })
          .catch(this.failed);
    }
  }
  dispose(): void {
    this.cancel();
    for (const listener of this.listeners) listener.dispose();
  }
}
