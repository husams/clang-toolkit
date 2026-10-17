import { realpath } from "node:fs/promises";
import { dirname } from "node:path";
import * as vscode from "vscode";
import { ActionService, type ActionSettings } from "./action-service.js";
import type {
  AstInspection,
  AstReference,
  SourceSelection,
} from "./ast-model.js";
import { findPython } from "./console-service.js";
import type { Result } from "./model.js";

export interface SearchAstContext {
  inspect(id?: string): Promise<AstInspection>;
  reference(reference: AstReference): Promise<AstInspection>;
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
  private readonly buffers = new Map<
    string,
    { document: vscode.TextDocument; version: number }
  >();
  private readonly disposables: vscode.Disposable[] = [];
  constructor(
    private readonly uri: vscode.Uri,
    private readonly invalidated: (reason?: "edit") => void = () => {},
    private readonly retained = false,
  ) {
    const watcher = vscode.workspace.createFileSystemWatcher(
      "**/*.{c,cc,cpp,cxx,h,hh,hpp,hxx}",
    );
    const reset = (reason?: "edit") => {
      this.reset();
      invalidated(reason);
    };
    const changed = async (uri: vscode.Uri, disk = false) => {
      const generation = this.generation;
      const header = /\.(?:h|hh|hpp|hxx)$/i.test(uri.fsPath);
      // Headers may affect any translation unit; unrelated source files do not.
      if (
        this.retained &&
        this.file &&
        (!header || (disk && this.buffers.size))
      ) {
        const file =
          uri.fsPath === this.file
            ? this.file
            : await realpath(uri.fsPath).catch(() => uri.fsPath);
        // A delayed alias lookup belongs to the context present at the edit,
        // not a replacement context opened while the lookup was in flight.
        if (generation !== this.generation) return;
        if (!header && file !== this.file) return;
        const buffer = this.buffers.get(file);
        // Disk notifications cannot change an immutable editor overlay. Saving
        // or editing its document still invalidates the snapshot normally.
        if (
          disk &&
          buffer?.document.isDirty &&
          buffer.document.version === buffer.version
        )
          return;
      }
      reset(disk ? undefined : "edit");
    };
    this.disposables.push(
      watcher,
      watcher.onDidChange((uri) => void changed(uri, true)),
      watcher.onDidCreate((uri) => void changed(uri, true)),
      watcher.onDidDelete((uri) => void changed(uri, true)),
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
    this.buffers.clear();
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
    const documents = vscode.workspace.textDocuments.filter(
      (doc) =>
        !doc.isClosed &&
        doc.uri.scheme === "file" &&
        /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i.test(doc.uri.fsPath),
    );
    if (!this.retained && documents.some((doc) => doc.isDirty))
      throw new Error("Save C++ changes before inspecting AST nodes.");
    const snapshots = (
      await Promise.all(
        documents.map(async (document) => {
          const version = document.version,
            text = document.getText(),
            dirty = document.isDirty;
          const file = await realpath(document.uri.fsPath).catch(
            () => document.uri.fsPath,
          );
          return { document, version, text, dirty, file };
        }),
      )
    ).filter(
      ({ file }) =>
        file === translationUnit || /\.(?:h|hh|hpp|hxx)$/i.test(file),
    );
    const buffers: Record<string, string> = {};
    for (const { file, text, dirty } of snapshots) {
      if (!dirty) continue;
      if (buffers[file] !== undefined && buffers[file] !== text)
        throw new Error(
          "Two editors have different unsaved contents for the same C++ file.",
        );
      buffers[file] = text;
    }
    const unchanged = () =>
      snapshots.every(
        ({ document, version, dirty }) =>
          (!dirty || !document.isClosed) && document.version === version,
      );
    if (!unchanged())
      throw new Error("C++ edits changed while preparing the AST; try again.");
    const config = vscode.workspace.getConfiguration("ctk");
    const settings: ActionSettings = {
      directory:
        vscode.workspace.getWorkspaceFolder(vscode.Uri.file(translationUnit))
          ?.uri.fsPath ?? dirname(translationUnit),
      timeoutMs: config.get<number>("rpcTimeoutMs", 30000),
      compileArguments: config.get<string[]>("compileArguments", []),
      ...(Object.keys(buffers).length ? { buffers } : {}),
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
    for (const { file, document, version, dirty } of snapshots)
      if (dirty) this.buffers.set(file, { document, version });
    const generation = this.generation;
    let root: AstInspection["root"] | undefined;
    const current = () => {
      if (generation !== this.generation || !unchanged())
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
      reference: async (reference) => {
        current();
        const inspection = await service.inspect(settings, {
          translationUnit,
          reference,
        });
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
