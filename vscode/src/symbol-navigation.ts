import { spawn } from "node:child_process";
import { basename, dirname } from "node:path";
import * as vscode from "vscode";
import { z } from "zod";
import { findPython } from "./console-service.js";
import { underlineStyle } from "./highlight-style.js";
import { ReferenceResults } from "./reference-results.js";

const targetSchema = z.object({
  file: z.string().min(1),
  line: z.number().int().positive(),
  column: z.number().int().positive(),
});
const referenceSchema = z.object({
  start: z.number().int().nonnegative(),
  end: z.number().int().positive(),
  name: z.string(),
  usr: z.string(),
  nativeDefinition: z.boolean().default(false),
  kind: z.string().default(""),
  signature: z.string().default(""),
  preview: z.string().default(""),
  target: targetSchema,
});
const responseSchema = z.object({
  references: z.array(referenceSchema).optional(),
  targets: z.array(targetSchema).optional(),
  errors: z.array(z.string()).default([]),
  error: z.string().optional(),
  occurrences: z
    .array(
      targetSchema.extend({
        project: z.string(),
        preview: z.string(),
        length: z.number(),
      }),
    )
    .optional(),
  coverage: z
    .object({ completed: z.number(), total: z.number(), projects: z.number() })
    .optional(),
  profile: z
    .object({
      file: z.string(),
      translationUnit: z.string(),
      workingDirectory: z.string(),
      compilationDatabase: z.string(),
      arguments: z.array(z.string()),
      provenance: z.string(),
      translationUnits: z.array(z.string()),
    })
    .optional(),
  details: z
    .object({
      project: z.string(),
      signature: z.string(),
      kind: z.string(),
      preview: z.string(),
      target: targetSchema.optional(),
      isDefinition: z.boolean().optional(),
    })
    .optional(),
});
type Reference = z.infer<typeof referenceSchema>;
type Target = z.infer<typeof targetSchema>;
type Response = z.infer<typeof responseSchema>;
interface Scan {
  version: number;
  generation: number;
  references: { reference: Reference; range: vscode.Range }[];
  pending?: Promise<void>;
  timer?: ReturnType<typeof setTimeout>;
  cancel?: () => void;
  state?: "queued" | "scanning" | "ready" | "failed";
  error?: string;
  details?: Map<string, Response>;
}
const supported = (document: vscode.TextDocument) =>
  document.uri.scheme === "file" &&
  (document.languageId === "cpp" ||
    document.languageId === "c" ||
    /\.(?:h|hh|hpp|hxx|i|ii)$/i.test(document.uri.fsPath));

/** Native references belong to one immutable editor snapshot, never to a name search. */
export class SymbolNavigation implements vscode.Disposable {
  private decoration = vscode.window.createTextEditorDecorationType(
    underlineStyle("symbolLinks"),
  );
  private readonly status = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    38,
  );
  private readonly referenceResults = new ReferenceResults();
  private readonly scans = new Map<vscode.TextDocument, Scan>();
  private readonly requests = new Set<() => void>();
  private readonly listeners: vscode.Disposable[];
  private generation = 0;
  private disposed = false;
  private referenceGeneration = 0;
  private referenceCancel: (() => void) | undefined;
  private compilerDocument?: vscode.TextDocument;
  private readonly compilerReports = new Map<string, string>();
  private readonly compilerChanged = new vscode.EventEmitter<vscode.Uri>();

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly log: (message: string) => void,
  ) {
    const selector = [
      { scheme: "file", language: "cpp" },
      { scheme: "file", language: "c" },
      { scheme: "file", pattern: "**/*.{h,hh,hpp,hxx,i,ii}" },
    ];
    this.listeners = [
      this.status,
      this.referenceResults,
      this.compilerChanged,
      vscode.workspace.registerTextDocumentContentProvider("ctk-compiler", {
        onDidChange: this.compilerChanged.event,
        provideTextDocumentContent: (uri) =>
          this.compilerReports.get(uri.toString()) ??
          "Compiler report is no longer available. Run CTK: Show Compiler Settings again.",
      }),
      vscode.window.onDidChangeActiveTextEditor(() => this.updateStatus()),
      vscode.languages.registerHoverProvider(selector, {
        provideHover: async (document, position, token) => {
          const selected = await this.selected(document, position);
          if (!selected || token.isCancellationRequested) return;
          const { scan, reference, range } = selected;
          let response = scan.details?.get(reference.usr);
          if (!response) {
            try {
              response = await this.request(
                document,
                { mode: "details", ...reference },
                () => {},
                () =>
                  this.current(document, scan) &&
                  !token.isCancellationRequested,
              );
              if (this.current(document, scan)) {
                scan.details ??= new Map();
                scan.details.set(reference.usr, response);
              }
            } catch {
              /* The native scan still supplies a useful hover offline. */
            }
          }
          if (!this.current(document, scan) || token.isCancellationRequested)
            return;
          const details = response?.details;
          const markdown = new vscode.MarkdownString();
          markdown.appendCodeblock(
            details?.signature || reference.signature || reference.name,
            "cpp",
          );
          markdown.appendText(`${details?.kind || reference.kind}\n`);
          if (details?.project)
            markdown.appendText(`Project: ${details.project}\n`);
          const location = details?.target ?? reference.target;
          markdown.appendText(
            `${details?.isDefinition ? "Definition" : "Declaration"}: ${location.file}:${location.line}:${location.column}\n`,
          );
          if (details?.preview || reference.preview)
            markdown.appendCodeblock(
              details?.preview || reference.preview,
              "cpp",
            );
          const args = encodeURIComponent(
            JSON.stringify([
              document.uri.toString(),
              scan.version,
              reference.start,
            ]),
          );
          markdown.appendMarkdown(
            `\n[Go to definition](command:ctk.openSymbolDefinition?${args}) · [Find all references](command:ctk.findSymbolReferences?${args})`,
          );
          markdown.isTrusted = {
            enabledCommands: [
              "ctk.openSymbolDefinition",
              "ctk.findSymbolReferences",
            ],
          };
          return new vscode.Hover(markdown, range);
        },
      }),
      vscode.languages.registerReferenceProvider(selector, {
        provideReferences: async (document, position, context, token) => {
          const selected = await this.selected(document, position);
          if (!selected || token.isCancellationRequested) return [];
          return this.references(
            document,
            selected.scan,
            selected.reference,
            context.includeDeclaration,
            token,
          );
        },
      }),
      vscode.commands.registerCommand(
        "ctk.openReference",
        async (value: unknown) => {
          const target = targetSchema.safeParse(value);
          if (!target.success) return;
          const location = await this.location(target.data);
          if (location)
            await vscode.window.showTextDocument(location.uri, {
              selection: location.range,
            });
        },
      ),
      vscode.commands.registerCommand(
        "ctk.findSymbolReferences",
        async (uri?: unknown, version?: unknown, start?: unknown) => {
          const document =
            typeof uri === "string"
              ? vscode.workspace.textDocuments.find(
                  (item) => item.uri.toString() === uri,
                )
              : vscode.window.activeTextEditor?.document;
          if (!document) return;
          const scan = await this.ensure(document);
          if (
            !scan ||
            (typeof version === "number" && document.version !== version)
          )
            return;
          const position = vscode.window.activeTextEditor?.selection.active;
          const item =
            typeof start === "number"
              ? scan.references.find((item) => item.reference.start === start)
              : position
                ? scan.references.find((item) => item.range.contains(position))
                : undefined;
          if (item) await this.references(document, scan, item.reference, true);
        },
      ),
      vscode.commands.registerCommand("ctk.navigationStatus", () =>
        this.showStatus(),
      ),
      vscode.commands.registerCommand("ctk.retrySymbolScan", () => {
        const document = vscode.window.activeTextEditor?.document;
        if (document) {
          this.clear(document);
          this.schedule(document);
        }
      }),
      vscode.commands.registerCommand("ctk.showCompilerSettings", () =>
        this.compilerSettings(),
      ),
      vscode.commands.registerCommand("ctk.selectHeaderTranslationUnit", () =>
        this.compilerSettings(true),
      ),
      vscode.languages.registerDocumentLinkProvider(selector, {
        provideDocumentLinks: async (document, token) => {
          if (
            vscode.workspace
              .getConfiguration("ctk", document.uri)
              .get<string>("symbolLinks.underline", "always") === "never"
          )
            return [];
          const scan = await this.ensure(document);
          if (token.isCancellationRequested || !scan) return [];
          return scan.references.map(({ reference, range }) => {
            const args = [
              document.uri.toString(),
              scan.version,
              reference.start,
            ];
            const link = new vscode.DocumentLink(
              range,
              vscode.Uri.parse(
                `command:ctk.openSymbolDefinition?${encodeURIComponent(JSON.stringify(args))}`,
              ),
            );
            link.tooltip = `Go to definition of ${reference.name}`;
            return link;
          });
        },
      }),
      vscode.languages.registerDefinitionProvider(selector, {
        provideDefinition: async (document, position, token) => {
          const scan = await this.ensure(document);
          if (!scan || token.isCancellationRequested) return [];
          const selected = scan.references.find(
            ({ range }) =>
              range.contains(position) && !range.end.isEqual(position),
          );
          if (!selected) return [];
          const locations = await this.definitions(
            document,
            scan,
            selected.reference,
          );
          return token.isCancellationRequested ? [] : locations;
        },
      }),
      vscode.commands.registerCommand(
        "ctk.openSymbolDefinition",
        async (uri: unknown, version: unknown, start: unknown) => {
          if (
            typeof uri !== "string" ||
            typeof version !== "number" ||
            typeof start !== "number"
          )
            return;
          const document = vscode.workspace.textDocuments.find(
            (item) => item.uri.toString() === uri,
          );
          const scan = document && this.scans.get(document);
          if (
            !document ||
            !scan ||
            document.version !== version ||
            scan.version !== version
          )
            return;
          const selected = scan.references.find(
            (item) => item.reference.start === start,
          );
          if (!selected) return;
          const locations = await this.definitions(
            document,
            scan,
            selected.reference,
          );
          if (locations.length === 1) {
            const target = locations[0];
            if (target)
              await vscode.window.showTextDocument(target.uri, {
                selection: target.range,
              });
          } else if (locations.length) {
            await vscode.commands.executeCommand(
              "editor.action.showReferences",
              document.uri,
              selected.range.start,
              locations,
            );
          }
        },
      ),
      vscode.workspace.onDidOpenTextDocument((document) =>
        this.schedule(document),
      ),
      vscode.workspace.onDidCloseTextDocument((document) =>
        this.clear(document),
      ),
      vscode.workspace.onDidChangeTextDocument((event) => {
        if (event.contentChanges.length && supported(event.document))
          this.changed(event.document);
      }),
      vscode.workspace.onDidSaveTextDocument((document) => {
        if (supported(document)) this.changed(document);
      }),
      vscode.window.onDidChangeVisibleTextEditors(() => {
        for (const editor of vscode.window.visibleTextEditors) {
          this.schedule(editor.document);
          this.decorate(editor.document);
        }
      }),
      vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("ctk")) {
          this.decoration.dispose();
          this.decoration = vscode.window.createTextEditorDecorationType(
            underlineStyle("symbolLinks"),
          );
          this.refresh();
        }
      }),
      vscode.workspace.onDidGrantWorkspaceTrust(() => this.refresh()),
    ];
    const watcher = vscode.workspace.createFileSystemWatcher(
      "**/*.{c,cc,cpp,cxx,i,ii,h,hh,hpp,hxx}",
    );
    this.listeners.push(
      watcher,
      watcher.onDidChange(() => this.refresh()),
      watcher.onDidCreate(() => this.refresh()),
      watcher.onDidDelete(() => this.refresh()),
    );
    for (const document of vscode.workspace.textDocuments)
      this.schedule(document);
    this.updateStatus();
  }

  private enabled(document: vscode.TextDocument): boolean {
    return (
      !this.disposed &&
      !document.isClosed &&
      supported(document) &&
      vscode.workspace.isTrusted &&
      vscode.workspace
        .getConfiguration("ctk", document.uri)
        .get("symbolNavigation", true)
    );
  }
  private schedule(document: vscode.TextDocument): void {
    if (!this.enabled(document) || this.scans.has(document)) return;
    const scan: Scan = {
      version: document.version,
      generation: this.generation,
      references: [],
      state: "queued",
    };
    this.scans.set(document, scan);
    this.updateStatus();
    scan.timer = setTimeout(() => {
      delete scan.timer;
      void this.load(document, scan);
    }, 200);
  }
  private current(document: vscode.TextDocument, scan: Scan): boolean {
    return (
      this.enabled(document) &&
      this.scans.get(document) === scan &&
      scan.version === document.version &&
      scan.generation === this.generation
    );
  }
  private async ensure(
    document: vscode.TextDocument,
  ): Promise<Scan | undefined> {
    this.schedule(document);
    const scan = this.scans.get(document);
    if (!scan) return;
    if (scan.timer) {
      clearTimeout(scan.timer);
      delete scan.timer;
      await this.load(document, scan);
    } else await scan.pending;
    return this.current(document, scan) ? scan : undefined;
  }
  private async load(document: vscode.TextDocument, scan: Scan): Promise<void> {
    if (scan.pending) return scan.pending;
    scan.pending = (async () => {
      try {
        scan.state = "scanning";
        this.updateStatus();
        const buffers: Record<string, string> = {};
        for (const item of vscode.workspace.textDocuments)
          if (supported(item) && (item.isDirty || item === document))
            buffers[item.uri.fsPath] = item.getText();
        const response = await this.request(
          document,
          { mode: "scan", file: document.uri.fsPath, buffers },
          (cancel) => {
            scan.cancel = cancel;
          },
          () => this.current(document, scan),
        );
        if (!this.current(document, scan)) return;
        const text = document.getText();
        const references = response.references ?? [];
        const wanted = new Set(
          references.flatMap((item) => [item.start, item.end]),
        );
        const offsets = new Map<number, number>();
        let byte = 0,
          utf16 = 0;
        if (wanted.has(0)) offsets.set(0, 0);
        for (const character of text) {
          byte += Buffer.byteLength(character);
          utf16 += character.length;
          if (wanted.has(byte)) offsets.set(byte, utf16);
        }
        scan.references = references.flatMap((reference) => {
          const start = offsets.get(reference.start),
            end = offsets.get(reference.end);
          if (start === undefined || end === undefined || start >= end)
            return [];
          return [
            {
              reference,
              range: new vscode.Range(
                document.positionAt(start),
                document.positionAt(end),
              ),
            },
          ];
        });
        scan.state = "ready";
        this.decorate(document);
      } catch (error) {
        if (this.current(document, scan)) {
          scan.state = "failed";
          scan.error = String(error);
          this.log(
            `Symbol navigation (${document.uri.fsPath}): ${String(error)}`,
          );
        }
      } finally {
        delete scan.cancel;
        this.updateStatus();
      }
    })();
    return scan.pending;
  }
  private decorate(document: vscode.TextDocument): void {
    const scan = this.scans.get(document);
    const ranges =
      scan &&
      this.current(document, scan) &&
      vscode.workspace
        .getConfiguration("ctk", document.uri)
        .get("symbolLinks.underline", "always") === "always"
        ? scan.references.map((item) => item.range)
        : [];
    for (const editor of vscode.window.visibleTextEditors)
      if (editor.document === document)
        editor.setDecorations(this.decoration, ranges);
  }
  private async selected(
    document: vscode.TextDocument,
    position: vscode.Position,
  ) {
    const scan = await this.ensure(document);
    if (!scan) return;
    const selected = scan.references.find(
      ({ range }) => range.contains(position) && !range.end.isEqual(position),
    );
    return selected ? { scan, ...selected } : undefined;
  }
  private updateStatus(): void {
    const document = vscode.window.activeTextEditor?.document;
    if (!document || !this.enabled(document)) {
      this.status.hide();
      return;
    }
    const scan = this.scans.get(document);
    this.status.name = "CTK symbol navigation";
    this.status.command = "ctk.navigationStatus";
    this.status.text =
      scan?.state === "failed"
        ? "$(warning) CTK links: failed"
        : scan?.state === "ready"
          ? `$(link) CTK links: ${scan.references.length}`
          : "$(loading~spin) CTK links: scanning";
    this.status.tooltip = `${document.uri.fsPath}\n${scan?.error || (scan?.state === "ready" ? "Symbol scan complete" : "Scanning native symbol bindings")}\nClick for details, retry, or compiler settings.`;
    this.status.show();
  }
  private async showStatus(): Promise<void> {
    const document = vscode.window.activeTextEditor?.document;
    if (!document) return;
    const scan = this.scans.get(document);
    const choice = await vscode.window.showQuickPick(
      [
        "Retry symbol scan",
        "Show compiler settings",
        ...(scan?.error ? ["Show scan error"] : []),
      ],
      {
        title: `Symbol navigation — ${basename(document.uri.fsPath)}`,
        placeHolder:
          scan?.error ||
          `${scan?.references.length ?? 0} links · ${scan?.state ?? "queued"}`,
      },
    );
    if (choice === "Retry symbol scan") {
      this.clear(document);
      this.schedule(document);
    }
    if (choice === "Show compiler settings") await this.compilerSettings();
    if (choice === "Show scan error")
      await vscode.window
        .showErrorMessage(scan?.error || "Unknown scan error", "Retry")
        .then((choice) => {
          if (choice === "Retry") {
            this.clear(document);
            this.schedule(document);
          }
        });
  }
  private async compilerSettings(select = false): Promise<void> {
    const active = vscode.window.activeTextEditor?.document;
    const document =
      active && supported(active) ? active : this.compilerDocument;
    if (!document || document.isClosed) {
      await vscode.window.showInformationMessage(
        "Open a C/C++ file to inspect its compiler settings.",
      );
      return;
    }
    this.compilerDocument = document;
    try {
      const response = await this.request(
        document,
        { mode: "profile", file: document.uri.fsPath },
        () => {},
        () => !this.disposed && !document.isClosed,
      );
      const profile = response.profile;
      if (!profile)
        throw new Error("The server returned no compilation profile");
      if (select) {
        if (!/\.(?:h|hh|hpp|hxx)$/i.test(document.uri.fsPath)) {
          await vscode.window.showInformationMessage(
            "Choose a header before selecting its translation unit.",
          );
          return;
        }
        const choices = [
          { label: "Automatic compiler context", file: "" },
          ...profile.translationUnits.map((file) => ({
            label: basename(file),
            description: file,
            file,
          })),
          { label: "Browse for a translation unit…", file: "browse" },
        ];
        const choice = await vscode.window.showQuickPick(choices, {
          title: `Compiler context for ${basename(document.uri.fsPath)}`,
          matchOnDescription: true,
        });
        if (!choice) return;
        let file = choice.file;
        if (file === "browse") {
          const files = await vscode.window.showOpenDialog({
            canSelectMany: false,
            filters: {
              "C/C++ translation units": ["c", "cc", "cpp", "cxx", "i", "ii"],
            },
          });
          if (!files?.[0]) return;
          file = files[0].fsPath;
        }
        const configuration = vscode.workspace.getConfiguration(
          "ctk",
          document.uri,
        );
        const values = {
          ...configuration.get<Record<string, string>>(
            "headerTranslationUnits",
            {},
          ),
        };
        if (file) values[document.uri.fsPath] = file;
        else delete values[document.uri.fsPath];
        await configuration.update(
          "headerTranslationUnits",
          values,
          vscode.workspace.getWorkspaceFolder(document.uri)
            ? vscode.ConfigurationTarget.WorkspaceFolder
            : vscode.workspace.workspaceFolders?.length
              ? vscode.ConfigurationTarget.Workspace
              : vscode.ConfigurationTarget.Global,
        );
        this.refresh();
        return;
      }
      const uri = vscode.Uri.parse(
        `ctk-compiler:/Compiler-settings-${encodeURIComponent(basename(document.uri.fsPath))}.json?source=${encodeURIComponent(document.uri.toString())}`,
      );
      this.compilerReports.set(
        uri.toString(),
        JSON.stringify(
          {
            ...profile,
            note: "These are the server-resolved effective arguments. Use CTK: Select Header Translation Unit to change a header's navigation context.",
            diagnostics: response.errors,
          },
          null,
          2,
        ),
      );
      this.compilerChanged.fire(uri);
      const output = await vscode.workspace.openTextDocument(uri);
      await vscode.window.showTextDocument(output, { preview: true });
    } catch (error) {
      await vscode.window.showErrorMessage(
        `Compiler settings: ${String(error)}`,
      );
    }
  }
  private async references(
    document: vscode.TextDocument,
    scan: Scan,
    reference: Reference,
    includeDeclaration: boolean,
    token?: vscode.CancellationToken,
  ): Promise<vscode.Location[]> {
    this.referenceCancel?.();
    const generation = ++this.referenceGeneration;
    const current = () =>
      this.current(document, scan) &&
      generation === this.referenceGeneration &&
      !token?.isCancellationRequested;
    if (!current()) return [];
    try {
      return await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: `CTK references: ${reference.name}`,
          cancellable: true,
        },
        async (progress, cancellation) => {
          const listeners: vscode.Disposable[] = [];
          try {
            const buffers = Object.fromEntries(
              vscode.workspace.textDocuments
                .filter((item) => supported(item) && item.isDirty)
                .map((item) => [item.uri.fsPath, item.getText()]),
            );
            const response = await this.request(
              document,
              {
                mode: "references",
                file: document.uri.fsPath,
                usr: reference.usr,
                name: reference.name,
                target: reference.target,
                includeDeclaration,
                buffers,
              },
              (cancel) => {
                this.referenceCancel = cancel;
                listeners.push(cancellation.onCancellationRequested(cancel));
                if (token)
                  listeners.push(token.onCancellationRequested(cancel));
                if (
                  token?.isCancellationRequested ||
                  cancellation.isCancellationRequested
                )
                  cancel();
              },
              () => current() && !cancellation.isCancellationRequested,
              (value) =>
                progress.report({
                  message: `${value.completed}/${value.total} · ${value.file}`,
                }),
            );
            if (!current() || cancellation.isCancellationRequested) return [];
            this.referenceResults.show(
              reference.name,
              response.occurrences ?? [],
              response.errors,
              response.coverage,
            );
            const locations = await Promise.all(
              (response.occurrences ?? []).map((item) => this.location(item)),
            );
            const unique = new Map(
              locations
                .filter((item) => item !== undefined)
                .map((item) => [
                  `${item.uri.toString()}:${item.range.start.line}:${item.range.start.character}`,
                  item,
                ]),
            );
            return current() ? [...unique.values()] : [];
          } catch (error) {
            if (
              cancellation.isCancellationRequested ||
              token?.isCancellationRequested
            )
              return [];
            throw error;
          } finally {
            for (const listener of listeners) listener.dispose();
            if (generation === this.referenceGeneration)
              this.referenceCancel = undefined;
          }
        },
      );
    } catch (error) {
      if (current()) {
        this.log(`References: ${String(error)}`);
        await vscode.window.showErrorMessage(
          `Reference search failed: ${String(error)}`,
        );
      }
      return [];
    }
  }
  private async definitions(
    document: vscode.TextDocument,
    scan: Scan,
    reference: Reference,
  ): Promise<vscode.Location[]> {
    try {
      const response = await this.request(
        document,
        {
          mode: "resolve",
          usr: reference.usr,
          nativeDefinition: reference.nativeDefinition,
          target: reference.target,
        },
        () => {},
        () => this.current(document, scan),
      );
      if (!this.current(document, scan)) return [];
      for (const error of response.errors)
        this.log(`Symbol definition: ${error}`);
      const targets = response.targets ?? [reference.target];
      const locations = await Promise.all(
        targets.map((target) => this.location(target)),
      );
      return this.current(document, scan)
        ? locations.filter((location) => location !== undefined)
        : [];
    } catch (error) {
      if (!this.current(document, scan)) return [];
      this.log(`Symbol definition: ${String(error)}`);
      const fallback = await this.location(reference.target);
      return this.current(document, scan) && fallback ? [fallback] : [];
    }
  }
  private async location(target: Target): Promise<vscode.Location | undefined> {
    try {
      const document = await vscode.workspace.openTextDocument(
        vscode.Uri.file(target.file),
      );
      if (target.line > document.lineCount) return;
      const line = document.lineAt(target.line - 1).text;
      const column = Buffer.from(line)
        .subarray(0, target.column - 1)
        .toString("utf8").length;
      const position = new vscode.Position(target.line - 1, column);
      return new vscode.Location(document.uri, position);
    } catch (error) {
      this.log(`Symbol target (${target.file}): ${String(error)}`);
      return;
    }
  }
  private async request(
    document: vscode.TextDocument,
    payload: Record<string, unknown>,
    own: (cancel: () => void) => void,
    current: () => boolean,
    progress?: (value: {
      file: string;
      completed: number;
      total: number;
    }) => void,
  ): Promise<Response> {
    const configuration = vscode.workspace.getConfiguration(
      "ctk",
      document.uri,
    );
    const directory =
      vscode.workspace.getWorkspaceFolder(document.uri)?.uri.fsPath ??
      dirname(document.uri.fsPath);
    const python = await findPython(
      configuration.get("pythonPath", ""),
      directory,
    );
    if (!current()) throw new Error("Symbol navigation cancelled");
    const timeoutMs = configuration.get("rpcTimeoutMs", 30000);
    const child = spawn(
      python,
      [
        "-I",
        "-B",
        "-u",
        vscode.Uri.joinPath(
          this.extensionUri,
          "console",
          "symbol_navigation.py",
        ).fsPath,
      ],
      { cwd: directory, stdio: "pipe" },
    );
    let cancelling = false;
    let killTimer: ReturnType<typeof setTimeout> | undefined;
    const cancel = () => {
      if (cancelling) return;
      cancelling = true;
      // Python's KeyboardInterrupt unwinds Client/EditorBuffers ownership.
      child.kill("SIGINT");
      killTimer = setTimeout(() => child.kill("SIGKILL"), 3000);
      killTimer.unref();
    };
    child.once("close", () => clearTimeout(killTimer));
    this.requests.add(cancel);
    own(cancel);
    try {
      return await new Promise<Response>((resolve, reject) => {
        let stdout = "",
          stderr = "";
        const timer =
          payload.mode === "references"
            ? undefined
            : setTimeout(
                () => {
                  cancel();
                  reject(new Error("Symbol navigation timed out"));
                },
                timeoutMs * 6 + 10000,
              );
        let pending = "";
        child.stdout.on("data", (data: Buffer) => {
          pending += data.toString();
          while (pending.includes("\n")) {
            const newline = pending.indexOf("\n");
            const line = pending.slice(0, newline);
            pending = pending.slice(newline + 1);
            try {
              const value = JSON.parse(line);
              if (value.progress) progress?.(value.progress);
              else stdout = line;
            } catch {
              stdout += line;
            }
          }
        });
        child.stderr.on("data", (data: Buffer) => {
          stderr = (stderr + data.toString()).slice(-8000);
        });
        child.once("error", (error) => {
          clearTimeout(timer);
          reject(error);
        });
        child.stdin.on("error", reject);
        child.once("close", (code) => {
          clearTimeout(timer);
          try {
            const response = responseSchema.parse(
              JSON.parse(pending || stdout),
            );
            if (code !== 0 || response.error)
              throw new Error(
                response.error || stderr || `Symbol scanner exited (${code})`,
              );
            resolve(response);
          } catch (error) {
            reject(error);
          }
        });
        child.stdin.end(
          JSON.stringify({
            directory,
            timeoutMs,
            endpoint: configuration.get("server", ""),
            configPath: configuration.get("configPath", ""),
            compilationDatabase: configuration.get("compilationDatabase", ""),
            compileArguments: configuration.get("compileArguments", []),
            translationUnit: configuration.get<Record<string, string>>(
              "headerTranslationUnits",
              {},
            )[document.uri.fsPath],
            ...payload,
          }),
        );
      });
    } finally {
      this.requests.delete(cancel);
    }
  }
  private clear(document: vscode.TextDocument): void {
    const scan = this.scans.get(document);
    if (!scan) return;
    clearTimeout(scan.timer);
    scan.cancel?.();
    this.scans.delete(document);
    this.decorate(document);
    this.updateStatus();
  }
  private changed(document: vscode.TextDocument): void {
    // Header overlays can affect every open TU. Ordinary source edits only
    // replace that file's scan, so typing does not reparse unrelated tabs.
    if (/\.(?:h|hh|hpp|hxx)$/i.test(document.uri.fsPath)) {
      this.refresh();
      return;
    }
    this.clear(document);
    this.schedule(document);
  }
  private refresh(): void {
    this.generation++;
    for (const cancel of this.requests) cancel();
    for (const document of this.scans.keys()) this.clear(document);
    for (const document of vscode.workspace.textDocuments)
      this.schedule(document);
  }
  dispose(): void {
    this.disposed = true;
    this.refresh();
    for (const listener of this.listeners) listener.dispose();
    this.decoration.dispose();
  }
}
