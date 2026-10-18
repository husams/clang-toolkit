import { randomBytes } from "node:crypto";
import * as vscode from "vscode";
import { z } from "zod";
import type { AnalysisGraph } from "./graph-model.js";

const messages = z.discriminatedUnion("type", [
  z.object({ type: z.literal("ready") }),
  z.object({ type: z.literal("graph-close") }),
  z.object({
    type: z.literal("graph-viewstate"),
    state: z.string().max(2000000),
  }),
]);
export async function openGraphPanel(
  uri: vscode.Uri,
  graph: AnalysisGraph,
  initial: string,
  returned: (state: string) => void,
): Promise<vscode.WebviewPanel> {
  const panel = vscode.window.createWebviewPanel(
    "ctk.graph",
    `${graph.kind === "cfg" ? "CFG" : "Call Graph"}: ${graph.name}`,
    vscode.ViewColumn.Active,
    {
      enableScripts: true,
      retainContextWhenHidden: true,
      localResourceRoots: [vscode.Uri.joinPath(uri, "media")],
    },
  );
  const nonce = randomBytes(18).toString("base64");
  const media = (file: string) =>
    panel.webview.asWebviewUri(vscode.Uri.joinPath(uri, "media", file));
  panel.webview.html = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${panel.webview.cspSource}; script-src 'nonce-${nonce}' ${panel.webview.cspSource};"><link rel="stylesheet" href="${media("graph.css")}"></head><body class="graph-window"><main id="graph" class="graph-panel"></main><script nonce="${nonce}" src="${media("elk.bundled.js")}"></script><script type="module" nonce="${nonce}" src="${media("graph-only.js")}"></script></body></html>`;
  let state = initial;
  panel.webview.onDidReceiveMessage((input: unknown) => {
    const message = messages.safeParse(input);
    if (!message.success) return;
    if (message.data.type === "ready")
      void panel.webview.postMessage({
        type: "graph",
        model: graph,
        uiState: state,
      });
    if (message.data.type === "graph-viewstate") state = message.data.state;
    if (message.data.type === "graph-close") panel.dispose();
  });
  panel.onDidDispose(() => {
    returned(state);
    void vscode.commands.executeCommand("workbench.view.extension.ctkSemantic");
    void vscode.commands.executeCommand("ctk.result.focus");
  });
  await vscode.commands.executeCommand("workbench.action.closeSidebar");
  await vscode.commands.executeCommand("workbench.action.closeAuxiliaryBar");
  await vscode.commands.executeCommand("workbench.action.closePanel");
  return panel;
}
