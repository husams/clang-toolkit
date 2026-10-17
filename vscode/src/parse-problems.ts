import { readFile, realpath } from "node:fs/promises";
import { resolve } from "node:path";
import * as vscode from "vscode";
import { compilerDiagnostics } from "./compiler-diagnostics.js";
import { sourceOffsets } from "./source-range.js";

interface Problem {
  uri: vscode.Uri;
  diagnostic: vscode.Diagnostic;
}
export class ParseProblems implements vscode.Disposable {
  private readonly collection =
    vscode.languages.createDiagnosticCollection("CTK");
  private readonly owners = new Map<string, Problem[]>();
  private readonly requests = new Map<string, object>();
  private disposed = false;

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
    const files = new Map<
      string,
      { uri: vscode.Uri; diagnostics: Map<string, vscode.Diagnostic> }
    >();
    for (const problems of this.owners.values()) {
      for (const { uri, diagnostic } of problems) {
        let group = files.get(uri.toString());
        if (!group) {
          group = { uri, diagnostics: new Map() };
          files.set(uri.toString(), group);
        }
        const { line, character } = diagnostic.range.start;
        group.diagnostics.set(
          JSON.stringify([line, character, diagnostic.message]),
          diagnostic,
        );
      }
    }
    // One header may be diagnosed by several retained translation units.
    // Clearing one file must not erase another file's contribution.
    this.collection.clear();
    this.collection.set(
      [...files.values()].map(({ uri, diagnostics }) => [
        uri,
        [...diagnostics.values()],
      ]),
    );
  }
  dispose(): void {
    this.disposed = true;
    this.requests.clear();
    this.owners.clear();
    this.collection.dispose();
  }
}
