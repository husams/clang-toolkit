import { randomBytes } from "node:crypto";
import * as vscode from "vscode";
import { z } from "zod";
import type { NodeActionTarget } from "./actions.js";
import {
  type AstEntry,
  type AstInspection,
  type AstSemantics,
  astDisplay,
  type SourceSelection,
} from "./ast-model.js";
import { InspectorTree } from "./inspector-tree.js";
import type { Result } from "./model.js";

type Load = (
  id?: string,
  selection?: SourceSelection,
) => Promise<AstInspection | undefined>;
interface Page {
  node: Result;
  children?: AstEntry[];
  nativeId?: string;
  semantics?: AstSemantics | undefined;
}
export interface InspectorState {
  current: Page | undefined;
  history: Page[];
  cache: Map<string, Page>;
  tree: InspectorTree;
  load: Load | undefined;
  prepareAction: ((id: string) => Promise<NodeActionTarget>) | undefined;
  contextId: string;
  rootLabel: string;
  tab: "ast" | "properties";
  error: string;
  notice: string;
  operation: Promise<AstInspection | undefined> | undefined;
}
const nodeMenuSchema = z.object({
  webviewSection: z.literal("ast-node"),
  ctkAstNodeId: z.string().min(1),
  ctkAstContext: z.string().min(1),
});
const messages = z.discriminatedUnion("type", [
  z.object({ type: z.literal("ready") }),
  z.object({ type: z.literal("back") }),
  z.object({ type: z.literal("root") }),
  z.object({ type: z.literal("retry") }),
  z.object({ type: z.literal("source") }),
  z.object({ type: z.literal("action") }),
  z.object({ type: z.literal("tab"), tab: z.enum(["ast", "properties"]) }),
  z.object({ type: z.literal("child"), id: z.string() }),
  z.object({ type: z.literal("properties"), id: z.string() }),
  z.object({ type: z.literal("related"), id: z.string() }),
  z.object({
    type: z.literal("expand"),
    id: z.string(),
    expanded: z.boolean(),
  }),
  z.object({
    type: z.literal("rendered"),
    nodeId: z.string(),
    kind: z.string(),
    properties: z.array(z.string()),
    children: z.array(z.string()),
    tree: z
      .array(
        z.object({
          id: z.string(),
          level: z.number().int().positive(),
          expanded: z.boolean().optional(),
          selected: z.boolean(),
          loaded: z.boolean(),
          context: nodeMenuSchema,
        }),
      )
      .max(10000),
    text: z.string().max(100000),
    tab: z.enum(["ast", "properties"]),
    panels: z.object({ ast: z.boolean(), properties: z.boolean() }),
    sections: z
      .array(z.object({ title: z.string(), open: z.boolean() }))
      .max(32),
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
  private tree = new InspectorTree();
  private treeReveal = 0;
  private retry: (() => Promise<void>) | undefined;
  private generation = 0;
  private running = false;
  private error = "";
  private notice = "";
  private rootLabel = "Selected result";
  private tab: "ast" | "properties" = "ast";
  private contextId = randomBytes(12).toString("hex");
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
    view.webview.html = `<!doctype html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${view.webview.cspSource}; script-src 'nonce-${nonce}' ${view.webview.cspSource};">
<link rel="stylesheet" href="${css}"></head><body><main>
<div class="inspector-body">
<p id="empty">Open a C++ file or select a match to inspect its AST.</p>
<section id="inspector" hidden>
<div class="inspector-toolbar"><div class="inspector-tabs" role="tablist" aria-label="AST inspector">
<button id="ast-tab" role="tab" aria-controls="ast-panel" aria-selected="true">AST</button>
<button id="properties-tab" role="tab" aria-controls="properties-panel" aria-selected="false" tabindex="-1">Properties</button></div><button id="action">Run Action</button></div>
<section id="ast-panel" class="outline" role="tabpanel" aria-labelledby="ast-tab">
<ul id="tree" role="tree" aria-label="C++ AST"></ul></section>
<section id="properties-panel" class="node-details" role="tabpanel" aria-labelledby="properties-tab" hidden><header><div class="node-title"><h2 id="name"></h2><span id="kind"></span></div></header>
<p id="signature"></p>
<details id="source-section" data-section="Source" open><summary>Source</summary><div class="section-body"><button id="location"></button><pre id="source"></pre></div></details>
<div id="semantics"></div>
<details id="properties-group" data-section="Properties" open><summary>Properties</summary><div class="section-body"><dl id="properties"></dl></div></details>
<details id="range-group" data-section="Source range" hidden><summary>Source range</summary><div class="section-body"><dl id="range"></dl></div></details>
</section></section></div></main><script type="module" nonce="${nonce}" src="${js}"></script></body></html>`;
    view.webview.onDidReceiveMessage((message: unknown) => {
      void this.receive(message).catch((error: unknown) => {
        this.error = error instanceof Error ? error.message : String(error);
        this.publish();
      });
    });
    view.onDidChangeVisibility(() => {
      if (view.visible) this.publish();
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
      semantics: this.current?.semantics,
      back: this.history.length > 0,
      running: this.running,
      canRunAction: Boolean(
        this.current?.nativeId &&
          this.prepareAction &&
          !this.error &&
          !this.notice &&
          !this.running,
      ),
      error: this.error,
      notice: this.notice,
      rootLabel: this.rootLabel,
      inspectionStatus: {
        text: this.status.text,
        tooltip: this.status.tooltip,
        command: this.status.command,
      },
      visible: this.view?.visible ?? false,
      tab: this.tab,
      contextId: this.contextId,
      treeReveal: this.treeReveal,
      tree: this.tree.rows().map(({ node, ...row }) => {
        const display = astDisplay(node);
        return {
          ...row,
          id: node.id,
          name: display.name,
          kind: display.kind,
          file: node.file ? vscode.workspace.asRelativePath(node.file) : "",
          line: node.line,
          column: node.column,
          locationValid: display.locationValid,
        };
      }),
      rendered: this.rendered,
    };
  }
  private publish(): void {
    this.status.command = undefined;
    if (this.running) {
      this.status.text = "$(loading~spin) CTK · inspecting AST";
      this.status.tooltip = "Loading the selected AST node";
      this.status.show();
    } else if (this.error || this.notice) {
      const expired =
        /cursor unavailable|cursor expired or closed|retained value has been closed/i.test(
          this.error,
        );
      this.status.text = this.error
        ? "$(warning) CTK · reload AST"
        : "$(info) CTK · no AST node";
      this.status.tooltip = expired
        ? "This analysis session expired or closed. Click to reload the file AST."
        : `${this.error || this.notice}\nClick to reload the file AST.`;
      this.status.command = "ctk.reloadFileAst";
      this.status.show();
    } else {
      this.status.hide();
    }
    void this.view?.webview.postMessage({
      type: "state",
      state: this.snapshot(),
    });
  }
  async show(
    result: Result,
    load: Load,
    prepareAction: (id: string) => Promise<NodeActionTarget>,
    options: { preserveEditor?: boolean; current?: () => boolean } = {},
  ): Promise<void> {
    const generation = ++this.generation;
    const current = options.current ?? (() => true);
    if (!current()) return;
    this.running = false;
    this.status.hide();
    this.current = { node: result };
    this.history = [];
    this.cache = new Map();
    this.tree = new InspectorTree();
    this.contextId = randomBytes(12).toString("hex");
    this.retry = undefined;
    this.load = load;
    this.prepareAction = prepareAction;
    this.error = "";
    this.notice = "";
    this.rootLabel = options.preserveEditor ? "File AST" : "Selected result";
    if (!options.preserveEditor)
      await vscode.commands.executeCommand("ctk.result.focus");
    if (generation !== this.generation || !current()) return;
    this.publish();
    await this.inspect(undefined, undefined, current, !options.preserveEditor);
  }
  async selectSource(
    selection: SourceSelection,
    current: () => boolean = () => true,
  ): Promise<void> {
    if (!this.current?.nativeId) return;
    await this.inspect(this.current.nativeId, selection, current);
  }
  private async inspect(
    id?: string,
    selection?: SourceSelection,
    selectionCurrent: () => boolean = () => true,
    revealSource = true,
    select = true,
  ): Promise<void> {
    if (!this.load || !this.current || !selectionCurrent()) return;
    const generation = ++this.generation;
    this.running = true;
    this.error = "";
    this.notice = "";
    this.status.text = "$(loading~spin) CTK · inspecting AST";
    this.status.show();
    this.publish();
    const previous = this.operation,
      load = this.load;
    const operation = (async () => {
      // Finish an earlier, superseded selection before reusing its native host.
      if (previous) await previous.catch(() => undefined);
      if (generation !== this.generation || !selectionCurrent()) return;
      return load(id, selection);
    })();
    this.operation = operation;
    try {
      const inspection = await operation;
      if (generation !== this.generation || !selectionCurrent()) return;
      if (!inspection) {
        this.tree.clearSelection();
        const location =
          selection?.start === selection?.end ? "position" : "selection";
        this.notice = `No AST node covers this ${location} in the current analysis; showing the previous node.`;
        return;
      }
      if (
        select &&
        selection &&
        this.current &&
        this.current.nativeId !== inspection.node.id
      )
        this.history.push(this.current);
      const page = {
        node: inspection.node,
        nativeId: inspection.node.id,
        children: inspection.children,
        ...(inspection.semantics ? { semantics: inspection.semantics } : {}),
      };
      this.tree.apply(page, inspection.path, select);
      for (const ancestor of inspection.path ?? [])
        this.cache.set(ancestor.node.id, {
          ...ancestor,
          nativeId: ancestor.node.id,
        });
      this.cache.set(inspection.node.id, page);
      if (select) {
        this.current = page;
        this.treeReveal++;
      }
      this.retry = undefined;
      if (select && !selection && revealSource)
        await this.openSource(page.node);
    } catch (error) {
      if (generation === this.generation && selectionCurrent()) {
        this.error = error instanceof Error ? error.message : String(error);
        this.retry = () =>
          this.inspect(id, selection, selectionCurrent, revealSource, select);
      }
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
    if (message.type === "tab") {
      this.tab = message.tab;
      this.publish();
      return;
    }
    if (message.type === "properties") {
      if (!this.tree.node(message.id))
        throw new Error("This AST node is no longer available.");
      if (this.running && this.current?.node.id !== message.id) return;
      this.tab = "properties";
      if (
        !this.running &&
        (this.current?.node.id !== message.id || !this.current.children)
      )
        await this.receive({ type: "child", id: message.id });
      this.publish();
      return;
    }
    if (this.running) return;
    if (message.type === "related") {
      if (!this.relatedNode(message.id))
        throw new Error("This base class is no longer available.");
      const previous = this.current;
      await this.inspect(message.id);
      if (
        previous &&
        this.current !== previous &&
        this.current?.nativeId === message.id
      )
        this.history.push(previous);
      this.publish();
      return;
    }
    if (message.type === "action") {
      await this.chooseAction(await this.actionTarget());
      return;
    }
    if (message.type === "source" && this.current) {
      this.notice = "";
      this.publish();
      await this.openSource(this.current.node);
      return;
    }
    if (message.type === "retry") {
      await this.retry?.();
      return;
    }
    if (message.type === "expand") {
      if (!this.tree.node(message.id))
        throw new Error("This AST branch is no longer available.");
      this.tree.expand(message.id, message.expanded);
      this.publish();
      if (message.expanded && !this.tree.loaded(message.id))
        await this.inspect(message.id, undefined, () => true, false, false);
      return;
    }
    if (message.type === "back" || message.type === "root") {
      const page =
        message.type === "root" ? this.history[0] : this.history.at(-1);
      if (!page) return;
      if (message.type === "root") this.history = [];
      else this.history.pop();
      this.current = page;
      this.tree.apply(page);
      this.treeReveal++;
      this.error = "";
      this.notice = "";
      this.publish();
      await this.openSource(page.node);
      return;
    }
    if (message.type === "child") {
      const child = this.tree.node(message.id);
      if (!child || !this.current)
        throw new Error("This AST child is no longer available.");
      if (this.current.node.id !== child.id) this.history.push(this.current);
      this.current = this.cache.get(child.id) ?? {
        node: child,
        nativeId: child.id,
      };
      this.error = "";
      this.notice = "";
      this.tree.apply(this.current);
      this.treeReveal++;
      this.publish();
      if (!this.current.children) await this.inspect(child.id);
      else await this.openSource(this.current.node);
    }
  }
  async actionTarget(): Promise<NodeActionTarget> {
    if (
      this.running ||
      this.error ||
      this.notice ||
      !this.current?.nativeId ||
      !this.prepareAction
    )
      throw new Error("Select a current AST node before choosing an action.");
    return this.prepareAction(this.current.nativeId);
  }
  async runNodeAction(input: unknown): Promise<void> {
    const context = nodeMenuSchema.parse(input);
    const current = () => {
      if (
        this.contextId !== context.ctkAstContext ||
        !this.prepareAction ||
        this.running ||
        !(
          this.tree.node(context.ctkAstNodeId) ||
          this.relatedNode(context.ctkAstNodeId)
        )
      )
        throw new Error(
          "This AST node menu is no longer current; reopen the menu.",
        );
    };
    current();
    const prepare = this.prepareAction;
    if (!prepare)
      throw new Error("Open a current file AST before choosing an action.");
    const target = await prepare(context.ctkAstNodeId);
    current();
    await this.chooseAction({
      ...target,
      activate: async () => {
        current();
        return target.activate();
      },
    });
  }
  private relatedNode(id: string): boolean {
    return (
      this.current?.semantics?.inheritance?.some(
        (base) => base.nodeId === id && !base.unresolved,
      ) ?? false
    );
  }
  save(): InspectorState {
    return {
      current: this.current,
      history: this.history,
      cache: this.cache,
      tree: this.tree,
      load: this.load,
      prepareAction: this.prepareAction,
      contextId: this.contextId,
      rootLabel: this.rootLabel,
      tab: this.tab,
      error: this.error,
      notice: this.notice,
      operation: this.operation,
    };
  }
  async restore(state: InspectorState, current: () => boolean): Promise<void> {
    const generation = ++this.generation;
    this.current = state.current;
    this.history = state.history;
    this.cache = state.cache;
    this.tree = state.tree;
    this.load = state.load;
    this.prepareAction = state.prepareAction;
    this.contextId = state.contextId;
    this.rootLabel = state.rootLabel;
    this.tab = state.tab;
    this.error = state.error;
    this.notice = state.notice;
    this.operation = undefined;
    this.running = Boolean(state.operation);
    this.retry = undefined;
    this.rendered = undefined;
    this.treeReveal++;
    this.publish();
    // A tab can be left while a native request is still finishing. Let it
    // settle before the restored tree can issue another request to that host.
    const pending = await state.operation?.catch(() => undefined);
    if (generation !== this.generation || !current()) return;
    this.running = false;
    if (pending) {
      const page = {
        node: pending.node,
        nativeId: pending.node.id,
        children: pending.children,
        ...(pending.semantics ? { semantics: pending.semantics } : {}),
      };
      this.tree.apply(page, pending.path, false);
      this.cache.set(page.node.id, page);
      if (this.current?.node.id === page.node.id) this.current = page;
    }
    if (!this.current?.nativeId) {
      const id =
        this.current && this.tree.node(this.current.node.id)
          ? this.current.node.id
          : undefined;
      await this.inspect(id, undefined, current, false);
    } else this.publish();
  }
  clear(): void {
    this.generation++;
    this.current = undefined;
    this.history = [];
    this.cache = new Map();
    this.tree = new InspectorTree();
    this.load = undefined;
    this.prepareAction = undefined;
    this.retry = undefined;
    this.operation = undefined;
    this.contextId = randomBytes(12).toString("hex");
    this.running = false;
    this.error = "";
    this.notice = "";
    this.rendered = undefined;
    this.publish();
  }
  dispose(): void {
    this.generation++;
    this.status.dispose();
  }
}
