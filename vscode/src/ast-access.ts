import { dirname } from "node:path";
import * as vscode from "vscode";
import { ActionService, type ActionSettings } from "./action-service.js";
import type { AstInspection, SourceSelection } from "./ast-model.js";
import { findPython } from "./console-service.js";
import type { Result } from "./model.js";

export interface SearchAstContext {
  inspect(id?: string): Promise<AstInspection>;
  selectSource(
    id: string,
    selection: SourceSelection,
  ): Promise<AstInspection | undefined>;
  session(): {
    service: ActionService;
    settings: ActionSettings;
    root: AstInspection["root"];
  };
  transfer(): void;
}

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
  ): Promise<SearchAstContext> {
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
    let root: AstInspection["root"] | undefined;
    const current = () => {
      if (generation !== this.generation)
        throw new Error(
          "Source or settings changed; reselect a current analysis result.",
        );
    };
    return {
      inspect: async (id) => {
        current();
        const inspection = await service.inspect(
          settings,
          id ?? { result, translationUnit },
        );
        current();
        root = inspection.root;
        return inspection;
      },
      session: () => {
        current();
        if (!root)
          throw new Error("Inspect this node before choosing an action.");
        return { service, settings, root };
      },
      selectSource: async (id, selection) => {
        current();
        const inspection = await service.selectSource(settings, id, selection);
        current();
        return inspection;
      },
      transfer: () => {
        current();
        // Actions now owns the live worker; new searches must not dispose it.
        if (this.service === service) this.service = undefined;
      },
    };
  }
  dispose(): void {
    this.reset();
    for (const item of this.disposables) item.dispose();
  }
}
