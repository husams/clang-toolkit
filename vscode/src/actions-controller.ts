import { realpath } from "node:fs/promises";
import { dirname } from "node:path";
import * as vscode from "vscode";
import { z } from "zod";
import {
  ActionArgumentCompletion,
  type ArgumentSuggestion,
} from "./action-argument-completion.js";
import { groupActionMatches } from "./action-results.js";
import { ActionService, type ActionSettings } from "./action-service.js";
import {
  type ActionNode,
  type ActionReport,
  actionTemplate,
  type NodeAction,
  type NodeActionTarget,
  newActionName,
  parseNodeAction,
  resolveArguments,
  updatedActionValues,
  validateCatalog,
} from "./actions.js";
import type { SearchAstContext } from "./ast-access.js";
import { astDisplay, type SourceSelection } from "./ast-model.js";
import { findPython } from "./console-service.js";
import type { Result } from "./model.js";

const messages = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("nodeCompleteArgument"),
    id: z.number().int().nonnegative(),
    revision: z.string(),
    argument: z.string(),
    value: z.string().max(16384),
    cursor: z.number().int().nonnegative(),
  }),
  z.object({
    type: z.literal("nodeRendered"),
    nodes: z.number().int().nonnegative(),
    groups: z.number().int().nonnegative(),
    rows: z.array(
      z.object({
        id: z.string(),
        file: z.string(),
        expanded: z.boolean(),
        bindings: z.array(z.string()),
        nodeIds: z.array(z.string()),
      }),
    ),
    action: z.string().optional(),
    arguments: z.array(z.string()).optional(),
    values: z.record(z.string(), z.string()).optional(),
    canRun: z.boolean().optional(),
  }),
  z.object({
    type: z.literal("nodeArguments"),
    revision: z.string(),
    values: z.record(z.string(), z.string()),
  }),
  z.object({ type: z.literal("nodeChoose"), followup: z.boolean().optional() }),
  z.object({
    type: z.literal("nodeRun"),
    values: z.record(z.string(), z.string()),
  }),
  z.object({ type: z.literal("nodeSelect"), id: z.string() }),
  z.object({ type: z.literal("nodeRoot") }),
  z.object({ type: z.literal("nodeBack") }),
  z.object({ type: z.literal("nodeRefresh") }),
  z.object({ type: z.literal("nodeClose") }),
  z.object({ type: z.literal("nodeEdit") }),
]);
type Input = ActionReport["input"];
interface History {
  report: ActionReport;
  action: NodeAction;
  values: Record<string, string>;
  input: Input;
}
const CXX = /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i;
const EXCLUDE = "**/{.git,node_modules,build,.venv,.cache,dist}/**";
export class ActionsController implements vscode.Disposable {
  private service: ActionService | undefined;
  private sharedSession = false;
  private releaseSessionCallbacks: (() => void) | undefined;
  private sessionSettings: ActionSettings | undefined;
  private action?: NodeAction;
  private values: Record<string, string> = {};
  private input: Input | undefined;
  private root: Input | undefined;
  private report: ActionReport | undefined;
  private selected: ActionNode | undefined;
  private history: History[] = [];
  private error = "";
  private definitionError = "";
  private definitionGeneration = 0;
  private argumentCompletion: ActionArgumentCompletion | undefined;
  private stale = false;
  private busy = false;
  private execution: Promise<void> | undefined;
  private target: vscode.Uri | undefined;
  private rendered?: {
    nodes: number;
    groups: number;
    rows: {
      id: string;
      file: string;
      expanded: boolean;
      bindings: string[];
      nodeIds: string[];
    }[];
    action: string | undefined;
    arguments: string[] | undefined;
    values: Record<string, string> | undefined;
    canRun: boolean | undefined;
  };
  private readonly status = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    40,
  );
  private readonly disposables: vscode.Disposable[] = [];
  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly changed: () => void,
    private readonly reveal: () => Promise<void>,
    private readonly show: (result: Result) => Promise<void>,
    private readonly output: vscode.OutputChannel,
    private readonly send: (message: unknown) => void,
  ) {
    this.status.name = "CTK analysis";
    this.status.text = "$(beaker) CTK";
    this.status.tooltip =
      "Open Semantic Analysis; the native server is contacted when an action runs";
    this.status.command = "ctk.openAnalysis";
    this.status.show();
    const mark = () => {
      this.argumentCompletion?.invalidate();
      this.markStale(
        "Source changed; refresh analysis to parse the current files.",
      );
    };
    const watcher = vscode.workspace.createFileSystemWatcher(
      "**/*.{c,cc,cpp,cxx,h,hh,hpp,hxx}",
    );
    const remember = (editor: vscode.TextEditor | undefined): void => {
      if (
        !this.root &&
        !this.busy &&
        editor?.document.uri.scheme === "file" &&
        CXX.test(editor.document.uri.fsPath)
      )
        this.target = editor.document.uri;
    };
    remember(vscode.window.activeTextEditor);
    this.disposables.push(
      vscode.window.onDidChangeActiveTextEditor(remember),
      this.status,
      watcher,
      watcher.onDidChange(mark),
      watcher.onDidDelete(mark),
      vscode.workspace.onDidChangeTextDocument(
        ({ document, contentChanges }) => {
          if (!contentChanges.length) return;
          if (CXX.test(document.uri.fsPath)) mark();
          this.documentChanged(document);
        },
      ),
      vscode.workspace.onDidCloseTextDocument((document) => {
        void this.reloadDefinition(document.uri);
      }),
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("ctk")) {
          this.argumentCompletion?.dispose();
          this.argumentCompletion = undefined;
          this.markStale("CTK settings changed; refresh analysis to use them.");
        }
      }),
    );
  }
  snapshot(): unknown {
    const display = (r: ActionNode) => ({
      ...r,
      raw: undefined,
      displayFile: vscode.workspace.asRelativePath(r.file),
    });
    const results = this.report?.results.map(display) ?? [];
    const matchFiles = groupActionMatches(this.report?.results ?? []).map(
      (file) => ({
        file: file.file,
        matches: file.matches.map((row) => ({
          id: row.id,
          anchor: display(row.anchor),
          bindings: row.bindings.map(display),
        })),
      }),
    );
    return {
      action: this.action
        ? { ...this.action, body: undefined, generated: undefined }
        : undefined,
      values: this.values,
      target: this.target
        ? vscode.workspace.asRelativePath(this.target)
        : undefined,
      input: this.input
        ? {
            ...this.input,
            label: this.input.label,
            file: vscode.workspace.asRelativePath(this.input.file),
          }
        : undefined,
      results,
      matchFiles,
      matches: this.report?.matches,
      truncated: this.report?.truncated ?? false,
      parseCount: this.report?.parseCount ?? 0,
      selected: this.selected?.nodeId,
      running: this.busy || Boolean(this.execution),
      stale: this.stale,
      error: this.definitionError || this.error,
      invalidAction: Boolean(this.definitionError),
      back: this.history.length > 1,
      root: Boolean(this.root && this.input?.id !== this.root.id),
      completed: Boolean(this.report),
      rendered: this.rendered,
    };
  }
  private markStale(reason: string): void {
    if (!this.service) return;
    this.stale = true;
    this.error = reason;
    this.status.text = "$(warning) CTK · refresh";
    this.changed();
  }
  private fail(error: unknown): void {
    this.error = error instanceof Error ? error.message : String(error);
    this.output.appendLine(this.error);
    this.changed();
  }
  private updateDefinition(action: NodeAction): void {
    const previous =
      this.action?.path === action.path ? this.action : undefined;
    this.values = updatedActionValues(
      previous,
      previous ? this.values : {},
      action,
    );
    this.action = action;
    this.definitionError = "";
    if (!this.stale) this.error = "";
  }
  private documentChanged(document: vscode.TextDocument): void {
    if (document.uri.fsPath !== this.action?.path) return;
    this.definitionGeneration++;
    try {
      this.updateDefinition(
        parseNodeAction(
          this.action.path,
          document.getText(),
          this.action.origin,
        ),
      );
    } catch {
      this.definitionError =
        "Action definition is incomplete or invalid; finish editing its YAML header and CTK body.";
    }
    this.changed();
  }
  private async reloadDefinition(uri: vscode.Uri): Promise<void> {
    const action = this.action;
    if (uri.fsPath !== action?.path) return;
    const generation = ++this.definitionGeneration;
    try {
      const next = await this.load(action.path, action.origin);
      if (
        generation !== this.definitionGeneration ||
        this.action?.path !== action.path
      )
        return;
      this.updateDefinition(next);
    } catch {
      if (
        generation !== this.definitionGeneration ||
        this.action?.path !== action.path
      )
        return;
      this.definitionError =
        "Cannot read the action definition; reopen or select another action.";
    }
    this.changed();
  }
  async receive(raw: unknown): Promise<boolean> {
    const parsed = messages.safeParse(raw);
    if (!parsed.success) return false;
    const message = parsed.data;
    try {
      switch (message.type) {
        case "nodeCompleteArgument": {
          let items: ArgumentSuggestion[] = [],
            error = "";
          try {
            if (message.revision === this.action?.revision)
              items = await this.completeArgument(
                message.argument,
                message.value,
                message.cursor,
              );
          } catch (failure) {
            error =
              failure instanceof Error ? failure.message : String(failure);
            this.output.appendLine(`Argument autocomplete: ${error}`);
          }
          if (message.revision === this.action?.revision)
            this.send({
              ...message,
              type: "nodeArgumentCompletions",
              items,
              error,
            });
          break;
        }
        case "nodeRendered":
          this.rendered = {
            nodes: message.nodes,
            groups: message.groups,
            rows: message.rows,
            action: message.action,
            arguments: message.arguments,
            values: message.values,
            canRun: message.canRun,
          };
          break;
        case "nodeArguments":
          if (message.revision === this.action?.revision)
            this.values = message.values;
          break;
        case "nodeChoose":
          await this.choose(undefined, Boolean(message.followup));
          break;
        case "nodeRun":
          await this.run(undefined, message.values);
          break;
        case "nodeSelect":
          await this.select(message.id);
          break;
        case "nodeRoot":
          if (this.root && !this.busy) {
            this.input = this.root;
            this.selected = undefined;
            this.changed();
          }
          break;
        case "nodeBack":
          this.back();
          break;
        case "nodeRefresh":
          await this.refresh();
          break;
        case "nodeClose":
          await this.close();
          break;
        case "nodeEdit":
          if (this.action)
            await vscode.window.showTextDocument(
              await vscode.workspace.openTextDocument(
                vscode.Uri.file(this.action.path),
              ),
            );
          break;
      }
    } catch (error) {
      this.fail(error);
    }
    return true;
  }
  async catalog(): Promise<NodeAction[]> {
    const bundled = vscode.Uri.joinPath(this.context.extensionUri, "actions");
    const files: (readonly [vscode.Uri, NodeAction["origin"]])[] = (
      await vscode.workspace.fs.readDirectory(bundled)
    )
      .filter(([name]) => name.endsWith(".ctk-action"))
      .map(
        ([name]) => [vscode.Uri.joinPath(bundled, name), "Predefined"] as const,
      );
    for (const uri of await vscode.workspace.findFiles(
      "**/*.ctk-action",
      EXCLUDE,
      501,
    )) {
      if (uri.fsPath.startsWith(`${bundled.fsPath}/`)) continue;
      files.push([uri, "Workspace"]);
    }
    if (files.filter(([, origin]) => origin === "Workspace").length > 500)
      throw new Error(
        "Too many action files; keep at most 500 workspace actions.",
      );
    const actions: NodeAction[] = [];
    for (const [uri, origin] of files) {
      try {
        actions.push(await this.load(uri.fsPath, origin));
      } catch (error) {
        this.output.appendLine(String(error));
        this.error = `Cannot load ${vscode.workspace.asRelativePath(uri)}; see CTK Output.`;
      }
    }
    return validateCatalog(actions);
  }
  async completeArgument(
    name: string,
    value: string,
    cursor = value.length,
  ): Promise<ArgumentSuggestion[]> {
    if (
      !this.action ||
      this.definitionError ||
      this.busy ||
      !vscode.workspace.isTrusted
    )
      return [];
    if (cursor < 0 || cursor > value.length) return [];
    const file = this.root?.file ?? this.target?.fsPath;
    const settings =
      this.sessionSettings ?? this.settings(file ?? this.action.path);
    const config = vscode.workspace.getConfiguration("ctk");
    if (!this.argumentCompletion) {
      const python = await findPython(
        config.get<string>("pythonPath", ""),
        settings.directory,
      );
      this.argumentCompletion ??= new ActionArgumentCompletion(
        vscode.Uri.joinPath(this.context.extensionUri, "dist/worker.js").fsPath,
        vscode.Uri.joinPath(
          this.context.extensionUri,
          "console/editor_service.py",
        ).fsPath,
        python,
        (text) => this.output.appendLine(text),
      );
    }
    return this.argumentCompletion.complete(this.action, name, value, cursor, {
      ...settings,
      file,
      cppDirty: vscode.workspace.textDocuments.some(
        (document) => document.isDirty && CXX.test(document.uri.fsPath),
      ),
      maximum: config.get<number>("maxResults", 2000),
    });
  }
  private async load(
    path: string,
    origin: NodeAction["origin"],
  ): Promise<NodeAction> {
    const doc = vscode.workspace.textDocuments.find(
      (d) => !d.isClosed && d.uri.fsPath === path,
    );
    const source =
      doc?.getText() ??
      Buffer.from(
        await vscode.workspace.fs.readFile(vscode.Uri.file(path)),
      ).toString("utf8");
    return parseNodeAction(path, source, origin);
  }
  async choose(
    target?: vscode.Uri,
    followup = false,
    node?: NodeActionTarget,
  ): Promise<void> {
    if (this.busy || this.execution) return;
    if (followup && !node && (!this.selected || this.stale))
      throw new Error(
        "Select a current binding before running another action.",
      );
    if (target) {
      if (this.root && this.root.file !== target.fsPath) await this.close();
      this.target = target;
    }
    const actions = await this.catalog();
    const items = actions.map((action) => ({
      label: action.title,
      description: action.origin,
      detail: action.description,
      action,
    }));
    const picked = await vscode.window.showQuickPick(
      [
        ...items,
        {
          label: "$(add) Create action…",
          description: "Workspace",
          detail: "Open a new custom action script in the editor",
          action: undefined,
        },
      ],
      {
        title: followup
          ? `CTK · Action on ${node?.name ?? this.selected?.name}`
          : "CTK · Select action",
        placeHolder: "Search predefined and workspace actions",
        matchOnDescription: true,
        matchOnDetail: true,
      },
    );
    if (!picked) return;
    if (!picked.action) {
      await this.create(followup, node);
      return;
    }
    await this.setAction(picked.action, followup, node);
  }
  async setAction(
    action: NodeAction,
    followup = false,
    node?: NodeActionTarget,
  ): Promise<void> {
    if (this.busy || this.execution)
      throw new Error("An action is already running.");
    if (followup && !node && (!this.selected || this.stale))
      throw new Error(
        "Select a current binding before running another action.",
      );
    if (node) {
      this.input = await node.activate();
      this.selected = undefined;
    } else if (followup && this.selected)
      this.input = {
        id: this.selected.nodeId,
        label: `${this.selected.binding}: ${this.selected.name}`,
        file: this.selected.file,
      };
    this.action = action;
    this.definitionGeneration++;
    this.definitionError = "";
    this.values = Object.fromEntries(
      this.action.arguments
        .filter((a) => a.default !== undefined)
        .map((a) => [a.name, String(a.default)]),
    );
    this.error = "";
    this.changed();
    await this.reveal();
    this.changed();
  }
  async create(followup = false, node?: NodeActionTarget): Promise<void> {
    if (this.busy || this.execution)
      throw new Error("An action is already running.");
    if (!vscode.workspace.isTrusted)
      throw new Error("Trust this workspace before creating actions.");
    if (followup && !node && (!this.selected || this.stale))
      throw new Error(
        "Select a current binding before creating a follow-up action.",
      );
    const inputFile = node?.file ?? this.input?.file ?? this.target?.fsPath;
    const folder =
      (inputFile
        ? vscode.workspace.getWorkspaceFolder(vscode.Uri.file(inputFile))
        : undefined) ?? vscode.workspace.workspaceFolders?.[0];
    if (!folder)
      throw new Error("Open a workspace folder to create an action.");
    const catalog = await this.catalog();
    const directory = vscode.Uri.joinPath(folder.uri, ".ctk", "actions");
    await vscode.workspace.fs.createDirectory(directory);
    const files = await vscode.workspace.fs.readDirectory(directory);
    const name = newActionName(
      catalog,
      files.map(([name]) => name),
    );
    const source = actionTemplate.replace("name: my-action", `name: ${name}`);
    const uri = vscode.Uri.joinPath(directory, `${name}.ctk-action`);
    const action = parseNodeAction(uri.fsPath, source);
    validateCatalog([...catalog, action]);
    const edit = new vscode.WorkspaceEdit();
    edit.createFile(uri, { overwrite: false });
    edit.insert(uri, new vscode.Position(0, 0), source);
    if (!(await vscode.workspace.applyEdit(edit)))
      throw new Error("Could not create the action file.");
    const document = await vscode.workspace.openTextDocument(uri);
    if (!(await document.save()))
      throw new Error("Could not save the action file.");
    await this.setAction(action, followup, node);
    await vscode.window.showTextDocument(document, { preview: false });
  }
  async current(document: vscode.TextDocument): Promise<void> {
    if (this.busy || this.execution)
      throw new Error("An action is already running.");
    this.definitionGeneration++;
    const action = parseNodeAction(document.uri.fsPath, document.getText());
    this.updateDefinition(action);
    this.changed();
    await this.reveal();
    if (!action.arguments.some((a) => a.default === undefined))
      await this.run();
  }
  private settings(file: string): ActionSettings {
    const config = vscode.workspace.getConfiguration("ctk");
    return {
      directory:
        vscode.workspace.getWorkspaceFolder(vscode.Uri.file(file))?.uri
          .fsPath ?? dirname(file),
      compileArguments: config.get<string[]>("compileArguments", []),
      timeoutMs: config.get<number>("rpcTimeoutMs", 30000),
      ...Object.fromEntries(
        [
          ["endpoint", "server"],
          ["configPath", "configPath"],
          ["compilationDatabase", "compilationDatabase"],
          ["libraryDirectory", "libraryDirectory"],
        ].flatMap(([key, setting]) => {
          const value = config.get<string>(setting ?? "", "");
          return value ? [[key, value]] : [];
        }),
      ),
    };
  }
  run(
    action?: NodeAction,
    values?: Record<string, string>,
    target?: vscode.Uri,
  ): Promise<void> {
    if (this.execution)
      return Promise.reject(new Error("An action is already running."));
    const execution = this.executeAction(action, values, target);
    this.execution = execution;
    this.changed();
    return execution
      .catch((error: unknown) => {
        if (!this.stale) this.fail(error);
        this.status.text = this.stale
          ? "$(warning) CTK · refresh"
          : "$(warning) CTK · action stopped";
        throw error;
      })
      .finally(() => {
        this.execution = undefined;
        this.changed();
      });
  }
  private async executeAction(
    action?: NodeAction,
    values?: Record<string, string>,
    target?: vscode.Uri,
  ): Promise<void> {
    if (this.busy) throw new Error("An action is already running.");
    if (!vscode.workspace.isTrusted)
      throw new Error("Trust this workspace before executing actions.");
    if (this.stale)
      throw new Error("Refresh analysis before using stale nodes.");
    if (target) {
      if (this.root && this.root.file !== target.fsPath) await this.close();
      this.target = target;
    }
    if (action) this.action = action;
    if (values) this.values = values;
    if (!this.action) throw new Error("Select an action first.");
    const currentAction = await this.load(this.action.path, this.action.origin);
    this.updateDefinition(currentAction);
    const currentValues = { ...this.values };
    const arguments_ = resolveArguments(currentAction, currentValues);
    let file = this.root?.file ?? this.target?.fsPath;
    const active = vscode.window.activeTextEditor?.document;
    if (!file && active?.uri.scheme === "file" && CXX.test(active.uri.fsPath))
      file = active.uri.fsPath;
    if (!file)
      file = (
        await vscode.window.showOpenDialog({
          title: "CTK · Select a C++ file to parse",
          canSelectMany: false,
          filters: { "C/C++": ["c", "cc", "cpp", "cxx", "h", "hpp"] },
        })
      )?.[0]?.fsPath;
    if (!file) return;
    const canonical = await realpath(file);
    this.target = vscode.Uri.file(canonical);
    const dirty = await Promise.all(
      vscode.workspace.textDocuments
        .filter(
          (d) => d.isDirty && d.uri.scheme === "file" && CXX.test(d.uri.fsPath),
        )
        .map((d) => realpath(d.uri.fsPath).catch(() => d.uri.fsPath)),
    );
    if (dirty.includes(canonical))
      throw new Error("Save the C++ file before parsing it.");
    const settings = this.sessionSettings ?? this.settings(file),
      config = vscode.workspace.getConfiguration("ctk");
    this.busy = true;
    this.error = "";
    this.changed();
    this.status.command = "ctk.cancelAction";
    this.status.text = `$(loading~spin) CTK · ${currentAction.title} · cancel`;
    this.status.tooltip = "Running action; click to cancel";
    try {
      this.sessionSettings = settings;
      this.service ??= new ActionService(
        vscode.Uri.joinPath(
          this.context.extensionUri,
          "console",
          "action_service.py",
        ).fsPath,
        await findPython(
          config.get<string>("pythonPath", ""),
          settings.directory,
        ),
        (reason) => this.markStale(reason),
        (text) => this.output.appendLine(text),
      );
      const response = await this.service.run(
        currentAction,
        arguments_,
        [file],
        settings,
        config.get<number>("maxResults", 2000),
        (text) => {
          this.status.tooltip = `${text} · Click to cancel`;
        },
        this.input?.id,
      );
      const report = {
        ...response,
        input:
          this.input?.id === response.input.id
            ? { ...response.input, label: this.input.label }
            : response.input,
      };
      this.root ??= report.input;
      this.input = report.input;
      this.report = report;
      this.selected = undefined;
      this.history.push({
        report,
        action: currentAction,
        values: currentValues,
        input: report.input,
      });
      for (const text of report.output) this.output.appendLine(text);
    } finally {
      this.busy = false;
      this.status.command = "ctk.openAnalysis";
      this.status.text = this.stale
        ? "$(warning) CTK · refresh"
        : this.error
          ? "$(warning) CTK · action stopped"
          : "$(check) CTK · connected";
      this.status.tooltip =
        this.error ||
        "Native server connected; parsed nodes retained for follow-up actions";
      this.changed();
    }
  }
  async select(id: string): Promise<void> {
    const selected = this.report?.results.find((r) => r.nodeId === id);
    if (!selected) throw new Error("This binding is no longer available.");
    this.selected = selected;
    this.changed();
    await this.show(selected);
  }
  async inspect(id: string) {
    return this.inspectNative((service, settings) =>
      service.inspect(settings, id),
    );
  }
  async selectSource(id: string, selection: SourceSelection) {
    return this.inspectNative((service, settings) =>
      service.selectSource(settings, id, selection),
    );
  }
  private async inspectNative<T>(
    operation: (service: ActionService, settings: ActionSettings) => Promise<T>,
  ): Promise<T> {
    if (this.busy || this.execution)
      throw new Error("Wait for the current action before inspecting its AST.");
    if (this.stale)
      throw new Error(
        "Source changed; refresh analysis before navigating AST nodes.",
      );
    if (!this.service || !this.sessionSettings)
      throw new Error(
        "This AST context has closed; refresh analysis and select a new result.",
      );
    this.busy = true;
    this.changed();
    try {
      return await operation(this.service, this.sessionSettings);
    } finally {
      this.busy = false;
      this.changed();
    }
  }
  async inspectorTarget(
    id: string,
    source?: SearchAstContext,
  ): Promise<NodeActionTarget> {
    const inspected = await (source ? source.inspect(id) : this.inspect(id));
    const display = astDisplay(inspected.node);
    return {
      name: display.name,
      file: inspected.root.file,
      activate: async () => {
        if (this.busy || this.execution)
          throw new Error("An action is already running.");
        if (!vscode.workspace.isTrusted)
          throw new Error("Trust this workspace before executing actions.");
        if (source) {
          // Validate the exact child before transferring its owning native worker.
          await source.inspect(id);
          const session = source.session();
          if (this.service !== session.service) {
            await this.refresh();
            source.transfer();
            this.service = session.service;
            this.sharedSession = session.retained;
            this.sessionSettings = session.settings;
            this.root = session.root;
            this.target = vscode.Uri.file(session.root.file);
            this.releaseSessionCallbacks = this.service.subscribe(
              (reason) => this.markStale(reason),
              (text) => this.output.appendLine(text),
            );
          }
        }
        const current = await this.inspect(id);
        return {
          id,
          file: current.root.file,
          label:
            display.kind === display.name
              ? display.kind
              : `${display.kind}: ${display.name}`,
        };
      },
    };
  }
  private back(): void {
    if (this.busy || this.history.length < 2) return;
    this.history.pop();
    const entry = this.history.at(-1);
    if (!entry) return;
    this.report = entry.report;
    this.action = entry.action;
    this.values = { ...entry.values };
    this.input = entry.input;
    this.selected = undefined;
    this.changed();
  }
  cancel(): void {
    this.service?.cancel();
  }
  async refresh(): Promise<void> {
    if (this.busy || this.execution)
      throw new Error(
        "Cancel the running action before refreshing or closing analysis.",
      );
    if (this.root) this.target = vscode.Uri.file(this.root.file);
    try {
      if (!this.sharedSession) await this.service?.reset();
    } catch (error) {
      this.output.appendLine(
        `Closing unavailable action session: ${String(error)}`,
      );
    } finally {
      if (!this.sharedSession) this.service?.dispose();
      this.releaseSessionCallbacks?.();
      this.releaseSessionCallbacks = undefined;
    }
    this.service = undefined;
    this.sharedSession = false;
    this.sessionSettings = undefined;
    this.root = undefined;
    this.input = undefined;
    this.report = undefined;
    this.selected = undefined;
    this.history = [];
    this.stale = false;
    this.error = "";
    this.status.text = "$(beaker) CTK · ready";
    this.changed();
  }
  async close(): Promise<void> {
    await this.refresh();
    this.target = undefined;
  }
  get sourceFile(): string | undefined {
    return this.root?.file;
  }
  get sourceService(): ActionService | undefined {
    return this.service;
  }
  get sourceContext(): string | undefined {
    return this.root?.id;
  }
  async closeFile(
    file: string,
    expectedContext = this.root?.id,
  ): Promise<void> {
    const root = this.root;
    if (!root || root.id !== expectedContext) return;
    if (
      (await realpath(root.file).catch(() => root.file)) !== file ||
      this.root !== root
    )
      return;
    const service = this.service;
    this.cancel();
    service?.dispose();
    await this.execution?.catch(() => undefined);
    const deadline = Date.now() + 5000;
    while (this.busy && Date.now() < deadline)
      await new Promise((done) => setTimeout(done, 20));
    if (this.service === service) await this.close();
  }
  dispose(): void {
    this.definitionGeneration++;
    if (!this.sharedSession) this.service?.dispose();
    this.releaseSessionCallbacks?.();
    this.argumentCompletion?.dispose();
    for (const disposable of this.disposables) disposable.dispose();
  }
}
