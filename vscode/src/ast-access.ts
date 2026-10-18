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
import {
  queries,
  type Result,
  type RunReport,
  type RunRequest,
} from "./model.js";

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
  private pendingSearch: ActionService | undefined;
  private searchState:
    | {
        service: ActionService;
        settings: ActionSettings;
        report: RunReport;
        generation: number;
      }
    | undefined;
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
    this.pendingSearch?.dispose();
    this.service = undefined;
    this.pendingSearch = undefined;
    this.searchState = undefined;
    this.buffers.clear();
  }
  close(): void {
    this.reset();
  }
  closeInspection(): void {
    // Live search matches belong to the result list, even without an editor tab.
    if (!this.searchState) this.close();
  }
  search(
    request: RunRequest,
    python: string,
    progress: (text: string) => void = () => {},
  ): { completion: Promise<RunReport>; cancel(): void } {
    if (!vscode.workspace.isTrusted)
      throw new Error("Trust this workspace before searching C++ files.");
    if (this.pendingSearch) throw new Error("A search is already running.");
    const expressions = queries(
      request.action,
      request.values,
      request.kinds,
      request.includeHeaders,
    );
    const settings: ActionSettings = {
      directory: request.directory,
      compileArguments: request.compileArguments,
      timeoutMs: request.timeoutMs,
      ...Object.fromEntries(
        [
          "endpoint",
          "configPath",
          "compilationDatabase",
          "libraryDirectory",
        ].flatMap((key) => {
          const value = request[key as keyof RunRequest];
          return typeof value === "string" && value ? [[key, value]] : [];
        }),
      ),
    };
    const service = new ActionService(
      vscode.Uri.joinPath(this.uri, "console", "action_service.py").fsPath,
      python,
      () => {
        if (this.service === service) {
          this.reset();
          this.invalidated();
        }
      },
    );
    const generation = this.generation;
    let cancelled = false;
    this.pendingSearch = service;
    const completion = service
      .search(
        settings,
        request.files,
        expressions,
        request.maxResults,
        progress,
      )
      .then((report) => {
        if (cancelled) throw new Error("Analysis cancelled");
        if (this.generation !== generation || this.pendingSearch !== service)
          throw new Error("Source or settings changed; rerun the search.");
        // Replace the previous owner only once the new report is complete.
        this.service?.dispose();
        this.service = service;
        this.pendingSearch = undefined;
        this.file = undefined;
        this.buffers.clear();
        this.generation++;
        this.searchState = {
          service,
          settings,
          report,
          generation: this.generation,
        };
        return report;
      })
      .catch((error: unknown) => {
        if (this.pendingSearch === service) this.pendingSearch = undefined;
        service.dispose();
        throw error;
      });
    return {
      completion,
      cancel: () => {
        cancelled = true;
        service.cancel();
      },
    };
  }
  matched(result: Result): SearchAstContext {
    const state = this.searchState;
    const selected = state?.report.results.find(
      (row) => row.id === result.id && row.nodeId === result.nodeId,
    );
    if (!state || !selected?.nodeId || !selected.translationUnit)
      throw new Error("Search context expired; rerun the search.");
    const { service, settings, generation } = state;
    const nodeId = selected.nodeId;
    const translationUnit = selected.translationUnit;
    let root: AstInspection["root"] | undefined;
    const current = () => {
      if (this.generation !== generation)
        throw new Error("Source or settings changed; rerun the search.");
      if (
        vscode.workspace.textDocuments.some(
          (doc) =>
            !doc.isClosed &&
            doc.isDirty &&
            /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i.test(doc.uri.fsPath),
        )
      )
        throw new Error("Save C++ changes before inspecting search results.");
    };
    return {
      inspect: async (id) => {
        current();
        const inspection = await service.inspect(settings, id ?? nodeId);
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
      selectSource: async (id, selection) => {
        current();
        const inspection = await service.selectSource(settings, id, selection);
        current();
        return inspection;
      },
      session: () => {
        current();
        if (!root)
          throw new Error("Inspect this node before choosing an action.");
        return { service, settings, root, retained: false };
      },
      transfer: () => {
        current();
        if (this.service === service) this.service = undefined;
      },
    };
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
    const config = vscode.workspace.getConfiguration(
      "ctk",
      vscode.Uri.file(translationUnit),
    );
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
