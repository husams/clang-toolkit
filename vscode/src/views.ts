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
    const completions = view.webview.asWebviewUri(
      vscode.Uri.joinPath(this.uri, "media", "argument-completion.js"),
    );
    view.webview.html = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${view.webview.cspSource}; script-src 'nonce-${nonce}';"><link rel="stylesheet" href="${css}"></head><body><main><div class="tabs" role="tablist" aria-label="Semantic Analysis"><button id="symbols-tab" role="tab" aria-controls="symbols-panel" aria-selected="true">Symbol Search</button><button id="actions-tab" role="tab" aria-controls="actions-panel" aria-selected="false" tabindex="-1">Actions</button></div>
<section id="symbols-panel" role="tabpanel" aria-labelledby="symbols-tab"><section id="fields" aria-label="Search inputs"></section>
<details id="search-options"><summary>Options</summary><select id="scope" aria-label="Search scope"><option value="file">Current C++ file</option><option value="workspace">Workspace</option></select><p id="target" class="muted"></p><fieldset id="kinds"><legend>Symbol kinds</legend><label><input type="checkbox" value="variables" checked>Variables</label><label><input type="checkbox" value="classes" checked>Classes</label><label><input type="checkbox" value="functions" checked>Functions</label></fieldset></details>
<div class="actions"><button id="run" class="primary">Search</button></div><p id="status" role="status" aria-live="polite"></p><button id="output" hidden>Open Output</button><div id="errors" role="alert"></div><section id="results" aria-label="Search matches grouped by file"></section></section>
<section id="actions-panel" role="tabpanel" aria-labelledby="actions-tab" hidden><p id="node-context" class="muted">Input: active C++ file root</p>
<div class="picker-row"><button id="node-picker" class="select" aria-label="Select action" aria-haspopup="dialog">Select action… ▾</button><button id="node-run" class="primary">Run</button></div>
<p id="node-description" class="muted"></p><details id="node-options"><summary>Options</summary><div id="node-arguments" aria-label="Action arguments"></div><button id="node-edit">Edit action</button></details>
<div class="context-tools"><button id="node-back" hidden>← Back</button><button id="node-root" hidden>File root</button><button id="node-refresh">Refresh</button><button id="node-close">Close</button></div>
<p id="node-error" role="alert"></p><div class="result-toolbar"><span id="node-count" role="status" aria-live="polite"></span><div role="group" aria-label="Result view"><button id="bindings-view" aria-pressed="true">Bindings</button><button id="files-view" aria-pressed="false">Files</button></div></div>
<div id="node-selection" hidden><p id="node-selected"></p><button id="node-followup">Run action on selected node…</button></div><section id="node-results" aria-label="Action matches"></section></section>
</main><script nonce="${nonce}" src="${completions}"></script><script nonce="${nonce}" src="${js}"></script></body></html>`;
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
