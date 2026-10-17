import { readFile, realpath } from "node:fs/promises";
import { resolve } from "node:path";
import * as vscode from "vscode";
import { compilerDiagnostics } from "./compiler-diagnostics.js";
import { sourceOffsets } from "./source-range.js";

interface Problem {
  file: string;
  uri: vscode.Uri;
  diagnostic: vscode.Diagnostic;
}
function diagnosticKey(file: string, diagnostic: vscode.Diagnostic): string {
  const { line, character } = diagnostic.range.start;
  const message = diagnostic.message
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/\s+/g, " ")
    .trim()
    .replace(/^[A-Z]/, (first) => first.toLowerCase());
  return JSON.stringify([file, line, character, diagnostic.severity, message]);
}
export class ParseProblems implements vscode.Disposable {
  private readonly collection =
    vscode.languages.createDiagnosticCollection("CTK");
  private readonly owners = new Map<string, Problem[]>();
  private readonly requests = new Map<string, object>();
  private readonly external = new Map<
    string,
    { file: string; diagnostics: vscode.Diagnostic[]; signature: string }
  >();
  private readonly listener: vscode.Disposable;
  private published = "";
  private disposed = false;

  constructor() {
    this.listener = vscode.languages.onDidChangeDiagnostics(({ uris }) => {
      if (this.disposed) return;
      for (const uri of uris) this.rememberExternal(uri);
      this.publish();
    });
    for (const [uri] of vscode.languages.getDiagnostics())
      this.rememberExternal(uri);
  }
  private rememberExternal(uri: vscode.Uri): void {
    if (uri.scheme !== "file") return;
    const diagnostics = vscode.languages
      .getDiagnostics(uri)
      .filter((item) => item.source !== "CTK");
    const key = uri.toString();
    if (!diagnostics.length) {
      this.external.delete(key);
      return;
    }
    const signature = JSON.stringify(
      diagnostics.map((item) => diagnosticKey(uri.fsPath, item)),
    );
    if (this.external.get(key)?.signature === signature) return;
    const entry = { file: uri.fsPath, diagnostics, signature };
    this.external.set(key, entry);
    void realpath(uri.fsPath)
      .catch(() => uri.fsPath)
      .then((file) => {
        if (
          this.disposed ||
          this.external.get(key) !== entry ||
          file === entry.file
        )
          return;
        entry.file = file;
        this.publish();
      });
  }

  async report(
    file: string,
    error: string,
    directory: string,
    current: () => boolean,
    document?: vscode.Uri,
  ): Promise<void> {
    if (this.disposed || !current()) return;
    const request = {};
    this.requests.set(file, request);
    const sources = new Map<
      string,
      Promise<{ file: string; text: string } | undefined>
    >();
    const source = (path: string) => {
      const absolute = resolve(directory, path);
      let pending = sources.get(absolute);
      if (!pending) {
        pending = (async () => {
          const canonical = await realpath(absolute).catch(() => absolute);
          const text = await readFile(canonical, "utf8").catch(() => undefined);
          return text === undefined ? undefined : { file: canonical, text };
        })();
        sources.set(absolute, pending);
      }
      return pending;
    };
    const located = await Promise.all(
      compilerDiagnostics(error).map(async (entry) => {
        const saved = await source(entry.file);
        if (!saved) return;
        const offsets = sourceOffsets(
          {
            file: saved.file,
            begin: { ...entry, file: saved.file, valid: true },
          },
          saved.text,
        );
        if (!offsets) return;
        const character =
          offsets.start -
          saved.text.slice(0, offsets.start).lastIndexOf("\n") -
          1;
        const point = new vscode.Position(entry.line - 1, character);
        const diagnostic = new vscode.Diagnostic(
          new vscode.Range(point, point),
          entry.message,
          vscode.DiagnosticSeverity.Error,
        );
        diagnostic.source = "CTK";
        return {
          file: saved.file,
          uri:
            saved.file === file && document
              ? document
              : vscode.Uri.file(saved.file),
          diagnostic,
        };
      }),
    );
    if (this.disposed || !current() || this.requests.get(file) !== request)
      return;
    this.owners.set(
      file,
      located.filter((problem): problem is Problem => problem !== undefined),
    );
    this.publish();
  }
  clear(file: string): void {
    this.requests.delete(file);
    this.owners.delete(file);
    if (!this.disposed) this.publish();
  }
  private publish(): void {
    const otherErrors = new Set(
      [...this.external.values()].flatMap(({ file, diagnostics }) =>
        diagnostics.map((item) => diagnosticKey(file, item)),
      ),
    );
    const files = new Map<
      string,
      { uri: vscode.Uri; diagnostics: Map<string, vscode.Diagnostic> }
    >();
    for (const problems of this.owners.values()) {
      for (const { file, uri, diagnostic } of problems) {
        const key = diagnosticKey(file, diagnostic);
        if (otherErrors.has(key)) continue;
        let group = files.get(file);
        if (!group) {
          group = { uri, diagnostics: new Map() };
          files.set(file, group);
        }
        group.diagnostics.set(key, diagnostic);
      }
    }
    const entries: [vscode.Uri, vscode.Diagnostic[]][] = [
      ...files.values(),
    ].map(({ uri, diagnostics }) => [uri, [...diagnostics.values()]]);
    const signature = JSON.stringify(
      entries.map(([uri, diagnostics]) => [
        uri.toString(),
        diagnostics.map((item) => [
          item.range.start.line,
          item.range.start.character,
          item.severity,
          item.message,
        ]),
      ]),
    );
    // Our collection also raises diagnostic events. Only write actual changes
    // so withdrawing/restoring a duplicate cannot trigger a feedback loop.
    if (signature === this.published) return;
    this.published = signature;
    // One header may be diagnosed by several retained translation units.
    // Clearing one file must not erase another file's contribution.
    this.collection.clear();
    this.collection.set(entries);
  }
  dispose(): void {
    this.disposed = true;
    this.listener.dispose();
    this.requests.clear();
    this.owners.clear();
    this.external.clear();
    this.collection.dispose();
  }
}
