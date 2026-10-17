import { realpath } from "node:fs/promises";
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
    retained: boolean;
  };
  transfer(): void;
}

// Owns a live context for an opened file or a search result; action results use
// their existing action host instead.
export class SearchAstAccess implements vscode.Disposable {
  private service: ActionService | undefined;
  private generation = 0;
  private file: string | undefined;
  private readonly disposables: vscode.Disposable[] = [];
  constructor(
    private readonly uri: vscode.Uri,
    private readonly invalidated: () => void = () => {},
    private readonly retained = false,
  ) {
    const watcher = vscode.workspace.createFileSystemWatcher(
      "**/*.{c,cc,cpp,cxx,h,hh,hpp,hxx}",
    );
    const reset = () => {
      this.reset();
      invalidated();
    };
    const changed = async (uri: vscode.Uri) => {
      // Headers may affect any translation unit; unrelated source files do not.
      if (
        this.retained &&
        this.file &&
        !/\.(?:h|hh|hpp|hxx)$/i.test(uri.fsPath)
      ) {
        const file = await realpath(uri.fsPath).catch(() => uri.fsPath);
        if (file !== this.file) return;
      }
      reset();
    };
    this.disposables.push(
      watcher,
      watcher.onDidChange(changed),
      watcher.onDidCreate(changed),
      watcher.onDidDelete(changed),
      vscode.workspace.onDidChangeTextDocument((e) => {
        if (
          e.contentChanges.length &&
          /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i.test(e.document.uri.fsPath)
        )
          void changed(e.document.uri);
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
  close(): void {
    this.reset();
  }
  async open(
    result: Result | undefined,
    translationUnit: string,
  ): Promise<SearchAstContext> {
    if (!vscode.workspace.isTrusted)
      throw new Error("Trust this workspace before inspecting AST nodes.");
    const dirty = vscode.workspace.textDocuments.filter(
      (doc) =>
        doc.isDirty && /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i.test(doc.uri.fsPath),
    );
    const relevantDirty = !this.retained
      ? dirty.length > 0
      : (
          await Promise.all(
            dirty.map(
              async (doc) =>
                /\.(?:h|hh|hpp|hxx)$/i.test(doc.uri.fsPath) ||
                (await realpath(doc.uri.fsPath).catch(() => doc.uri.fsPath)) ===
                  translationUnit,
            ),
          )
        ).some(Boolean);
    if (relevantDirty)
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
    // A newly opened file or selected search result starts a fresh history.
    // Release the previous context, including bounded native child caches.
    this.reset();
    this.file = translationUnit;
    const generation = this.generation;
    let root: AstInspection["root"] | undefined;
    const current = () => {
      if (generation !== this.generation)
        throw new Error(
          "Source or settings changed; reselect a current analysis result.",
        );
    };
    const python = await findPython(
      config.get<string>("pythonPath", ""),
      settings.directory,
    );
    current();
    const service = new ActionService(
      vscode.Uri.joinPath(this.uri, "console", "action_service.py").fsPath,
      python,
      () => {
        if (this.service === service && root) {
          root = undefined;
          this.invalidated();
        }
      },
    );
    this.service = service;
    return {
      inspect: async (id) => {
        current();
        const inspection = await service.inspect(
          settings,
          id ?? { ...(result ? { result } : {}), translationUnit },
        );
        current();
        root = inspection.root;
        return inspection;
      },
      session: () => {
        current();
        if (!root)
          throw new Error("Inspect this node before choosing an action.");
        return { service, settings, root, retained: this.retained };
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
        if (!this.retained && this.service === service)
          this.service = undefined;
      },
    };
  }
  dispose(): void {
    this.reset();
    for (const item of this.disposables) item.dispose();
  }
}
