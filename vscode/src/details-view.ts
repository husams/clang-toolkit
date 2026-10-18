import { randomBytes } from "node:crypto";
import * as vscode from "vscode";
import { z } from "zod";
import type { NodeActionTarget } from "./actions.js";
import {
  type AstEntry,
  type AstInspection,
  type AstReference,
  type AstSemantics,
  astDisplay,
  MAX_RETAINED_NODES,
  type SourceSelection,
} from "./ast-model.js";
import type { AnalysisGraph, GraphKind, GraphLoad } from "./graph-model.js";
import { openGraphPanel } from "./graph-panel.js";
import {
  type BookmarkPage,
  type InspectorBookmark,
  rebuildTree,
} from "./inspector-bookmark.js";
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
  tab: "ast" | "properties" | "callgraph" | "cfg";
  graphLoad?: GraphLoad | undefined;
  error: string;
  notice: string;
  operation: Promise<AstInspection | undefined> | undefined;
}
export async function refreshedInspectorState(
  root: BookmarkPage,
  load: Load,
  prepareAction: (id: string) => Promise<NodeActionTarget>,
  tab: InspectorState["tab"],
  bookmark: InspectorBookmark | undefined,
  text: string,
  file: string,
  current: () => boolean,
  graphLoad?: GraphLoad,
): Promise<InspectorState | undefined> {
  const rebuilt = bookmark
    ? await rebuildTree(
        bookmark,
        root,
        async (id) => {
          const page = await load(id);
          if (!page) throw new Error("This AST node is no longer available.");
          return page;
        },
        text,
        file,
        current,
      )
    : undefined;
  if (!current()) return;
  const tree = rebuilt?.tree ?? new InspectorTree();
  if (!rebuilt) tree.apply(root);
  const page = (value: BookmarkPage): Page => ({
    ...value,
    nativeId: value.node.id,
  });
  return {
    current: page(rebuilt?.selected ?? root),
    history: [],
    cache: new Map(
      [...(rebuilt?.pages ?? new Map([[root.node.id, root]]))].map(
        ([id, value]) => [id, page(value)],
      ),
    ),
    tree,
    load,
    prepareAction,
    contextId: randomBytes(12).toString("hex"),
    rootLabel: "File AST",
    tab,
    error: "",
    notice: "",
    operation: undefined,
    graphLoad,
  };
}
const nodeMenuSchema = z.object({
  webviewSection: z.literal("ast-node"),
  ctkAstNodeId: z.string().min(1),
  ctkAstContext: z.string().min(1),
});
const graphRenderedSchema = z.object({
  type: z.literal("graph-rendered"),
  key: z.string(),
  nodeCount: z.number().int().nonnegative(),
  edgeCount: z.number().int().nonnegative(),
  visibleCount: z.number().int().nonnegative(),
  zoom: z.number().finite().positive(),
  labels: z.array(z.string()),
  trail: z.array(z.string()),
});
const messages = z.discriminatedUnion("type", [
  graphRenderedSchema,
  z.object({ type: z.literal("ready") }),
  z.object({ type: z.literal("back") }),
  z.object({ type: z.literal("root") }),
  z.object({ type: z.literal("retry") }),
  z.object({ type: z.literal("source") }),
  z.object({ type: z.literal("action") }),
  z.object({
    type: z.literal("tab"),
    tab: z.enum(["ast", "properties", "callgraph", "cfg"]),
  }),
  z.object({ type: z.literal("graph-retry") }),
  z.object({
    type: z.literal("graph-fullscreen"),
    key: z.string(),
    state: z.string().max(2000000),
  }),
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
      .max(MAX_RETAINED_NODES),
    text: z.string().max(100000),
    tab: z.enum(["ast", "properties", "callgraph", "cfg"]),
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
  private tab: InspectorState["tab"] = "ast";
  private graphLoad: GraphLoad | undefined;
  private graphData: AnalysisGraph | undefined;
  private graphRequest = "";
  private graphLoading = false;
  private graphError = "";
  private graphUiState = "";
  private graphUiRevision = 0;
  private graphPanel: vscode.WebviewPanel | undefined;
  private graphRendered: z.infer<typeof graphRenderedSchema> | undefined;
  private contextId = randomBytes(12).toString("hex");
  private rendered: z.infer<typeof messages> | undefined;
  private operation: Promise<AstInspection | undefined> | undefined;
  private readonly refreshErrors = new Map<
    string,
    { message: string; hasAst: boolean }
  >();
  private readonly status = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    38,
  );
  constructor(
    private readonly uri: vscode.Uri,
    private readonly openSource: (result: Result) => Promise<void>,
    private readonly chooseAction: (target: NodeActionTarget) => Promise<void>,
    private readonly refreshRelated: (
      reference: AstReference,
    ) => Promise<string | false | undefined> = async () => undefined,
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
    const graphCss = view.webview.asWebviewUri(
      vscode.Uri.joinPath(this.uri, "media", "graph.css"),
    );
    const elk = view.webview.asWebviewUri(
      vscode.Uri.joinPath(this.uri, "media", "elk-api.js"),
    );
    view.webview.html = `<!doctype html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${view.webview.cspSource}; script-src 'nonce-${nonce}' ${view.webview.cspSource}; worker-src blob:;">
<link rel="stylesheet" href="${css}"><link rel="stylesheet" href="${graphCss}"></head><body><main>
<div class="inspector-body">
<p id="empty">Open a C++ file or select a match to inspect its AST.</p>
<section id="inspector" hidden>
<div class="inspector-toolbar"><div class="inspector-tabs" role="tablist" aria-label="AST inspector">
<button id="ast-tab" role="tab" aria-controls="ast-panel" aria-selected="true">AST</button>
<button id="properties-tab" role="tab" aria-controls="properties-panel" aria-selected="false" tabindex="-1">Properties</button><button id="callgraph-tab" role="tab" aria-controls="callgraph-panel" aria-selected="false" tabindex="-1">Call Graph</button><button id="cfg-tab" role="tab" aria-controls="cfg-panel" aria-selected="false" tabindex="-1">CFG</button></div><button id="action">Run Action</button></div>
<section id="ast-panel" class="outline" role="tabpanel" aria-labelledby="ast-tab">
<ul id="tree" role="tree" aria-label="C++ AST"></ul></section>
<section id="properties-panel" class="node-details" role="tabpanel" aria-labelledby="properties-tab" hidden><header><div class="node-title"><h2 id="name"></h2><span id="kind"></span></div></header>
<p id="signature"></p>
<details id="source-section" data-section="Source" open><summary>Source</summary><div class="section-body"><button id="location"></button><pre id="source"></pre></div></details>
<div id="semantics"></div>
<details id="properties-group" data-section="Properties" open><summary>Properties</summary><div class="section-body"><dl id="properties"></dl></div></details>
<details id="range-group" data-section="Source range" hidden><summary>Source range</summary><div class="section-body"><dl id="range"></dl></div></details>
</section><section id="callgraph-panel" class="graph-panel" role="tabpanel" aria-labelledby="callgraph-tab" hidden></section><section id="cfg-panel" class="graph-panel" role="tabpanel" aria-labelledby="cfg-tab" hidden></section></section></div></main><script nonce="${nonce}" src="${elk}"></script><script type="module" nonce="${nonce}" src="${js}"></script></body></html>`;
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
      graph: {
        model: this.graphData,
        loading: this.graphLoading,
        error: this.graphError || this.error || this.notice,
        uiState: this.graphUiState,
        uiRevision: this.graphUiRevision,
        rendered: this.graphRendered,
      },
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
          referencedDeclaration: this.cache.get(node.id)?.semantics
            ?.referencedDeclaration,
        };
      }),
      rendered: this.rendered,
    };
  }
  private publish(): void {
    if (!this.running && (this.tab === "callgraph" || this.tab === "cfg"))
      void this.ensureGraph(this.tab);
    this.status.command = undefined;
    const refreshError =
      [...this.refreshErrors].find(
        ([file]) => file === this.current?.node.file,
      ) ?? [...this.refreshErrors].at(-1);
    if (this.running) {
      this.status.text = "$(loading~spin) CTK · inspecting AST";
      this.status.tooltip = "Loading the selected AST node";
      this.status.show();
    } else if (refreshError && (!this.error || !this.load)) {
      const [file, failure] = refreshError;
      this.status.text = "$(warning) CTK · AST refresh failed";
      this.status.tooltip = `${file}\n${failure.message}\n${failure.hasAst ? "Showing the last valid AST. " : ""}Save this file again to retry.`;
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
      this.status.text = "";
      this.status.tooltip = undefined;
      this.status.hide();
    }
    void this.view?.webview.postMessage({
      type: "state",
      state: this.snapshot(),
    });
  }
  private async ensureGraph(kind: GraphKind): Promise<void> {
    const id = this.current?.nativeId,
      load = this.graphLoad;
    if (!id || !load || !this.load || this.error || this.notice) return;
    const key = `${this.contextId}:${id}:${kind}`;
    if (this.graphRequest === key) return;
    this.graphRequest = key;
    this.graphUiState = "";
    this.graphLoading = true;
    this.graphError = "";
    this.graphData = undefined;
    this.publish();
    try {
      const graph = await load(kind, id);
      if (this.graphRequest === key) this.graphData = graph;
    } catch (error) {
      if (this.graphRequest === key)
        this.graphError =
          error instanceof Error ? error.message : String(error);
    } finally {
      if (this.graphRequest === key) {
        this.graphLoading = false;
        this.publish();
      }
    }
  }
  private async openGraphPanel(state: string): Promise<void> {
    const graph = this.graphData,
      context = this.contextId;
    if (!graph) return;
    this.graphPanel?.dispose();
    this.graphPanel = await openGraphPanel(
      this.uri,
      graph,
      state,
      (returned) => {
        if (this.contextId !== context || this.graphData?.key !== graph.key)
          return;
        this.graphUiState = returned;
        this.graphUiRevision++;
        this.publish();
      },
      (input) => {
        const parsed = graphRenderedSchema.safeParse(input);
        if (
          parsed.success &&
          this.contextId === context &&
          parsed.data.key === this.graphData?.key
        )
          this.graphRendered = parsed.data;
      },
    );
  }
  setRefreshError(file: string, error?: string, hasAst = false): void {
    if (error) this.refreshErrors.set(file, { message: error, hasAst });
    else {
      const previous = this.refreshErrors.get(file);
      if (previous && this.error === previous.message) this.error = "";
      this.refreshErrors.delete(file);
    }
    this.publish();
  }
  async refreshFile(
    result: Result,
    previous: InspectorState | undefined,
    build: (current: () => boolean) => Promise<InspectorState | undefined>,
    current: () => boolean,
  ): Promise<InspectorState | undefined> {
    if (!current()) return;
    this.graphPanel?.dispose();
    this.graphPanel = undefined;
    if (previous) this.applyState(previous);
    else {
      this.clear();
      this.current = { node: result };
      this.rootLabel = "File AST";
    }
    const generation = ++this.generation;
    const valid = () => generation === this.generation && current();
    // The displayed snapshot may outlive its native worker. Keep its facts
    // visible, but never traverse or run an action through the old handles.
    this.load = undefined;
    this.prepareAction = undefined;
    this.operation = undefined;
    this.retry = undefined;
    this.error = "";
    this.notice = "";
    this.running = true;
    this.publish();
    try {
      const state = await build(valid);
      if (!state || !valid()) return;
      state.tab = this.tab;
      await this.restore(state, current);
      return state;
    } catch (error) {
      if (!valid()) return;
      this.error = error instanceof Error ? error.message : String(error);
      throw error;
    } finally {
      if (generation === this.generation) {
        this.running = false;
        this.publish();
      }
    }
  }
  async show(
    result: Result,
    load: Load,
    prepareAction: (id: string) => Promise<NodeActionTarget>,
    options: {
      preserveEditor?: boolean;
      current?: () => boolean;
      graphLoad?: GraphLoad;
    } = {},
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
    this.graphLoad = options.graphLoad;
    this.graphRequest = "";
    this.graphData = undefined;
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
    if (message.type === "graph-rendered") {
      if (message.key === this.graphData?.key) this.graphRendered = message;
      return;
    }
    if (message.type === "rendered") {
      this.rendered = message;
      return;
    }
    if (message.type === "ready") {
      this.publish();
      return;
    }
    if (message.type === "graph-retry") {
      this.graphRequest = "";
      this.publish();
      return;
    }
    if (message.type === "graph-fullscreen") {
      if (this.graphData?.key === message.key)
        await this.openGraphPanel(message.state);
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
    if (message.type === "related") {
      if (this.running) return;
      if (!this.relatedNode(message.id))
        throw new Error("This declaration is no longer available.");
      const reference = this.reference(message.id);
      const refreshed = reference
        ? await this.refreshRelated(reference)
        : undefined;
      if (refreshed === false || !this.load) return;
      const id = refreshed ?? message.id;
      const previous = this.current;
      await this.inspect(id);
      if (
        previous &&
        this.current !== previous &&
        this.current?.nativeId === id
      )
        this.history.push(previous);
      this.publish();
      return;
    }
    if (this.running || !this.load) return;
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
      [...this.cache.values()].some(
        ({ semantics }) => semantics?.referencedDeclaration?.nodeId === id,
      ) ||
      (this.current?.semantics?.inheritance?.some(
        (base) => base.nodeId === id && !base.unresolved,
      ) ??
        false)
    );
  }
  private reference(id: string): AstReference | undefined {
    const base = this.current?.semantics?.inheritance?.find(
      (base) => base.nodeId === id,
    );
    if (base?.declaration) return base.declaration;
    for (const page of this.cache.values()) {
      const reference = page.semantics?.referencedDeclaration;
      if (reference?.nodeId === id && reference.symbol)
        return { name: reference.name, symbol: reference.symbol };
    }
    return;
  }
  save(): InspectorState {
    return {
      current: this.current,
      history: this.history,
      cache: this.cache,
      tree: this.tree,
      load: this.load,
      graphLoad: this.graphLoad,
      prepareAction: this.prepareAction,
      contextId: this.contextId,
      rootLabel: this.rootLabel,
      tab: this.tab,
      error: this.error,
      notice: this.notice,
      operation: this.operation,
    };
  }
  async rebind(
    bookmark: InspectorBookmark,
    text: string,
    file: string,
    current: () => boolean,
  ): Promise<void> {
    if (
      !this.current?.nativeId ||
      !this.current.children ||
      !this.load ||
      !this.prepareAction ||
      this.error
    )
      return;
    const generation = ++this.generation,
      load = this.load;
    const valid = () => generation === this.generation && current();
    this.running = true;
    this.publish();
    try {
      const state = await refreshedInspectorState(
        {
          node: this.current.node,
          children: this.current.children,
          semantics: this.current.semantics,
        },
        async (id) => {
          const operation = load(id);
          this.operation = operation;
          try {
            return await operation;
          } finally {
            if (this.operation === operation) this.operation = undefined;
          }
        },
        this.prepareAction,
        this.tab,
        bookmark,
        text,
        file,
        valid,
        this.graphLoad,
      );
      if (state && valid()) {
        state.tab = this.tab;
        await this.restore(state, current);
      }
    } catch (error) {
      if (valid())
        this.error = error instanceof Error ? error.message : String(error);
    } finally {
      if (valid()) {
        this.running = false;
        this.publish();
      }
    }
  }
  private applyState(state: InspectorState): void {
    this.current = state.current;
    this.history = state.history;
    this.cache = state.cache;
    this.tree = state.tree;
    this.load = state.load;
    this.graphLoad = state.graphLoad;
    this.graphRequest = "";
    this.graphData = undefined;
    this.graphLoading = false;
    this.graphError = "";
    this.prepareAction = state.prepareAction;
    this.contextId = state.contextId;
    if (this.graphPanel) {
      this.graphPanel.dispose();
      this.graphPanel = undefined;
    }
    this.rootLabel = state.rootLabel;
    this.tab = state.tab;
    this.error = state.error;
    this.notice = state.notice;
    this.operation = undefined;
    this.running = Boolean(state.operation);
    this.retry = undefined;
    this.rendered = undefined;
    this.treeReveal++;
  }
  async restore(state: InspectorState, current: () => boolean): Promise<void> {
    if (!current()) return;
    const generation = ++this.generation;
    this.applyState(state);
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
    this.graphLoad = undefined;
    this.graphRequest = "";
    this.graphData = undefined;
    this.graphLoading = false;
    this.graphError = "";
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
    this.graphPanel?.dispose();
    this.status.dispose();
  }
}
