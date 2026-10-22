import { spawn } from "node:child_process";
import { dirname } from "node:path";
import * as vscode from "vscode";
import { z } from "zod";
import { findPython } from "./console-service.js";

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
  target: targetSchema,
});
const responseSchema = z.object({
  references: z.array(referenceSchema).optional(),
  targets: z.array(targetSchema).optional(),
  errors: z.array(z.string()).default([]),
  error: z.string().optional(),
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
}
const supported = (document: vscode.TextDocument) =>
  document.uri.scheme === "file" &&
  (document.languageId === "cpp" ||
    document.languageId === "c" ||
    /\.(?:h|hh|hpp|hxx|i|ii)$/i.test(document.uri.fsPath));

/** Native references belong to one immutable editor snapshot, never to a name search. */
export class SymbolNavigation implements vscode.Disposable {
  private readonly decoration = vscode.window.createTextEditorDecorationType({
    textDecoration: "underline",
    rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
  });
  private readonly scans = new Map<vscode.TextDocument, Scan>();
  private readonly requests = new Set<() => void>();
  private readonly listeners: vscode.Disposable[];
  private generation = 0;
  private disposed = false;

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
      this.decoration,
      vscode.languages.registerDocumentLinkProvider(selector, {
        provideDocumentLinks: async (document, token) => {
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
        if (event.affectsConfiguration("ctk")) this.refresh();
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
    };
    this.scans.set(document, scan);
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
        this.decorate(document);
      } catch (error) {
        if (this.current(document, scan))
          this.log(
            `Symbol navigation (${document.uri.fsPath}): ${String(error)}`,
          );
      } finally {
        delete scan.cancel;
      }
    })();
    return scan.pending;
  }
  private decorate(document: vscode.TextDocument): void {
    const scan = this.scans.get(document);
    const ranges =
      scan && this.current(document, scan)
        ? scan.references.map((item) => item.range)
        : [];
    for (const editor of vscode.window.visibleTextEditors)
      if (editor.document === document)
        editor.setDecorations(this.decoration, ranges);
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
        const timer = setTimeout(
          () => {
            cancel();
            reject(new Error("Symbol navigation timed out"));
          },
          timeoutMs * 6 + 10000,
        );
        child.stdout.on("data", (data: Buffer) => {
          stdout += data.toString();
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
            const response = responseSchema.parse(JSON.parse(stdout));
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
  }
}
