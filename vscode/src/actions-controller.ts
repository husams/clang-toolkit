import { realpath } from "node:fs/promises";
import { dirname } from "node:path";
import * as vscode from "vscode";
import { z } from "zod";
import { ActionService, type ActionSettings } from "./action-service.js";
import {
  type ActionNode,
  type ActionReport,
  actionTemplate,
  type NodeAction,
  parseNodeAction,
  resolveArguments,
  validateCatalog,
} from "./actions.js";
import { findPython } from "./console-service.js";
import type { Result } from "./model.js";

const messages = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("nodeRendered"),
    view: z.enum(["bindings", "files"]),
    nodes: z.number().int().nonnegative(),
    groups: z.number().int().nonnegative(),
  }),
  z.object({ type: z.literal("nodeChoose"), followup: z.boolean().optional() }),
  z.object({
    type: z.literal("nodeRun"),
    values: z.record(z.string(), z.string()),
  }),
  z.object({ type: z.literal("nodeSelect"), id: z.string() }),
  z.object({
    type: z.literal("nodeView"),
    view: z.enum(["bindings", "files"]),
  }),
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
  private sessionSettings: ActionSettings | undefined;
  private action?: NodeAction;
  private values: Record<string, string> = {};
  private input: Input | undefined;
  private root: Input | undefined;
  private report: ActionReport | undefined;
  private selected: ActionNode | undefined;
  private history: History[] = [];
  private error = "";
  private stale = false;
  private busy = false;
  private execution: Promise<void> | undefined;
  private mode: "bindings" | "files" = "bindings";
  private target: vscode.Uri | undefined;
  private rendered?: {
    view: "bindings" | "files";
    nodes: number;
    groups: number;
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
  ) {
    this.status.name = "CTK analysis";
    this.status.text = "$(beaker) CTK";
    this.status.tooltip =
      "Open Semantic Analysis; the native server is contacted when an action runs";
    this.status.command = "ctk.openAnalysis";
    this.status.show();
    const mark = () =>
      this.markStale(
        "Source changed; refresh analysis to parse the current files.",
      );
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
          if (contentChanges.length && CXX.test(document.uri.fsPath)) mark();
        },
      ),
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("ctk"))
          this.markStale("CTK settings changed; refresh analysis to use them.");
      }),
    );
  }
  snapshot(): unknown {
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
      results:
        this.report?.results.map((r) => ({
          ...r,
          raw: undefined,
          displayFile: vscode.workspace.asRelativePath(r.file),
        })) ?? [],
      matches: this.report?.matches,
      truncated: this.report?.truncated ?? false,
      parseCount: this.report?.parseCount ?? 0,
      selected: this.selected?.nodeId,
      running: this.busy || Boolean(this.execution),
      stale: this.stale,
      error: this.error,
      view: this.mode,
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
  async receive(raw: unknown): Promise<boolean> {
    const parsed = messages.safeParse(raw);
    if (!parsed.success) return false;
    const message = parsed.data;
    try {
      switch (message.type) {
        case "nodeRendered":
          this.rendered = {
            view: message.view,
            nodes: message.nodes,
            groups: message.groups,
          };
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
        case "nodeView":
          this.mode = message.view;
          this.changed();
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
  private async load(
    path: string,
    origin: NodeAction["origin"],
  ): Promise<NodeAction> {
    const doc = vscode.workspace.textDocuments.find(
      (d) => d.uri.fsPath === path,
    );
    const source =
      doc?.getText() ??
      Buffer.from(
        await vscode.workspace.fs.readFile(vscode.Uri.file(path)),
      ).toString("utf8");
    return parseNodeAction(path, source, origin);
  }
  async choose(target?: vscode.Uri, followup = false): Promise<void> {
    if (this.busy || this.execution) return;
    if (followup && (!this.selected || this.stale))
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
          detail: "Create a YAML action with a CTK body",
          action: undefined,
        },
      ],
      {
        title: followup
          ? `CTK · Action on ${this.selected?.name}`
          : "CTK · Select action",
        placeHolder: "Search predefined and workspace actions",
        matchOnDescription: true,
        matchOnDetail: true,
      },
    );
    if (!picked) return;
    if (!picked.action) {
      await this.create();
      return;
    }
    await this.setAction(picked.action, followup);
  }
  async setAction(action: NodeAction, followup = false): Promise<void> {
    if (this.busy || this.execution)
      throw new Error("An action is already running.");
    if (followup && (!this.selected || this.stale))
      throw new Error(
        "Select a current binding before running another action.",
      );
    if (followup && this.selected)
      this.input = {
        id: this.selected.nodeId,
        label: `${this.selected.binding}: ${this.selected.name}`,
        file: this.selected.file,
      };
    this.action = action;
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
  async create(): Promise<void> {
    if (this.busy || this.execution)
      throw new Error("An action is already running.");
    if (!vscode.workspace.isTrusted)
      throw new Error("Trust this workspace before creating actions.");
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (!folder)
      throw new Error("Open a workspace folder to create an action.");
    const name = await vscode.window.showInputBox({
      title: "CTK · Create action",
      prompt: "Unique action name",
      value: "my-action",
      validateInput: (value) =>
        /^[A-Za-z_][A-Za-z0-9_-]*$/.test(value)
          ? undefined
          : "Use letters, digits, underscores or hyphens; start with a letter.",
    });
    if (!name) return;
    const source = actionTemplate.replace("name: my-action", `name: ${name}`);
    const uri = vscode.Uri.joinPath(
      folder.uri,
      ".ctk",
      "actions",
      `${name}.ctk-action`,
    );
    const action = parseNodeAction(uri.fsPath, source);
    validateCatalog([...(await this.catalog()), action]);
    await vscode.workspace.fs.createDirectory(
      vscode.Uri.joinPath(folder.uri, ".ctk", "actions"),
    );
    const edit = new vscode.WorkspaceEdit();
    edit.createFile(uri, { overwrite: false });
    edit.insert(uri, new vscode.Position(0, 0), source);
    if (!(await vscode.workspace.applyEdit(edit)))
      throw new Error("Could not create the action file.");
    const document = await vscode.workspace.openTextDocument(uri);
    await document.save();
    await vscode.window.showTextDocument(document);
    this.action = action;
    this.values = {};
    this.changed();
    await this.reveal();
  }
  async current(document: vscode.TextDocument): Promise<void> {
    if (this.busy || this.execution)
      throw new Error("An action is already running.");
    this.action = parseNodeAction(document.uri.fsPath, document.getText());
    this.values = {};
    this.changed();
    await this.reveal();
    if (!this.action.arguments.some((a) => a.default === undefined))
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
        this.fail(error);
        this.status.text = "$(warning) CTK · action stopped";
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
    this.action = await this.load(this.action.path, this.action.origin);
    const arguments_ = resolveArguments(this.action, this.values);
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
    this.status.text = `$(loading~spin) CTK · ${this.action.title} · cancel`;
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
      const report = await this.service.run(
        this.action,
        arguments_,
        [file],
        settings,
        config.get<number>("maxResults", 2000),
        (text) => {
          this.status.tooltip = `${text} · Click to cancel`;
        },
        this.input?.id,
      );
      this.root ??= report.input;
      this.input = report.input;
      this.report = report;
      this.selected = undefined;
      this.history.push({
        report,
        action: this.action,
        values: { ...this.values },
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
    try {
      await this.service?.reset();
    } catch (error) {
      this.output.appendLine(
        `Closing unavailable action session: ${String(error)}`,
      );
    } finally {
      this.service?.dispose();
    }
    this.service = undefined;
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
  dispose(): void {
    this.service?.dispose();
    for (const disposable of this.disposables) disposable.dispose();
  }
}
