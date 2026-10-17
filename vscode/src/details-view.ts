import { randomBytes } from "node:crypto";
import * as vscode from "vscode";
import { z } from "zod";
import type { NodeActionTarget } from "./actions.js";
import { type AstEntry, type AstInspection, astDisplay } from "./ast-model.js";
import type { Result } from "./model.js";

type Load = (id?: string) => Promise<AstInspection>;
interface Page {
  node: Result;
  children?: AstEntry[];
  nativeId?: string;
}
const messages = z.discriminatedUnion("type", [
  z.object({ type: z.literal("ready") }),
  z.object({ type: z.literal("back") }),
  z.object({ type: z.literal("root") }),
  z.object({ type: z.literal("retry") }),
  z.object({ type: z.literal("source") }),
  z.object({ type: z.literal("action") }),
  z.object({ type: z.literal("child"), id: z.string() }),
  z.object({
    type: z.literal("rendered"),
    kind: z.string(),
    properties: z.array(z.string()),
    children: z.array(z.string()),
    text: z.string().max(100000),
  }),
]);
export class DetailsView
  implements vscode.WebviewViewProvider, vscode.Disposable
{
  private view?: vscode.WebviewView;
  private current: Page | undefined;
  private history: Page[] = [];
  private load: Load | undefined;
  private prepareAction:
    | ((id: string) => Promise<NodeActionTarget>)
    | undefined;
  private cache = new Map<string, Page>();
  private generation = 0;
  private running = false;
  private error = "";
  private rendered: z.infer<typeof messages> | undefined;
  private operation: Promise<AstInspection | undefined> | undefined;
  private readonly status = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    38,
  );
  constructor(
    private readonly uri: vscode.Uri,
    private readonly openSource: (result: Result) => Promise<void>,
    private readonly chooseAction: (target: NodeActionTarget) => Promise<void>,
  ) {
    this.status.name = "CTK AST inspection";
  }
  resolveWebviewView(view: vscode.WebviewView): void {
    this.view = view;
    view.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.uri, "media")],
    };
    const nonce = randomBytes(18).toString("base64");
    const css = view.webview.asWebviewUri(
      vscode.Uri.joinPath(this.uri, "media", "inspector.css"),
    );
    const js = view.webview.asWebviewUri(
      vscode.Uri.joinPath(this.uri, "media", "inspector.js"),
    );
    view.webview.html = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${view.webview.cspSource}; script-src 'nonce-${nonce}';"><link rel="stylesheet" href="${css}"></head><body><main><p id="empty">Select a match to inspect its AST.</p><section id="inspector" hidden><nav aria-label="AST navigation"><button id="back">← Back</button><button id="root">Selected result</button></nav><header><h2 id="name"></h2><span id="kind"></span></header><p id="signature"></p><button id="location"></button><pre id="source"></pre><div id="error" role="alert"></div><button id="retry" hidden>Retry loading children</button><button id="action">Run action on this node…</button><div class="columns"><details open><summary>Properties</summary><dl id="properties"></dl></details><details open><summary>Children</summary><p id="loading" role="status" hidden>Loading AST children…</p><p id="no-children" hidden>No child nodes.</p><ul id="children"></ul></details></div><details id="range-group" hidden><summary>Source range</summary><dl id="range"></dl></details></section></main><script nonce="${nonce}" src="${js}"></script></body></html>`;
    view.webview.onDidReceiveMessage((message: unknown) => {
      void this.receive(message).catch((error: unknown) => {
        this.error = error instanceof Error ? error.message : String(error);
        this.publish();
      });
    });
    this.publish();
  }
  snapshot() {
    return {
      node: this.current
        ? {
            ...astDisplay(this.current.node, this.current.children),
            file: this.current.node.file
              ? vscode.workspace.asRelativePath(this.current.node.file)
              : "",
          }
        : undefined,
      children: this.current?.children?.map((child) => ({
        ...astDisplay(child),
        file: child.file ? vscode.workspace.asRelativePath(child.file) : "",
      })),
      back: this.history.length > 0,
      running: this.running,
      canRunAction: Boolean(
        this.current?.nativeId &&
          this.prepareAction &&
          !this.error &&
          !this.running,
      ),
      error: this.error,
      rendered: this.rendered,
    };
  }
  private publish(): void {
    void this.view?.webview.postMessage({
      type: "state",
      state: this.snapshot(),
    });
  }
  async show(
    result: Result,
    load: Load,
    prepareAction: (id: string) => Promise<NodeActionTarget>,
  ): Promise<void> {
    this.generation++;
    this.running = false;
    this.status.hide();
    this.current = { node: result };
    this.history = [];
    this.cache.clear();
    this.load = load;
    this.prepareAction = prepareAction;
    this.error = "";
    await vscode.commands.executeCommand("ctk.result.focus");
    this.publish();
    await this.inspect();
  }
  private async inspect(id?: string): Promise<void> {
    if (!this.load || !this.current) return;
    const generation = ++this.generation;
    this.running = true;
    this.error = "";
    this.status.text = "$(loading~spin) CTK · inspecting AST";
    this.status.show();
    this.publish();
    const previous = this.operation,
      load = this.load;
    const operation = (async () => {
      // Finish an earlier, superseded selection before reusing its native host.
      if (previous) await previous.catch(() => undefined);
      if (generation !== this.generation) return;
      return load(id);
    })();
    this.operation = operation;
    try {
      const inspection = await operation;
      if (!inspection || generation !== this.generation) return;
      this.current = {
        node: inspection.node,
        nativeId: inspection.node.id,
        children: inspection.children,
      };
      this.cache.set(inspection.node.id, this.current);
      await this.openSource(this.current.node);
    } catch (error) {
      if (generation === this.generation)
        this.error = error instanceof Error ? error.message : String(error);
    } finally {
      if (this.operation === operation) this.operation = undefined;
      if (generation === this.generation) {
        this.running = false;
        this.status.hide();
        this.publish();
      }
    }
  }
  async receive(input: unknown): Promise<void> {
    const message = messages.parse(input);
    if (message.type === "rendered") {
      this.rendered = message;
      return;
    }
    if (message.type === "ready") {
      this.publish();
      return;
    }
    if (this.running) return;
    if (message.type === "action") {
      await this.chooseAction(await this.actionTarget());
      return;
    }
    if (message.type === "source" && this.current) {
      await this.openSource(this.current.node);
      return;
    }
    if (message.type === "retry") {
      await this.inspect(this.current?.nativeId);
      return;
    }
    if (message.type === "back" || message.type === "root") {
      const page =
        message.type === "root" ? this.history[0] : this.history.at(-1);
      if (!page) return;
      if (message.type === "root") this.history = [];
      else this.history.pop();
      this.current = page;
      this.error = "";
      this.publish();
      await this.openSource(page.node);
      return;
    }
    if (message.type === "child") {
      const child = this.current?.children?.find(
        (node) => node.id === message.id,
      );
      if (!child || !this.current)
        throw new Error("This AST child is no longer available.");
      this.history.push(this.current);
      this.current = this.cache.get(child.id) ?? {
        node: child,
        nativeId: child.id,
      };
      this.error = "";
      this.publish();
      if (!this.current.children) await this.inspect(child.id);
      else await this.openSource(this.current.node);
    }
  }
  async actionTarget(): Promise<NodeActionTarget> {
    if (
      this.running ||
      this.error ||
      !this.current?.nativeId ||
      !this.prepareAction
    )
      throw new Error("Select a current AST node before choosing an action.");
    return this.prepareAction(this.current.nativeId);
  }
  dispose(): void {
    this.generation++;
    this.status.dispose();
  }
}
