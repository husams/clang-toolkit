import { readFile } from "node:fs/promises";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import * as vscode from "vscode";
import { z } from "zod";
import { ActionsController } from "./actions-controller.js";
import { SearchAstAccess } from "./ast-access.js";
import { findPython } from "./console-service.js";
import { DetailsView } from "./details-view.js";
import { EditorSelectionSync } from "./editor-selection.js";
import { registerLanguage } from "./language.js";
import {
  type Action,
  predefined,
  type Result,
  type RunRequest,
  scriptAction,
  validateParameters,
} from "./model.js";
import { SourceHighlight } from "./source-highlight.js";
import { AnalysisView } from "./views.js";
import {
  startConsoleWorker,
  startWorker,
  type WorkerRun,
} from "./worker-client.js";

const CXX = /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i;
const EXCLUDE = "**/{.git,node_modules,build,.venv,.cache,dist}/**";
const messageSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("ready") }),
  z.object({
    type: z.literal("rendered"),
    action: z.string(),
    matches: z.number().int().nonnegative(),
    groups: z.number().int().nonnegative(),
  }),
  z.object({ type: z.literal("chooseAction") }),
  z.object({ type: z.literal("stop") }),
  z.object({ type: z.literal("showOutput") }),
  z.object({ type: z.literal("openResult"), id: z.string() }),
  z.object({
    type: z.literal("editBlock"),
    source: z.string().max(1024 * 1024),
  }),
  z.object({
    type: z.literal("run"),
    values: z.record(z.string(), z.string()),
    scope: z.enum(["file", "workspace"]),
    kinds: z.array(z.enum(["variables", "classes", "functions"])),
    source: z.string().max(1024 * 1024),
  }),
  z.object({
    type: z.literal("update"),
    values: z.record(z.string(), z.string()),
    scope: z.enum(["file", "workspace"]),
    kinds: z.array(z.enum(["variables", "classes", "functions"])),
    source: z.string().max(1024 * 1024),
  }),
]);
const custom: Action = {
  id: "custom",
  title: "Custom script block",
  description: "Edit console CTK in the script editor",
  kind: "script",
  parameters: [],
  source: 'match functionDecl(isExpansionInMainFile()).bind("symbol");',
};
export class Prototype {
  readonly view: AnalysisView;
  readonly actions: ActionsController;
  private tab: "symbols" | "actions" = "symbols";
  readonly details: DetailsView;
  private readonly searchAst: SearchAstAccess;
  private readonly sourceHighlight = new SourceHighlight();
  private readonly editorSelection: EditorSelectionSync;
  private readonly output = vscode.window.createOutputChannel("CTK Output");
  private readonly taskStatus = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    39,
  );
  private target?: vscode.Uri;
  private customDocument: vscode.TextDocument | undefined;
  private action: Action = predefined[0] ?? custom;
  private values: Record<string, string> = {};
  private kinds = ["variables", "classes", "functions"];
  private scope: "file" | "workspace" = "file";
  private results: Result[] = [];
  private errors: string[] = [];
  private consoleOutput: string[] = [];
  private status = "Ready · native server required";
  private completed = false;
  private active: WorkerRun | undefined;
  private preparing = false;
  private rendered:
    | { action: string; matches: number; groups: number }
    | undefined;
  constructor(context: vscode.ExtensionContext) {
    this.details = new DetailsView(
      context.extensionUri,
      (result) => this.openSource(result),
      (target) => this.actions.choose(undefined, true, target),
    );
    this.searchAst = new SearchAstAccess(context.extensionUri);
    this.view = new AnalysisView(
      context.extensionUri,
      (message) => {
        void this.receive(message).catch((error: unknown) => this.fail(error));
      },
      () => this.publish(),
    );
    this.actions = new ActionsController(
      context,
      () => this.publish(),
      async () => {
        this.tab = "actions";
        await this.view.reveal();
        this.publish();
      },
      (result) => this.showResult(result),
      this.output,
      (message) => this.view.post(message),
    );
    this.editorSelection = new EditorSelectionSync(
      this.sourceHighlight,
      (selection, current) => this.details.selectSource(selection, current),
      (error) => this.output.appendLine(`Source selection: ${String(error)}`),
    );
    context.subscriptions.push(
      this.output,
      this.taskStatus,
      this.actions,
      this.details,
      this.searchAst,
      this.sourceHighlight,
      this.editorSelection,
      vscode.window.registerWebviewViewProvider("ctk.analysis", this.view, {
        webviewOptions: { retainContextWhenHidden: true },
      }),
      vscode.window.registerWebviewViewProvider("ctk.result", this.details),
    );
    const remember = (editor: vscode.TextEditor | undefined): void => {
      if (
        editor?.document.uri.scheme === "file" &&
        CXX.test(editor.document.uri.fsPath)
      ) {
        this.target = editor.document.uri;
        this.publish();
      }
    };
    remember(vscode.window.activeTextEditor);
    context.subscriptions.push(
      vscode.window.onDidChangeActiveTextEditor(remember),
      vscode.workspace.onDidChangeTextDocument(({ document }) => {
        if (document === this.customDocument) this.publish();
      }),
      { dispose: () => this.active?.cancel() },
    );
  }
  snapshot(): unknown {
    return {
      tab: this.tab,
      actions: this.actions.snapshot(),
      action: this.action,
      values: this.values,
      kinds: this.kinds,
      scope: this.scope,
      target: this.target?.fsPath ?? "",
      source: this.customDocument?.getText() ?? this.action.source ?? "",
      running: this.preparing || Boolean(this.active),
      status: this.status,
      completed: this.completed,
      errors: this.errors,
      output: this.consoleOutput,
      results: this.results.map((r) => ({
        ...r,
        raw: undefined,
        displayFile: vscode.workspace.asRelativePath(r.file),
      })),
      rendered: this.rendered,
    };
  }
  completionTarget(): string | undefined {
    return this.target?.fsPath;
  }
  private publish(): void {
    if (this.active || this.preparing) {
      this.taskStatus.text = `$(loading~spin) CTK · ${this.action.kind === "script" ? "script" : "search"} · cancel`;
      this.taskStatus.command = "ctk.cancelSearch";
      this.taskStatus.show();
    } else this.taskStatus.hide();
    this.view.post({ type: "state", state: this.snapshot() });
  }
  cancelSearch(): void {
    this.active?.cancel();
  }
  private fail(error: unknown): void {
    this.errors = [error instanceof Error ? error.message : String(error)];
    this.status = this.errors[0]?.includes("cancelled")
      ? "Analysis cancelled"
      : "Analysis failed";
    this.output.appendLine(this.errors[0] ?? "Analysis failed");
    if (this.action.kind === "script") this.output.show(true);
    this.publish();
  }
  private async receive(raw: unknown): Promise<void> {
    const tab = z
      .object({ type: z.literal("tab"), tab: z.enum(["symbols", "actions"]) })
      .safeParse(raw);
    if (tab.success) {
      this.tab = tab.data.tab;
      this.publish();
      return;
    }
    if (await this.actions.receive(raw)) return;
    const message = messageSchema.parse(raw);
    switch (message.type) {
      case "ready":
        this.publish();
        return;
      case "rendered":
        this.rendered = {
          action: message.action,
          matches: message.matches,
          groups: message.groups,
        };
        return;
      case "chooseAction":
        await this.choose("all");
        return;
      case "stop":
        this.active?.cancel();
        return;
      case "showOutput":
        this.output.show(true);
        return;
      case "openResult":
        await this.openResult(message.id);
        return;
      case "editBlock":
        if (!this.customDocument || this.customDocument.isClosed)
          this.customDocument = await vscode.workspace.openTextDocument({
            language: "ctk",
            content: message.source,
          });
        await vscode.window.showTextDocument(
          this.customDocument,
          vscode.ViewColumn.One,
        );
        return;
      case "update":
      case "run":
        if (this.active || this.preparing) return;
        this.values = message.values;
        this.scope = message.scope;
        this.kinds = message.kinds;
        if (this.action.id === "custom")
          this.action = {
            ...this.action,
            source: this.customDocument?.getText() ?? message.source,
          };
        if (message.type === "run") await this.execute();
        return;
    }
  }
  async scripts(): Promise<Action[]> {
    const files = await vscode.workspace.findFiles("**/*.ctk", EXCLUDE, 500);
    const actions: Action[] = [];
    for (const uri of files) {
      try {
        const stat = await vscode.workspace.fs.stat(uri);
        if (stat.size > 1024 * 1024) continue;
        actions.push(
          scriptAction(
            uri.fsPath,
            Buffer.from(await vscode.workspace.fs.readFile(uri)).toString(
              "utf8",
            ),
          ),
        );
      } catch (error) {
        this.output.appendLine(`Cannot load ${uri.fsPath}: ${String(error)}`);
      }
    }
    return actions;
  }
  async choose(
    filter: "all" | "scripts" | "predefined",
    target?: vscode.Uri,
    run = false,
  ): Promise<void> {
    if (this.active || this.preparing) return;
    if (target?.scheme === "file" && CXX.test(target.fsPath)) {
      this.target = target;
      this.scope = "file";
    }
    const actions = [
      ...(filter !== "scripts" ? predefined : []),
      ...(filter !== "predefined" ? await this.scripts() : []),
      ...(filter === "all" ? [custom] : []),
    ];
    const picked = await vscode.window.showQuickPick(
      actions.map((action) => ({
        label: action.title,
        description: action.script
          ? vscode.workspace.asRelativePath(action.script)
          : action.id === "custom"
            ? "Custom block"
            : "Predefined",
        detail: `${action.description} · ${action.parameters.filter((p) => p.required).length} required parameters`,
        action,
      })),
      {
        title:
          filter === "scripts"
            ? "CTK · Choose Script"
            : filter === "predefined"
              ? "CTK · Choose Predefined Executable"
              : "CTK · Choose Analysis",
        placeHolder: "Search analyses or scripts",
        matchOnDescription: true,
        matchOnDetail: true,
      },
    );
    if (!picked) return;
    await this.select(picked.action, run);
  }
  private async select(action: Action, run: boolean): Promise<boolean> {
    const values: Record<string, string> = {};
    for (const p of action.parameters) {
      if (!p.required) {
        values[p.name] = p.default ?? "";
        continue;
      }
      let value: string | undefined;
      if (p.kind === "choice")
        value = await vscode.window.showQuickPick(p.choices ?? [], {
          title: `CTK · ${action.title}`,
          placeHolder: p.label,
        });
      else if (p.kind === "file" || p.kind === "folder")
        value = (
          await vscode.window.showOpenDialog({
            title: p.label,
            canSelectFiles: p.kind === "file",
            canSelectFolders: p.kind === "folder",
            canSelectMany: false,
          })
        )?.[0]?.fsPath;
      else
        value = await vscode.window.showInputBox({
          title: `CTK · ${action.title}`,
          prompt: `${p.label}${p.required ? " (required)" : " (optional)"}`,
          value: p.default ?? "",
          validateInput: (input) =>
            p.required && !input.trim() ? `${p.label} is required` : undefined,
        });
      if (value === undefined) return false;
      values[p.name] = value;
    }
    this.action = action;
    this.values = values;
    this.kinds = action.kinds ?? ["variables", "classes", "functions"];
    this.customDocument = undefined;
    this.errors = [];
    this.publish();
    await this.view.reveal();
    this.publish();
    if (action.id === "custom") {
      this.customDocument = await vscode.workspace.openTextDocument({
        language: "ctk",
        content: action.source ?? "",
      });
      await vscode.window.showTextDocument(this.customDocument);
    }
    if (run) await this.execute();
    return true;
  }
  async currentScript(): Promise<void> {
    const document = vscode.window.activeTextEditor?.document;
    if (document?.uri.fsPath.endsWith(".ctk-action")) {
      await this.actions.current(document);
      return;
    }
    if (document?.languageId !== "ctk")
      throw new Error("Open a CTK script first");
    if (
      !(await this.select(
        {
          ...scriptAction(document.uri.fsPath, document.getText()),
          ...(document.uri.scheme === "file" ? {} : { script: undefined }),
        },
        false,
      ))
    )
      return;
    this.customDocument = document;
    await this.execute();
  }
  private async targets(): Promise<{ files: string[]; directory: string }> {
    if (!vscode.workspace.isTrusted)
      throw new Error("Trust this workspace before executing CTK analyses");
    let directory =
      (this.target
        ? vscode.workspace.getWorkspaceFolder(this.target)?.uri.fsPath
        : undefined) ?? vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    directory ??= this.action.script
      ? dirname(this.action.script)
      : this.target
        ? dirname(this.target.fsPath)
        : process.cwd();
    if (this.scope === "file") {
      if (!this.target && this.action.kind === "script")
        return { files: [], directory };
      if (!this.target) {
        const candidates = await vscode.workspace.findFiles(
          "**/*.{c,cc,cpp,cxx,h,hh,hpp,hxx}",
          EXCLUDE,
          500,
        );
        const picked = await vscode.window.showQuickPick(
          candidates.map((uri) => ({
            label: vscode.workspace.asRelativePath(uri),
            uri,
          })),
          { title: "CTK · Choose Target C++ File" },
        );
        if (!picked) throw new Error("Target selection cancelled");
        this.target = picked.uri;
        directory =
          vscode.workspace.getWorkspaceFolder(this.target)?.uri.fsPath ??
          directory;
      }
      return { files: [this.target.fsPath], directory };
    }
    const maximum = vscode.workspace
      .getConfiguration("ctk")
      .get<number>("maxFiles", 200);
    const files = await vscode.workspace.findFiles(
      new vscode.RelativePattern(directory, "**/*.{c,cc,cpp,cxx,h,hh,hpp,hxx}"),
      EXCLUDE,
      maximum + 1,
    );
    if (files.length > maximum)
      throw new Error(
        `Workspace exceeds the ${maximum}-file limit. Increase ctk.maxFiles or use current-file scope.`,
      );
    if (!files.length && this.action.kind !== "script")
      throw new Error("No C++ files found in this workspace");
    return { files: files.map((uri) => uri.fsPath), directory };
  }
  async execute(override?: {
    action: Action;
    values?: Record<string, string>;
    kinds?: string[];
    scope?: "file" | "workspace";
    target?: vscode.Uri;
  }): Promise<void> {
    if (this.active || this.preparing)
      throw new Error("An analysis is already running");
    this.preparing = true;
    this.status = "Preparing analysis…";
    this.publish();
    try {
      if (override) {
        this.tab = "symbols";
        this.customDocument = undefined;
        this.action = override.action;
        this.values = override.values ?? {};
        this.kinds = override.kinds ?? override.action.kinds ?? this.kinds;
        this.scope = override.scope ?? "file";
        if (override.target) this.target = override.target;
      }
      this.values = validateParameters(this.action, this.values);
      const { files, directory } = await this.targets();
      if (this.action.script) {
        const document = vscode.workspace.textDocuments.find(
          (doc) => doc.uri.fsPath === this.action.script,
        );
        this.action = {
          ...this.action,
          source:
            document?.getText() ?? (await readFile(this.action.script, "utf8")),
        };
      } else if (
        this.customDocument &&
        !this.customDocument.isClosed &&
        this.action.kind === "script"
      ) {
        this.action = { ...this.action, source: this.customDocument.getText() };
      }
      const config = vscode.workspace.getConfiguration("ctk");
      const endpoint = config.get<string>("server", ""),
        configPath = config.get<string>("configPath", ""),
        compilationDatabase = config.get<string>("compilationDatabase", "");
      const request: RunRequest = {
        action: this.action,
        values: this.values,
        kinds: this.kinds as RunRequest["kinds"],
        files,
        directory,
        compileArguments: config.get<string[]>("compileArguments", []),
        timeoutMs: config.get<number>("rpcTimeoutMs", 30000),
        maxResults: config.get<number>("maxResults", 2000),
        ...(endpoint ? { endpoint } : {}),
        ...(configPath ? { configPath } : {}),
        ...(compilationDatabase ? { compilationDatabase } : {}),
        ...(config.get<string>("libraryDirectory", "")
          ? { libraryDirectory: config.get<string>("libraryDirectory", "") }
          : {}),
      };
      const progress = (text: string) => {
        this.taskStatus.tooltip = `${text} · Click to cancel`;
      };
      const worker =
        this.action.kind === "script"
          ? startConsoleWorker(
              fileURLToPath(
                new URL("../console/run_service.py", import.meta.url),
              ),
              await findPython(config.get<string>("pythonPath", ""), directory),
              request,
              progress,
            )
          : startWorker(
              fileURLToPath(new URL("./worker.js", import.meta.url)),
              request,
              progress,
            );
      this.active = worker;
      this.status = "Running analysis…";
      this.errors = [];
      this.completed = false;
      try {
        await this.view.reveal();
        this.publish();
        const report = await worker.completion;
        this.results = report.results;
        this.errors = report.errors;
        this.consoleOutput = report.output;
        this.completed = true;
        this.status = `${this.action.kind === "script" ? (report.errors.length ? "Script failed · " : "Script completed · ") : ""}${report.results.length} matches in ${new Set(report.results.map((r) => r.file)).size} files${report.truncated ? " · result limit reached" : ""}${report.errors.length ? ` · ${report.errors.length} errors` : ""}`;
        this.output.appendLine(`${this.action.title}: ${this.status}`);
        for (const output of report.output) this.output.appendLine(output);
        for (const error of report.errors) this.output.appendLine(error);
        if (this.action.kind === "script") this.output.show(true);
      } catch (error) {
        this.fail(error);
      } finally {
        this.active = undefined;
        this.publish();
      }
    } finally {
      this.preparing = false;
      this.publish();
    }
  }
  async openResult(id: string): Promise<void> {
    const result = this.results.find((r) => r.id === id);
    if (!result) throw new Error("This result is no longer available");
    await this.showResult(result);
  }
  private async showResult(result: Result): Promise<void> {
    const translationUnit = this.target?.fsPath ?? result.file;
    await this.openSource(result);
    let searchLoad: Awaited<ReturnType<SearchAstAccess["open"]>> | undefined;
    const actionId =
      "nodeId" in result && typeof result.nodeId === "string"
        ? result.nodeId
        : undefined;
    await this.details.show(
      result,
      async (id, selection) => {
        if (actionId)
          return selection
            ? this.actions.selectSource(id ?? actionId, selection)
            : this.actions.inspect(id ?? actionId);
        searchLoad ??= await this.searchAst.open(result, translationUnit);
        return selection && id
          ? searchLoad.selectSource(id, selection)
          : searchLoad.inspect(id);
      },
      (id) =>
        this.actions.inspectorTarget(id, actionId ? undefined : searchLoad),
    );
  }
  private async openSource(result: Result): Promise<void> {
    this.editorSelection.cancel();
    await this.sourceHighlight.reveal(result);
  }
}
export async function activate(
  context: vscode.ExtensionContext,
): Promise<Prototype> {
  const prototype = new Prototype(context);
  for (const [name, handler] of [
    ["ctk.openAnalysis", () => prototype.view.reveal()],
    [
      "ctk.runScript",
      (uri?: vscode.Uri) => prototype.choose("scripts", uri, true),
    ],
    [
      "ctk.runPredefined",
      (uri?: vscode.Uri) => prototype.choose("predefined", uri, true),
    ],
    ["ctk.runCurrentScript", () => prototype.currentScript()],
    ["ctk.cancelSearch", () => prototype.cancelSearch()],
    ["ctk.runAction", (uri?: vscode.Uri) => prototype.actions.choose(uri)],
    ["ctk.createAction", () => prototype.actions.create()],
    ["ctk.cancelAction", () => prototype.actions.cancel()],
    ["ctk.refreshActions", () => prototype.actions.refresh()],
    ["ctk.closeActions", () => prototype.actions.close()],
  ] as const)
    context.subscriptions.push(
      vscode.commands.registerCommand(name, (...args: unknown[]) =>
        Promise.resolve(
          handler(args[0] instanceof vscode.Uri ? args[0] : undefined),
        ).catch((error: unknown) =>
          vscode.window.showErrorMessage(
            error instanceof Error ? error.message : String(error),
          ),
        ),
      ),
    );
  await registerLanguage(context, () => prototype.completionTarget());
  return prototype;
}
