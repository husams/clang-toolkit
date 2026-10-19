import { realpath, stat } from "node:fs/promises";
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
  type ActionSourceContext,
  isRelevantActionSource,
  pathIsWithin,
  selectActionTargets,
} from "./action-targets.js";
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
    type: z.literal("nodeScope"),
    scope: z.enum(["file", "directory", "workspace"]),
  }),
  z.object({ type: z.literal("nodeChooseDirectory") }),
  z.object({
    type: z.literal("nodeRun"),
    values: z.record(z.string(), z.string()),
  }),
  z.object({ type: z.literal("nodeSelect"), id: z.string() }),
  z.object({ type: z.literal("nodeRoot") }),
  z.object({ type: z.literal("nodeBack") }),
  z.object({
    type: z.literal("nodePage"),
    direction: z.enum(["first", "previous", "next", "last"]),
  }),
  z.object({ type: z.literal("nodeOpenResults") }),
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
  root: Input | undefined;
  scope: ActionScope;
  directoryTarget: vscode.Uri | undefined;
  target: vscode.Uri | undefined;
}
const CXX = /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i;
const EXCLUDE =
  "**/{.git,.hg,.svn,node_modules,build,.venv,.cache,dist,out,target,.vscode-test}/**";
type ActionScope = "file" | "directory" | "workspace";
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
  private scope: ActionScope = "file";
  private directoryTarget: vscode.Uri | undefined;
  private readonly resolvedNodes = new Map<string, string>();
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
    const mark = (uri?: vscode.Uri) => {
      if (
        uri &&
        !isRelevantActionSource(uri.fsPath, this.sourceChangeContext())
      )
        return;
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
      watcher.onDidCreate(mark),
      watcher.onDidDelete(mark),
      vscode.workspace.onDidChangeTextDocument(
        ({ document, contentChanges }) => {
          if (!contentChanges.length) return;
          if (
            isRelevantActionSource(
              document.uri.fsPath,
              this.sourceChangeContext(),
            )
          )
            mark();
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
      scope: this.scope,
      directoryTarget: this.directoryTarget
        ? vscode.workspace.asRelativePath(this.directoryTarget)
        : undefined,
      batch: this.report?.batch ?? false,
      files: this.report?.files ?? 0,
      errors: this.report?.errors ?? [],
      totalMatches: this.report?.totalMatches ?? this.report?.matches ?? 0,
      pageOffset: this.report?.pageOffset ?? 0,
      pageSize: this.report?.pageSize ?? this.report?.results.length ?? 0,
      hasMore: this.report?.hasMore ?? false,
      complete: this.report?.complete ?? true,
      coverageComplete: this.report?.coverageComplete ?? true,
      cancelled: this.report?.cancelled ?? false,
      completedFiles: this.report?.completedFiles,
      failedFiles: this.report?.failedFiles,
      attemptedFiles: this.report?.attemptedFiles,
      unattemptedFiles: this.report?.unattemptedFiles ?? 0,
      fileStatuses: this.report?.fileStatuses ?? [],
      resultHandle: this.report?.resultHandle,
      resultFile: this.report?.resultFile,
      resultIndexFile: this.report?.resultIndexFile,
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
  private sourceChangeContext(): ActionSourceContext {
    return {
      scope: this.scope,
      workspaceRoots: (vscode.workspace.workspaceFolders ?? []).map(
        (folder) => folder.uri.fsPath,
      ),
      ...(this.target ? { target: this.target.fsPath } : {}),
      ...(this.directoryTarget
        ? { directoryTarget: this.directoryTarget.fsPath }
        : {}),
    };
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
        case "nodeScope":
          await this.setScope(message.scope);
          break;
        case "nodeChooseDirectory":
          await this.chooseDirectory();
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
            this.scope = "file";
            this.directoryTarget = undefined;
            this.target = vscode.Uri.file(this.root.file);
            this.changed();
          }
          break;
        case "nodeBack":
          this.back();
          break;
        case "nodePage":
          await this.changeResultsPage(message.direction);
          break;
        case "nodeOpenResults":
          await this.openCompleteResults();
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
  private async setScope(
    scope: ActionScope,
    directory?: vscode.Uri,
  ): Promise<void> {
    if (this.busy || this.execution) return;
    const nextDirectory = directory ?? this.directoryTarget;
    const changed =
      scope !== this.scope ||
      (directory && directory.fsPath !== this.directoryTarget?.fsPath);
    if (!changed) return;
    if (this.service || this.report) await this.refresh();
    this.scope = scope;
    if (directory) this.directoryTarget = directory;
    if (scope === "directory" && !nextDirectory) await this.chooseDirectory();
    if (scope === "workspace") this.directoryTarget = undefined;
    this.error = "";
    this.changed();
  }
  private async chooseDirectory(): Promise<void> {
    if (this.busy || this.execution) return;
    const defaultUri =
      this.directoryTarget ??
      (this.target ? vscode.Uri.file(dirname(this.target.fsPath)) : undefined);
    const selected = await vscode.window.showOpenDialog({
      title: "CTK · Choose action directory",
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      ...(defaultUri ? { defaultUri } : {}),
    });
    if (!selected?.[0]) return;
    await this.setScope("directory", selected[0]);
    this.changed();
  }
  private async discover(
    scope: ActionScope,
    file: string,
  ): Promise<{ files: string[]; roots: string[]; batch: boolean }> {
    if (scope === "file") return { files: [file], roots: [file], batch: false };
    const folders =
      scope === "workspace"
        ? (vscode.workspace.workspaceFolders ?? []).map((folder) => folder.uri)
        : this.directoryTarget
          ? [this.directoryTarget]
          : [];
    if (!folders.length)
      throw new Error(
        scope === "workspace"
          ? "Open a workspace folder before running a workspace action."
          : "Choose a directory for this action scope.",
      );
    const config = vscode.workspace.getConfiguration("ctk");
    const maximum = config.get<number>("maxFiles", 1000);
    const candidates = new Set<string>();
    for (const folder of folders) {
      const exclude = new vscode.RelativePattern(folder, EXCLUDE);
      let found = await vscode.workspace.findFiles(
        new vscode.RelativePattern(folder, "**/*.{c,cc,cpp,cxx}"),
        exclude,
        maximum + 1,
      );
      if (!found.length)
        found = await vscode.workspace.findFiles(
          new vscode.RelativePattern(folder, "**/*.{h,hh,hpp,hxx}"),
          exclude,
          maximum + 1,
        );
      for (const uri of found) candidates.add(uri.fsPath);
      if (candidates.size > maximum) break;
    }
    const manifest = selectActionTargets(
      [...candidates],
      maximum,
      folders.map((folder) => folder.fsPath),
    );
    if (!manifest.files.length)
      throw new Error(
        "No C++ translation units or headers were found in this action scope.",
      );
    return {
      files: manifest.files,
      roots: folders.map((folder) => folder.fsPath),
      batch: true,
    };
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
      const stat = await vscode.workspace.fs.stat(target);
      if (stat.type & vscode.FileType.Directory) {
        await this.setScope("directory", target);
      } else {
        if (
          this.target?.fsPath !== target.fsPath &&
          (this.service || this.report)
        )
          await this.refresh();
        if (this.root && this.root.file !== target.fsPath) await this.close();
        await this.setScope("file");
        this.target = target;
      }
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
    } else if (followup && this.selected) {
      const selected = this.selected;
      if (selected.detached) {
        const inspection = await this.inspect(selected.nodeId);
        this.root = inspection.root;
        this.target = vscode.Uri.file(inspection.root.file);
        this.input = {
          id: inspection.node.id,
          label: `${selected.binding}: ${selected.name}`,
          file: inspection.root.file,
        };
      } else {
        this.input = {
          id: selected.nodeId,
          label: `${selected.binding}: ${selected.name}`,
          file: selected.file,
        };
      }
    }
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
    const config = vscode.workspace.getConfiguration(
      "ctk",
      vscode.Uri.file(file),
    );
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
    resumeManifest?: string,
  ): Promise<void> {
    if (this.execution)
      return Promise.reject(new Error("An action is already running."));
    const execution = this.executeAction(
      action,
      values,
      target,
      resumeManifest,
    );
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
    resumeManifest?: string,
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
    if (
      this.scope === "file" &&
      !file &&
      active?.uri.scheme === "file" &&
      CXX.test(active.uri.fsPath)
    )
      file = active.uri.fsPath;
    if (this.scope === "directory") file = this.directoryTarget?.fsPath;
    if (this.scope === "workspace")
      file = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!file && this.scope === "file")
      file = (
        await vscode.window.showOpenDialog({
          title: "CTK · Select a C++ file to parse",
          canSelectMany: false,
          filters: { "C/C++": ["c", "cc", "cpp", "cxx", "h", "hpp"] },
        })
      )?.[0]?.fsPath;
    if (!file) {
      if (this.scope === "workspace")
        throw new Error(
          "Open a workspace folder before running a workspace action.",
        );
      if (this.scope === "directory")
        throw new Error("Choose a directory for this action scope.");
      return;
    }
    const scopeAnchor = await realpath(file);
    if (this.scope === "file") this.target = vscode.Uri.file(scopeAnchor);
    const settings =
      this.scope === "file" && this.sessionSettings
        ? this.sessionSettings
        : this.settings(file);
    const config = vscode.workspace.getConfiguration("ctk");
    const followsNode = Boolean(
      this.input?.id && this.root?.id && this.input.id !== this.root.id,
    );
    const discovered = followsNode
      ? {
          files: [this.input?.file ?? scopeAnchor],
          roots: [this.input?.file ?? scopeAnchor],
          batch: false,
        }
      : await this.discover(this.scope, scopeAnchor);
    const files = await Promise.all(
      discovered.files.map((path) => realpath(path)),
    );
    const roots = await Promise.all(
      discovered.roots.map((path) => realpath(path).catch(() => path)),
    );
    const dirty = await Promise.all(
      vscode.workspace.textDocuments
        .filter(
          (document) =>
            document.isDirty &&
            document.uri.scheme === "file" &&
            CXX.test(document.uri.fsPath),
        )
        .map(async (document) => ({
          file: await realpath(document.uri.fsPath).catch(
            () => document.uri.fsPath,
          ),
          text: document.getText(),
        })),
    );
    const headerRoots = await Promise.all(
      discovered.roots.map(async (root) => {
        const projectRoot =
          vscode.workspace.getWorkspaceFolder(vscode.Uri.file(root))?.uri
            .fsPath ?? root;
        return realpath(projectRoot).catch(() => projectRoot);
      }),
    );
    const changedDraft = dirty.find(
      (draft) =>
        (this.scope === "file"
          ? draft.file === scopeAnchor
          : (/\.(?:h|hh|hpp|hxx)$/i.test(draft.file) &&
              pathIsWithin(draft.file, headerRoots)) ||
            pathIsWithin(draft.file, roots)) &&
        settings.buffers?.[draft.file] !== draft.text,
    );
    if (changedDraft)
      throw new Error(
        `Save the C++ file before parsing it: ${vscode.workspace.asRelativePath(changedDraft.file)}.`,
      );
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
      const inputId =
        followsNode || (this.input?.id && this.root?.id === this.input.id)
          ? this.input?.id
          : undefined;
      const profiles = discovered.batch
        ? Object.fromEntries(
            files.map((path, index) => {
              // Keep the URI-discovered spelling for VS Code resource-scoped
              // settings and workspace lookup; `path` remains the canonical
              // key sent to the backend.
              const resourcePath = discovered.files[index] ?? path;
              const fileSettings = this.settings(resourcePath);
              const directory =
                this.scope === "directory"
                  ? scopeAnchor
                  : (vscode.workspace.getWorkspaceFolder(
                      vscode.Uri.file(resourcePath),
                    )?.uri.fsPath ?? dirname(resourcePath));
              return [
                path,
                {
                  directory,
                  compileArguments: fileSettings.compileArguments,
                  ...(fileSettings.compilationDatabase
                    ? { compilationDatabase: fileSettings.compilationDatabase }
                    : {}),
                },
              ];
            }),
          )
        : undefined;
      const response = await this.service.run(
        currentAction,
        arguments_,
        files,
        settings,
        config.get<number>("maxResults", 2000),
        (text) => {
          this.status.tooltip = `${text} · Click to cancel`;
        },
        inputId,
        discovered.batch && !followsNode,
        profiles,
        resumeManifest,
      );
      const report = {
        ...response,
        matches: response.totalMatches ?? response.matches,
        totalMatches: response.totalMatches ?? response.matches,
        pageOffset: response.pageOffset ?? 0,
        pageSize: response.pageSize ?? response.results.length,
        hasMore: response.hasMore ?? false,
        complete: response.complete ?? true,
        coverageComplete: response.coverageComplete ?? true,
        cancelled: response.cancelled ?? false,
        attemptedFiles: response.attemptedFiles ?? response.completedFiles ?? 0,
        unattemptedFiles: response.unattemptedFiles ?? 0,
        fileStatuses: response.fileStatuses ?? [],
        input:
          this.input?.id === response.input.id
            ? { ...response.input, label: this.input.label }
            : response.input,
      };
      if (!report.batch) this.root ??= report.input;
      this.input = report.input;
      this.report = report;
      this.resolvedNodes.clear();
      this.selected = undefined;
      this.history.push({
        report,
        action: currentAction,
        values: currentValues,
        input: report.input,
        root: this.root,
        scope: this.scope,
        directoryTarget: this.directoryTarget,
        target: this.target,
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
        (this.report?.batch
          ? "Open a match to inspect its AST or run another action"
          : "Native server connected; parsed nodes retained for follow-up actions");
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
  private async changeResultsPage(
    direction: "first" | "previous" | "next" | "last",
  ): Promise<void> {
    const report = this.report;
    const service = this.service;
    const resultHandle = report?.resultHandle;
    const pageSize = report?.pageSize ?? 0;
    const offset = report?.pageOffset ?? 0;
    if (!report || !service || !resultHandle || pageSize < 1 || this.busy)
      return;
    const lastOffset =
      Math.floor(
        Math.max(0, (report.totalMatches ?? report.matches) - 1) / pageSize,
      ) * pageSize;
    const nextOffset =
      direction === "first"
        ? 0
        : direction === "last"
          ? lastOffset
          : direction === "next"
            ? offset + pageSize
            : Math.max(0, offset - pageSize);
    if (nextOffset === offset || (direction === "next" && !report.hasMore))
      return;
    const settings = this.sessionSettings ?? this.settings(report.input.file);
    this.busy = true;
    this.error = "";
    this.changed();
    try {
      const page = await service.pageActionResults(
        settings,
        resultHandle,
        nextOffset,
        pageSize,
      );
      this.report = {
        ...report,
        results: page.results,
        matches: page.totalMatches,
        totalMatches: page.totalMatches,
        pageOffset: page.offset,
        pageSize: page.limit,
        hasMore: page.hasMore,
        complete: page.complete,
      };
      this.selected = undefined;
    } finally {
      this.busy = false;
      this.changed();
    }
  }
  private async openCompleteResults(): Promise<void> {
    const file = this.report?.resultFile;
    if (!file) throw new Error("This action has no complete results file.");
    const fileInfo = await stat(file);
    const document =
      !file.endsWith(".gz") && fileInfo.size <= 32 * 1024 * 1024
        ? await vscode.workspace.openTextDocument(vscode.Uri.file(file))
        : this.report?.resultIndexFile
          ? await vscode.workspace.openTextDocument(
              vscode.Uri.file(this.report.resultIndexFile),
            )
          : await vscode.workspace.openTextDocument({
              language: "markdown",
              content: [
                "# Complete action results",
                "",
                `The full JSONL result file is ${(fileInfo.size / (1024 * 1024)).toFixed(1)} MiB, so it was not loaded into the editor.`,
                "",
                `- Matches: ${this.report?.totalMatches ?? this.report?.matches ?? 0}`,
                `- Completed files: ${this.report?.completedFiles ?? "unknown"}`,
                `- Failed files: ${this.report?.failedFiles ?? "unknown"}`,
                `- Full result file: [${file}](${vscode.Uri.file(file).toString()})`,
              ].join("\n"),
            });
    await vscode.window.showTextDocument(document, { preview: false });
  }
  async inspect(id: string) {
    return this.inspectNative(async (service, settings) => {
      const result = this.report?.results.find((item) => item.nodeId === id);
      if (result?.detached) {
        if (!result.translationUnit)
          throw new Error(
            "Detached result has no translation unit for AST lookup.",
          );
        const inspection = await service.inspect(settings, {
          translationUnit: result.translationUnit,
          result: this.asResult(result),
        });
        this.resolvedNodes.set(id, inspection.node.id);
        return inspection;
      }
      return service.inspect(settings, this.resolvedNodes.get(id) ?? id);
    });
  }
  async graph(id: string, kind: import("./graph-model.js").GraphKind) {
    return this.inspectNative(async (service, settings) =>
      service.graph(
        settings,
        await this.retainedNodeId(service, settings, id),
        kind,
      ),
    );
  }
  async selectSource(id: string, selection: SourceSelection) {
    return this.inspectNative(async (service, settings) =>
      service.selectSource(
        settings,
        await this.retainedNodeId(service, settings, id),
        selection,
      ),
    );
  }
  private asResult(result: ActionNode): Result {
    return {
      id: result.id,
      nodeId: result.nodeId,
      translationUnit: result.translationUnit,
      name: result.name,
      kind: result.kind,
      file: result.file,
      line: result.line,
      column: result.column,
      excerpt: result.excerpt,
      raw: result.raw,
    };
  }
  private async retainedNodeId(
    service: ActionService,
    settings: ActionSettings,
    id: string,
  ): Promise<string> {
    const existing = this.resolvedNodes.get(id);
    if (existing) return existing;
    const result = this.report?.results.find((item) => item.nodeId === id);
    if (!result?.detached) return id;
    if (!result.translationUnit)
      throw new Error(
        "Detached result has no translation unit for AST lookup.",
      );
    const inspection = await service.inspect(settings, {
      translationUnit: result.translationUnit,
      result: this.asResult(result),
    });
    this.resolvedNodes.set(id, inspection.node.id);
    return inspection.node.id;
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
        this.root = current.root;
        this.target = vscode.Uri.file(current.root.file);
        return {
          id: this.resolvedNodes.get(id) ?? id,
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
    this.root = entry.root;
    this.scope = entry.scope;
    this.directoryTarget = entry.directoryTarget;
    this.target = entry.target;
    this.selected = undefined;
    this.resolvedNodes.clear();
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
    this.resolvedNodes.clear();
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
    return this.root?.file ?? this.input?.file;
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
