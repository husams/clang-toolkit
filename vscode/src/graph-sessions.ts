import * as vscode from "vscode";
import { z } from "zod";
import {
  type AnalysisGraph,
  type GraphKind,
  graphSchema,
} from "./graph-model.js";
import { openGraphPanel } from "./graph-panel.js";
import {
  type GraphSession,
  GraphSessionStore,
  graphUiSchema,
} from "./graph-session-store.js";

const webviewState = z.object({
  graphModel: graphSchema.optional(),
  graphs: z.record(z.string(), z.unknown()),
});
export class GraphSessions
  implements vscode.WebviewPanelSerializer, vscode.Disposable
{
  private readonly store: GraphSessionStore | undefined;
  private readonly registrations: vscode.Disposable[];
  private readonly panels = new Map<string, vscode.WebviewPanel>();
  private session: GraphSession | undefined;
  private rendered: unknown;
  private disposed = false;
  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly returned: (graph: AnalysisGraph, state: string) => void,
  ) {
    this.store = context.storageUri
      ? new GraphSessionStore(context.storageUri.fsPath, (error) =>
          this.report(error),
        )
      : undefined;
    this.registrations = [
      vscode.window.registerWebviewPanelSerializer("ctk.graph", this),
      vscode.commands.registerCommand("ctk.reopenGraph", () => this.reopen()),
    ];
  }
  private report(error: unknown): void {
    console.error("CTK graph session:", error);
    void vscode.window.showWarningMessage(
      `Unable to save or restore graph: ${String(error)}`,
    );
  }
  remember(graph: AnalysisGraph, state: string): void {
    this.session = { model: graph, uiState: state };
    void this.store
      ?.remember(this.session)
      .catch((error: unknown) => this.report(error));
  }
  snapshot() {
    return { ...this.session, rendered: this.rendered };
  }
  async open(
    graph: AnalysisGraph,
    initial: string,
    returned?: (state: string) => void,
    rendered?: (state: unknown) => void,
    panel?: vscode.WebviewPanel,
  ): Promise<vscode.WebviewPanel> {
    this.remember(graph, initial);
    this.rendered = undefined;
    const opened = await openGraphPanel(
      this.context.extensionUri,
      graph,
      initial,
      (state) => {
        this.remember(graph, state);
        if (!this.disposed) {
          if (returned) returned(state);
          else this.returned(graph, state);
        }
      },
      (state) => {
        this.rendered = state;
        rendered?.(state);
      },
      {
        ...(panel ? { panel } : {}),
        changed: (state) => this.remember(graph, state),
      },
    );
    this.panels.set(graph.key, opened);
    opened.onDidDispose(() => {
      if (this.panels.get(graph.key) === opened) this.panels.delete(graph.key);
    });
    return opened;
  }
  async reopen(kind?: GraphKind): Promise<void> {
    await this.store?.ready;
    const session = this.store?.latest(kind) ?? this.session;
    if (!session) {
      void vscode.window.showInformationMessage(
        "Open a function and choose Show Call Graph or Show CFG first.",
      );
      return;
    }
    const panel = this.panels.get(session.model.key);
    if (panel) panel.reveal();
    else await this.open(session.model, session.uiState);
  }
  async deserializeWebviewPanel(
    panel: vscode.WebviewPanel,
    state: unknown,
  ): Promise<void> {
    await this.store?.ready;
    const saved = webviewState.safeParse(state);
    let session: GraphSession | undefined;
    if (saved.success) {
      const model = saved.data.graphModel;
      if (model) {
        const ui = graphUiSchema.safeParse(saved.data.graphs[model.key]);
        if (ui.success) session = { model, uiState: JSON.stringify(ui.data) };
      }
      if (!session)
        for (const key of Object.keys(saved.data.graphs)) {
          session = this.store?.byModelKey(key);
          if (session) break;
        }
    }
    if (!session) {
      panel.webview.html =
        "<!doctype html><html><body><p>This saved graph is unavailable. Use CTK: Show Call Graph to refresh it.</p></body></html>";
      return;
    }
    await this.open(
      session.model,
      session.uiState,
      undefined,
      undefined,
      panel,
    );
  }
  async flush(): Promise<void> {
    await this.store?.flush();
  }
  dispose(): void {
    this.disposed = true;
    for (const registration of this.registrations) registration.dispose();
  }
}
