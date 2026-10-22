import { createHash, randomBytes } from "node:crypto";
import { readFile, realpath } from "node:fs/promises";
import * as vscode from "vscode";
import { z } from "zod";
import type { Result } from "./model.js";
import { sourceTarget } from "./source-range.js";

const snapshotSchema = z.object({
  title: z.string(),
  query: z.string(),
  results: z.array(
    z.object({
      id: z.string(),
      name: z.string(),
      kind: z.string(),
      file: z.string(),
      line: z.number().int().positive(),
      column: z.number().int().positive(),
      excerpt: z.string(),
      raw: z.unknown(),
      binding: z.string().optional(),
      displayFile: z.string().optional(),
      translationUnit: z.string().optional(),
    }),
  ),
  fingerprints: z.record(z.string(), z.string()),
  selected: z.number().int().nonnegative().optional(),
  scroll: z.number().nonnegative().optional(),
  expanded: z.array(z.string()).optional(),
  queryExpanded: z.boolean().optional(),
});
type Snapshot = z.infer<typeof snapshotSchema>;
const digest = (text: string) =>
  createHash("sha256").update(text).digest("hex");

export class PinnedQueries implements vscode.Disposable {
  private readonly panels = new Set<vscode.WebviewPanel>();
  private readonly serializer: vscode.Disposable;
  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly reveal: (result: Result, text: string) => Promise<void>,
  ) {
    this.serializer = vscode.window.registerWebviewPanelSerializer(
      "ctk.pinnedQuery",
      {
        deserializeWebviewPanel: async (panel, state: unknown) => {
          const snapshot = snapshotSchema.safeParse(state);
          if (snapshot.success) this.attach(panel, snapshot.data);
          else panel.dispose();
        },
      },
    );
  }
  private async text(file: string): Promise<string> {
    const canonical = await realpath(file).catch(() => file);
    for (const document of vscode.workspace.textDocuments) {
      if (document.isClosed || document.uri.scheme !== "file") continue;
      if (
        (await realpath(document.uri.fsPath).catch(
          () => document.uri.fsPath,
        )) === canonical
      )
        return document.getText();
    }
    return readFile(file, "utf8");
  }
  async pin(
    title: string,
    query: string,
    results: readonly Result[],
    current: () => boolean = () => true,
  ): Promise<void> {
    if (!results.length) {
      await vscode.window.showInformationMessage(
        "Run a query before pinning its results.",
      );
      return;
    }
    if (!current()) {
      await vscode.window.showInformationMessage(
        "Refresh the query before pinning its results.",
      );
      return;
    }
    const fingerprints: Record<string, string> = {};
    for (const result of results) {
      const file = sourceTarget(result)?.file ?? result.file;
      if (file in fingerprints) continue;
      try {
        fingerprints[file] = digest(await this.text(file));
      } catch {
        fingerprints[file] = "";
      }
    }
    if (!current()) {
      await vscode.window.showInformationMessage(
        "The query changed while pinning. Pin the completed query again.",
      );
      return;
    }
    const snapshot = snapshotSchema.parse({
      title,
      query,
      results: results.map(({ nodeId: _nodeId, ...result }) => ({
        ...result,
        displayFile: vscode.workspace.asRelativePath(result.file),
      })),
      fingerprints,
    });
    const panel = vscode.window.createWebviewPanel(
      "ctk.pinnedQuery",
      title,
      [...this.panels][0]?.viewColumn ?? vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
      },
    );
    this.attach(panel, snapshot);
  }
  private attach(panel: vscode.WebviewPanel, snapshot: Snapshot): void {
    this.panels.add(panel);
    panel.title = snapshot.title;
    panel.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "media")],
    };
    const nonce = randomBytes(18).toString("base64");
    const css = panel.webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "media", "sidebar.css"),
    );
    const script = panel.webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "media", "pinned-query.js"),
    );
    panel.webview.html = `<!doctype html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${panel.webview.cspSource}; script-src 'nonce-${nonce}'"><link rel="stylesheet" href="${css}"></head><body><main><h2 id="title"></h2><details id="query-details"><summary>Query</summary><pre id="query"></pre></details><p id="count" class="muted"></p><section id="results" aria-label="Pinned query results"></section></main><script nonce="${nonce}" src="${script}"></script></body></html>`;
    const listener = panel.webview.onDidReceiveMessage(
      async (message: unknown) => {
        const parsed = z
          .object({
            type: z.enum(["ready", "open"]),
            index: z.number().int().nonnegative().optional(),
          })
          .safeParse(message);
        if (!parsed.success) return;
        if (parsed.data.type === "ready") {
          await panel.webview.postMessage({ type: "snapshot", snapshot });
          return;
        }
        const result = snapshot.results[parsed.data.index ?? -1];
        if (!result) return;
        const file = sourceTarget(result)?.file ?? result.file;
        try {
          const text = await this.text(file);
          if (digest(text) !== snapshot.fingerprints[file])
            throw new Error(
              "Source changed since this query was pinned. Rerun the query to navigate current matches.",
            );
          await this.reveal(result, text);
        } catch (error) {
          await vscode.window.showWarningMessage(String(error));
        }
      },
    );
    panel.onDidDispose(() => {
      listener.dispose();
      this.panels.delete(panel);
    });
  }
  dispose(): void {
    for (const panel of this.panels) panel.dispose();
    this.serializer.dispose();
  }
}
