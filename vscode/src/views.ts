import { randomBytes } from "node:crypto";
import * as vscode from "vscode";
import type { Result } from "./model.js";

export function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ] ?? character,
  );
}
export class AnalysisView implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;
  constructor(
    private readonly uri: vscode.Uri,
    private readonly receive: (message: unknown) => void,
    private readonly ready: () => void,
  ) {}
  resolveWebviewView(view: vscode.WebviewView): void {
    this.view = view;
    view.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.uri, "media")],
    };
    const nonce = randomBytes(18).toString("base64");
    const css = view.webview.asWebviewUri(
      vscode.Uri.joinPath(this.uri, "media", "sidebar.css"),
    );
    const js = view.webview.asWebviewUri(
      vscode.Uri.joinPath(this.uri, "media", "sidebar.js"),
    );
    view.webview.html = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${view.webview.cspSource}; script-src 'nonce-${nonce}';"><link rel="stylesheet" href="${css}"></head><body><main><label for="action">Analysis</label><button id="action" class="select" aria-haspopup="dialog">Find symbols ▾</button><label for="scope">Scope</label><select id="scope"><option value="file">Current C++ file</option><option value="workspace">Workspace</option></select><p id="target" class="muted"></p><section id="fields" aria-label="Analysis inputs"></section><section id="block" hidden><label for="source">Script block</label><textarea id="source" rows="5" spellcheck="false"></textarea><button id="edit">Edit in CTK editor</button></section><fieldset id="kinds"><legend>Symbol kinds</legend><label><input type="checkbox" value="variables" checked>Variables</label><label><input type="checkbox" value="classes" checked>Classes</label><label><input type="checkbox" value="functions" checked>Functions</label></fieldset><div class="actions"><button id="run" class="primary">Run Analysis</button><button id="stop" hidden>Stop</button></div><p id="status" role="status" aria-live="polite">Ready</p><button id="output" hidden>Open Output</button><div id="errors" role="alert"></div><section id="results" aria-label="Matches grouped by file"><p class="muted">Run an analysis to see matching C++ declarations.</p></section></main><script nonce="${nonce}" src="${js}"></script></body></html>`;
    view.webview.onDidReceiveMessage(this.receive);
    view.onDidChangeVisibility(() => {
      if (view.visible) this.ready();
    });
  }
  post(value: unknown): void {
    void this.view?.webview.postMessage(value);
  }
  async reveal(): Promise<void> {
    await vscode.commands.executeCommand("ctk.analysis.focus");
  }
}
export class DetailsView implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;
  private result?: Result;
  constructor(private readonly uri: vscode.Uri) {}
  resolveWebviewView(view: vscode.WebviewView): void {
    this.view = view;
    view.webview.options = {
      enableScripts: false,
      localResourceRoots: [vscode.Uri.joinPath(this.uri, "media")],
    };
    this.render();
  }
  async show(result: Result): Promise<void> {
    this.result = result;
    await vscode.commands.executeCommand("ctk.result.focus");
    this.render();
  }
  private render(): void {
    if (!this.view) return;
    const webview = this.view.webview,
      r = this.result;
    const css = webview.asWebviewUri(
      vscode.Uri.joinPath(this.uri, "media", "sidebar.css"),
    );
    webview.html = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}"><link rel="stylesheet" href="${css}"></head><body><main>${r ? `<dl><dt>Kind</dt><dd>${escapeHtml(r.kind)}</dd><dt>Name</dt><dd>${escapeHtml(r.name)}</dd><dt>Location</dt><dd>${escapeHtml(`${r.file}:${r.line}:${r.column}`)}</dd></dl><pre>${escapeHtml(r.excerpt)}</pre><details><summary>Semantic fields</summary><pre>${escapeHtml(JSON.stringify(r.raw, null, 2))}</pre></details>` : "Select a match to inspect its semantic fields."}</main></body></html>`;
  }
}
