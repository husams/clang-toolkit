import { dirname } from "node:path";
import * as vscode from "vscode";
import { ActionService, type ActionSettings } from "./action-service.js";
import type { AstInspection } from "./ast-model.js";
import { findPython } from "./console-service.js";
import type { Result } from "./model.js";

// Search workers release their cursors after returning results. This owns a
// separate live context; action results instead use their existing action host.
export class SearchAstAccess implements vscode.Disposable {
  private service: ActionService | undefined;
  private generation = 0;
  private readonly disposables: vscode.Disposable[] = [];
  constructor(private readonly uri: vscode.Uri) {
    const watcher = vscode.workspace.createFileSystemWatcher(
      "**/*.{c,cc,cpp,cxx,h,hh,hpp,hxx}",
    );
    const reset = () => this.reset();
    this.disposables.push(
      watcher,
      watcher.onDidChange(reset),
      watcher.onDidCreate(reset),
      watcher.onDidDelete(reset),
      vscode.workspace.onDidChangeTextDocument((e) => {
        if (/\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i.test(e.document.uri.fsPath))
          reset();
      }),
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("ctk")) reset();
      }),
    );
  }
  private reset(): void {
    this.generation++;
    this.service?.dispose();
    this.service = undefined;
  }
  async open(
    result: Result,
    translationUnit: string,
  ): Promise<(id?: string) => Promise<AstInspection>> {
    if (!vscode.workspace.isTrusted)
      throw new Error("Trust this workspace before inspecting AST nodes.");
    if (
      vscode.workspace.textDocuments.some(
        (doc) =>
          doc.isDirty &&
          /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i.test(doc.uri.fsPath),
      )
    )
      throw new Error("Save C++ changes before inspecting AST nodes.");
    const config = vscode.workspace.getConfiguration("ctk");
    const settings: ActionSettings = {
      directory:
        vscode.workspace.getWorkspaceFolder(vscode.Uri.file(translationUnit))
          ?.uri.fsPath ?? dirname(translationUnit),
      timeoutMs: config.get<number>("rpcTimeoutMs", 30000),
      compileArguments: config.get<string[]>("compileArguments", []),
      ...Object.fromEntries(
        [
          ["endpoint", "server"],
          ["configPath", "configPath"],
          ["compilationDatabase", "compilationDatabase"],
          ["libraryDirectory", "libraryDirectory"],
        ].flatMap(([key, setting]) => {
          const value = config.get<string>(setting ?? "", "");
          return value ? [[key, value]] : [];
        }),
      ),
    };
    // A newly selected search result starts a fresh inspector history. Release
    // the previous search context, including any bounded native child caches.
    this.reset();
    this.service ??= new ActionService(
      vscode.Uri.joinPath(this.uri, "console", "action_service.py").fsPath,
      await findPython(
        config.get<string>("pythonPath", ""),
        settings.directory,
      ),
    );
    const generation = this.generation,
      service = this.service;
    return async (id) => {
      if (generation !== this.generation)
        throw new Error(
          "Source or settings changed; reselect a current analysis result.",
        );
      return service.inspect(settings, id ?? { result, translationUnit });
    };
  }
  dispose(): void {
    this.reset();
    for (const item of this.disposables) item.dispose();
  }
}
