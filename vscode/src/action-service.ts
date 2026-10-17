import { type ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { z } from "zod";
import {
  type ActionReport,
  type ArgumentValue,
  actionReportSchema,
  type NodeAction,
} from "./actions.js";
import {
  type AstInspection,
  astDisplay,
  astInspectionSchema,
  nativeKind,
  type SourceSelection,
  sourceSelectionSchema,
} from "./ast-model.js";
import type { Result, RunRequest } from "./model.js";

export type ActionSettings = Pick<
  RunRequest,
  | "directory"
  | "compileArguments"
  | "timeoutMs"
  | "endpoint"
  | "configPath"
  | "compilationDatabase"
  | "libraryDirectory"
>;
const responseSchema = z.object({
  id: z.number().int(),
  progress: z.string().optional(),
  error: z.string().optional(),
  output: z.array(z.string()).optional(),
  report: actionReportSchema.optional(),
  reset: z.boolean().optional(),
  inspection: astInspectionSchema.optional(),
  notFound: z.boolean().optional(),
});
type Response = z.infer<typeof responseSchema>;
interface Pending {
  resolve(value: Response): void;
  reject(error: Error): void;
  timer: ReturnType<typeof setTimeout>;
  progress(text: string): void;
}
export class ActionService {
  private child: ChildProcessWithoutNullStreams | undefined;
  private identity = 0;
  private pending = new Map<number, Pending>();
  private stderr = "";
  private killTimer: ReturnType<typeof setTimeout> | undefined;
  private disposed = false;
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

  async run(
    action: NodeAction,
    values: Record<string, ArgumentValue>,
    files: string[],
    settings: ActionSettings,
    maximum: number,
    progress: (text: string) => void = () => {},
    inputId?: string,
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
      },
      settings.directory,
      Math.max(30000, settings.timeoutMs * Math.max(1, files.length) + 10000),
      progress,
    );
    if (!response.report)
      throw new Error("Action worker returned no matches report");
    return response.report;
  }
  async reset(): Promise<void> {
    if (this.child)
      await this.request({ type: "reset" }, process.cwd(), 15000, () => {});
  }
  async inspect(
    settings: ActionSettings,
    target: string | { result?: Result; translationUnit: string },
  ): Promise<AstInspection> {
    const input =
      typeof target === "string"
        ? { nodeId: target }
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
      settings.timeoutMs + 10000,
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
  private start(directory: string): ChildProcessWithoutNullStreams {
    if (this.child) return this.child;
    const child = spawn(this.python, ["-I", "-B", "-u", this.script], {
      cwd: directory,
      stdio: "pipe",
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
    });
    this.child = child;
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
        clearTimeout(this.killTimer);
        for (const text of response.output ?? []) if (text) this.log(text);
        if (response.error) {
          if (
            /cursor unavailable|cursor expired or closed|retained value has been closed|node has expired/i.test(
              response.error,
            )
          )
            this.invalidated(
              "Analysis context expired or closed; click Refresh, then Run to parse the same C++ file again.",
            );
          pending.reject(new Error(response.error));
        } else pending.resolve(response);
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
      this.invalidated(
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
      this.invalidated(
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
  ): Promise<Response> {
    if (this.disposed)
      return Promise.reject(new Error("Action session closed"));
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
      this.pending.set(id, { resolve, reject, timer, progress });
      child.stdin.write(`${JSON.stringify({ ...value, id })}\n`);
    });
  }
  cancel(): void {
    if (!this.pending.size || !this.child) return;
    this.child.kill("SIGINT");
    this.killTimer = setTimeout(() => this.child?.kill("SIGKILL"), 5000);
    this.killTimer.unref();
  }
  private fail(error: Error): void {
    clearTimeout(this.killTimer);
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }
  dispose(): void {
    this.disposed = true;
    const child = this.child;
    this.child = undefined;
    child?.stdin.end();
    const timer = setTimeout(() => child?.kill(), 3000);
    timer.unref();
    this.fail(new Error("Action session closed"));
  }
}
