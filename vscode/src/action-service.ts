import { type ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { z } from "zod";
import {
  type ActionReport,
  type ArgumentValue,
  actionReportSchema,
  actionResultSchema,
  type NodeAction,
} from "./actions.js";
import {
  type AstInspection,
  type AstReference,
  astDisplay,
  astInspectionSchema,
  astReferenceSchema,
  nativeKind,
  type SourceSelection,
  sourceSelectionSchema,
} from "./ast-model.js";
import {
  type AnalysisGraph,
  type GraphKind,
  graphSchema,
} from "./graph-model.js";
import {
  type Result,
  type RunReport,
  type RunRequest,
  reportSchema,
} from "./model.js";

export type ActionSettings = Pick<
  RunRequest,
  | "directory"
  | "compileArguments"
  | "timeoutMs"
  | "endpoint"
  | "configPath"
  | "compilationDatabase"
  | "libraryDirectory"
> & { buffers?: Record<string, string> };
export interface ActionFileProfile {
  directory: string;
  compileArguments: string[];
  compilationDatabase?: string;
}
const responseSchema = z.object({
  id: z.number().int(),
  progress: z.string().optional(),
  error: z.string().optional(),
  output: z.array(z.string()).optional(),
  report: actionReportSchema.optional(),
  searchReport: reportSchema
    .extend({
      results: z.array(
        reportSchema.shape.results.element.extend({
          nodeId: z.string().min(1),
          translationUnit: z.string().min(1),
        }),
      ),
    })
    .optional(),
  actionResults: z
    .object({
      resultHandle: z.string().min(1),
      offset: z.number().int().nonnegative(),
      limit: z.number().int().positive(),
      totalMatches: z.number().int().nonnegative(),
      results: z.array(actionResultSchema),
      hasMore: z.boolean(),
      complete: z.boolean(),
    })
    .optional(),
  reset: z.boolean().optional(),
  inspection: astInspectionSchema.optional(),
  graph: graphSchema.optional(),
  notFound: z.boolean().optional(),
  keptAlive: z.number().int().nonnegative().optional(),
});
type Response = z.infer<typeof responseSchema>;
export type ActionResultsPage = NonNullable<Response["actionResults"]>;
interface Pending {
  resolve(value: Response): void;
  reject(error: Error): void;
  timer: ReturnType<typeof setTimeout>;
  cancellationGraceMs: number;
  progress(text: string): void;
}
export class ActionService {
  private child: ChildProcessWithoutNullStreams | undefined;
  private identity = 0;
  private pending = new Map<number, Pending>();
  private stderr = "";
  private killTimer: ReturnType<typeof setTimeout> | undefined;
  private disposed = false;
  private heartbeat: ReturnType<typeof setInterval> | undefined;
  private renewing: Promise<Response> | undefined;
  private directory: string | undefined;
  private readonly observers = new Set<{
    invalidated: (reason: string) => void;
    log: (text: string) => void;
  }>();
  constructor(
    private readonly script: string,
    private readonly python: string,
    private invalidated: (reason: string) => void = () => {},
    private log: (text: string) => void = () => {},
  ) {}

  setCallbacks(
    invalidated: (reason: string) => void,
    log: (text: string) => void,
  ): void {
    this.invalidated = invalidated;
    this.log = log;
  }
  subscribe(
    invalidated: (reason: string) => void,
    log: (text: string) => void,
  ): () => void {
    const observer = { invalidated, log };
    this.observers.add(observer);
    return () => this.observers.delete(observer);
  }
  private invalidate(reason: string): void {
    this.invalidated(reason);
    for (const observer of this.observers) observer.invalidated(reason);
  }
  private output(text: string): void {
    this.log(text);
    for (const observer of this.observers) observer.log(text);
  }

  async run(
    action: NodeAction,
    values: Record<string, ArgumentValue>,
    files: string[],
    settings: ActionSettings,
    maximum: number,
    progress: (text: string) => void = () => {},
    inputId?: string,
    batch = false,
    profiles?: Record<string, ActionFileProfile>,
    resumeManifest?: string,
  ): Promise<ActionReport> {
    const response = await this.request(
      {
        type: "run",
        action,
        values,
        files,
        settings,
        maximum,
        ...(inputId ? { inputId } : {}),
        ...(batch ? { batch: true } : {}),
        ...(profiles ? { profiles } : {}),
        ...(resumeManifest ? { resumeManifest } : {}),
      },
      settings.directory,
      Math.max(30000, settings.timeoutMs * Math.max(1, files.length) + 10000),
      progress,
      batch ? settings.timeoutMs + 10000 : 5000,
    );
    if (!response.report)
      throw new Error("Action worker returned no matches report");
    return response.report;
  }
  async reset(): Promise<void> {
    this.stopHeartbeat();
    this.clearKillTimer();
    if (this.child)
      await this.request({ type: "reset" }, process.cwd(), 15000, () => {});
  }
  async pageActionResults(
    settings: ActionSettings,
    resultHandle: string,
    offset: number,
    limit: number,
  ): Promise<ActionResultsPage> {
    const response = await this.request(
      { type: "pageActionResults", settings, resultHandle, offset, limit },
      settings.directory,
      settings.timeoutMs + 10000,
      () => {},
    );
    if (!response.actionResults)
      throw new Error("Action worker returned no results page");
    return response.actionResults;
  }
  async search(
    settings: ActionSettings,
    files: string[],
    queries: string[],
    maximum: number,
    progress: (text: string) => void = () => {},
  ): Promise<RunReport> {
    const response = await this.request(
      { type: "search", settings, files, queries, maximum },
      settings.directory,
      Math.max(
        30000,
        settings.timeoutMs * Math.max(1, files.length) * (queries.length + 1) +
          10000,
      ),
      progress,
    );
    if (!response.searchReport)
      throw new Error("Search worker returned no report");
    return response.searchReport;
  }
  async keepAlive(): Promise<number> {
    if (this.disposed) throw new Error("Action session closed");
    if (!this.child || !this.directory) return 0;
    if (this.renewing) return (await this.renewing).keptAlive ?? 0;
    if (this.pending.size) return 0;
    const renewal = this.request(
      { type: "keepAlive" },
      this.directory,
      15000,
      () => {},
    );
    this.renewing = renewal;
    try {
      return (await renewal).keptAlive ?? 0;
    } finally {
      if (this.renewing === renewal) this.renewing = undefined;
    }
  }
  private startHeartbeat(): void {
    if (this.heartbeat || this.disposed) return;
    this.heartbeat = setInterval(() => {
      void this.keepAlive().catch((error: unknown) => {
        if (this.disposed) return;
        this.stopHeartbeat();
        this.output(`AST session renewal: ${String(error)}`);
        this.invalidate(
          "Analysis session renewal failed; reload the file AST.",
        );
      });
    }, 60000);
    this.heartbeat.unref();
  }
  private stopHeartbeat(): void {
    clearInterval(this.heartbeat);
    this.heartbeat = undefined;
  }
  async inspect(
    settings: ActionSettings,
    target:
      | string
      | { result?: Result; translationUnit: string; reference?: AstReference },
  ): Promise<AstInspection> {
    const input =
      typeof target === "string"
        ? { nodeId: target }
        : target.reference
          ? {
              translationUnit: target.translationUnit,
              reference: astReferenceSchema.parse(target.reference),
            }
          : !target.result
            ? { translationUnit: target.translationUnit }
            : {
                translationUnit: target.translationUnit,
                result: {
                  ...target.result,
                  raw: undefined,
                  nativeKind: nativeKind(target.result),
                  implicit: astDisplay(target.result).properties.some(
                    (property) => property.label === "Implicit",
                  ),
                  kind: nativeKind(target.result).replace(/^./, (c) =>
                    c.toUpperCase(),
                  ),
                },
              };
    const response = await this.request(
      { type: "inspect", settings, ...input },
      settings.directory,
      // Initial inspection parses the file, locates its root, then fetches
      // children. Each RPC already enforces settings.timeoutMs separately.
      settings.timeoutMs * (typeof target === "string" ? 1 : 3) + 10000,
      () => {},
    );
    if (!response.inspection) throw new Error("AST inspector returned no node");
    return response.inspection;
  }
  async selectSource(
    settings: ActionSettings,
    nodeId: string,
    selection: SourceSelection,
  ): Promise<AstInspection | undefined> {
    const response = await this.request(
      {
        type: "selectSource",
        settings,
        nodeId,
        selection: sourceSelectionSchema.parse(selection),
      },
      settings.directory,
      settings.timeoutMs + 10000,
      () => {},
    );
    if (response.notFound) return;
    if (!response.inspection)
      throw new Error("Source lookup returned no AST result");
    return response.inspection;
  }
  async graph(
    settings: ActionSettings,
    nodeId: string,
    kind: GraphKind,
  ): Promise<AnalysisGraph> {
    const response = await this.request(
      { type: "graph", settings, nodeId, kind },
      settings.directory,
      settings.timeoutMs * 3 + 10000,
      () => {},
    );
    if (!response.graph) throw new Error("Graph worker returned no graph");
    return response.graph;
  }
  private start(directory: string): ChildProcessWithoutNullStreams {
    if (this.child) return this.child;
    const child = spawn(this.python, ["-I", "-B", "-u", this.script], {
      cwd: directory,
      stdio: "pipe",
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
    });
    this.child = child;
    this.directory = directory;
    this.stderr = "";
    const lines = createInterface({ input: child.stdout });
    lines.on("line", (line) => {
      try {
        const response = responseSchema.parse(JSON.parse(line));
        const pending = this.pending.get(response.id);
        if (!pending) return;
        if (response.progress) {
          pending.progress(response.progress);
          return;
        }
        this.pending.delete(response.id);
        clearTimeout(pending.timer);
        this.clearKillTimer();
        for (const text of response.output ?? []) if (text) this.output(text);
        if (response.error) {
          if (
            /cursor unavailable|cursor expired or closed|retained value has been closed|node has expired|analysis session expired/i.test(
              response.error,
            )
          )
            this.invalidate(
              "Analysis context expired or closed; click Refresh, then Run to parse the same C++ file again.",
            );
          pending.reject(new Error(response.error));
        } else {
          if (
            response.inspection ||
            response.report ||
            response.searchReport ||
            response.actionResults
          )
            this.startHeartbeat();
          pending.resolve(response);
        }
      } catch (error) {
        this.fail(error instanceof Error ? error : new Error(String(error)));
        child.kill();
      }
    });
    child.stderr.on("data", (data: Buffer) => {
      this.stderr = (this.stderr + data.toString()).slice(-8000);
    });
    child.once("error", (error) => {
      if (this.child !== child) return;
      this.child = undefined;
      this.fail(error);
      this.invalidate(
        "Could not start action session; check ctk.pythonPath and refresh analysis.",
      );
    });
    child.stdin.on("error", (error) => this.fail(error));
    child.once("exit", (code) => {
      lines.close();
      if (this.child !== child) return;
      this.child = undefined;
      this.fail(
        new Error(
          `Action session stopped (${code}); refresh analysis. ${this.stderr}`,
        ),
      );
      this.invalidate(
        "Action session closed; refresh analysis before continuing",
      );
    });
    return child;
  }
  private request(
    value: Record<string, unknown>,
    directory: string,
    timeout: number,
    progress: (text: string) => void,
    cancellationGraceMs = 5000,
  ): Promise<Response> {
    if (this.disposed)
      return Promise.reject(new Error("Action session closed"));
    if (value.type !== "keepAlive" && this.renewing)
      return this.renewing
        .catch(() => undefined)
        .then(() => this.request(value, directory, timeout, progress));
    if (this.pending.size)
      return Promise.reject(new Error("An action is already running"));
    const child = this.start(directory),
      id = ++this.identity;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.fail(
          new Error("Action timed out; refresh analysis before continuing"),
        );
        child.kill();
      }, timeout);
      this.pending.set(id, {
        resolve,
        reject,
        timer,
        cancellationGraceMs,
        progress,
      });
      child.stdin.write(`${JSON.stringify({ ...value, id })}\n`);
    });
  }
  cancel(): void {
    if (!this.pending.size || !this.child) return;
    const child = this.child;
    const pending = this.pending.values().next().value as Pending | undefined;
    child.kill("SIGINT");
    this.clearKillTimer();
    this.killTimer = setTimeout(() => {
      if (this.child === child) child.kill("SIGKILL");
    }, pending?.cancellationGraceMs ?? 5000);
    this.killTimer.unref();
  }
  private clearKillTimer(): void {
    if (this.killTimer) clearTimeout(this.killTimer);
    this.killTimer = undefined;
  }
  private fail(error: Error): void {
    this.stopHeartbeat();
    this.clearKillTimer();
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }
  dispose(): void {
    if (this.disposed) return;
    this.stopHeartbeat();
    this.disposed = true;
    const child = this.child;
    this.child = undefined;
    child?.stdin.end();
    const timer = setTimeout(() => child?.kill(), 3000);
    timer.unref();
    this.fail(new Error("Action session closed"));
  }
}
