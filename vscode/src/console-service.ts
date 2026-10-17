import { type ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { access } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { createInterface } from "node:readline";
import { z } from "zod";

const responseSchema = z.object({
  id: z.number().int(),
  error: z.string().optional(),
  items: z
    .array(
      z.object({
        label: z.string(),
        text: z.string(),
        start: z.number().int().nonnegative(),
        detail: z.string(),
        documentation: z.string(),
      }),
    )
    .optional(),
  functions: z
    .record(
      z.string(),
      z.object({
        signature: z.string(),
        documentation: z.string(),
        signatures: z.array(z.string()).optional(),
      }),
    )
    .optional(),
  call: z
    .object({ name: z.string(), parameter: z.number().int().nonnegative() })
    .nullish(),
  symbols: z
    .object({
      file: z.string().min(1),
      prefix: z.string(),
      start: z.number().int().nonnegative(),
      quote: z.enum(['"', "'"]),
      close: z.boolean(),
    })
    .nullish(),
  parameterRoles: z.record(z.string(), z.enum(["path", "class"])).optional(),
});
export type ConsoleResponse = z.infer<typeof responseSchema>;
const messageSchema = z.union([
  z.object({ ready: z.literal(true) }),
  responseSchema,
]);
interface Pending {
  resolve(value: ConsoleResponse): void;
  reject(error: Error): void;
  timer: ReturnType<typeof setTimeout>;
}
export class ConsoleService {
  private child: ChildProcessWithoutNullStreams | undefined;
  private identity = 0;
  private readonly pending = new Map<number, Pending>();
  private readonly requests = new Map<string, Promise<ConsoleResponse>>();
  private stderr = "";
  private disposed = false;
  private ready = false;
  private starting:
    | {
        promise: Promise<ChildProcessWithoutNullStreams>;
        resolve(child: ChildProcessWithoutNullStreams): void;
        reject(error: Error): void;
        timer: ReturnType<typeof setTimeout>;
      }
    | undefined;
  constructor(
    private readonly script: string,
    private readonly python: string,
    private readonly log: (message: string) => void,
  ) {}
  request(
    source: string,
    cursor: number,
    directory: string,
    library: string,
    scriptDirectory?: string,
    targetFile?: string,
    parametersFor?: string,
  ): Promise<ConsoleResponse> {
    if (this.disposed)
      return Promise.reject(new Error("Console completion closed"));
    const payload = {
      source,
      cursor,
      directory,
      library,
      scriptDirectory,
      targetFile,
      parametersFor,
    };
    const key = JSON.stringify(payload);
    const existing = this.requests.get(key);
    if (existing) return existing;
    const request = this.send(payload).finally(() => {
      if (this.requests.get(key) === request) this.requests.delete(key);
    });
    this.requests.set(key, request);
    return request;
  }
  private start(): Promise<ChildProcessWithoutNullStreams> {
    if (this.disposed)
      return Promise.reject(new Error("Console completion closed"));
    if (this.ready && this.child) return Promise.resolve(this.child);
    if (this.starting) return this.starting.promise;
    const child = spawn(this.python, ["-I", "-B", "-u", this.script], {
      stdio: "pipe",
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
    });
    this.child = child;
    this.stderr = "";
    let finish!: (child: ChildProcessWithoutNullStreams) => void;
    let fail!: (error: Error) => void;
    const promise = new Promise<ChildProcessWithoutNullStreams>(
      (resolve, reject) => {
        finish = resolve;
        fail = reject;
      },
    );
    // Python imports are cold-start work, separate from processing a draft.
    this.starting = {
      promise,
      resolve: finish,
      reject: fail,
      timer: setTimeout(
        () =>
          this.stop(
            child,
            new Error(
              "Console completion worker startup timed out; retry completion.",
            ),
          ),
        30000,
      ),
    };
    const lines = createInterface({ input: child.stdout });
    lines.on("line", (line) => {
      if (this.child !== child) return;
      try {
        const result = messageSchema.parse(JSON.parse(line));
        if ("ready" in result) {
          this.ready = true;
          if (this.starting) {
            clearTimeout(this.starting.timer);
            this.starting.resolve(child);
            this.starting = undefined;
          }
          return;
        }
        const pending = this.pending.get(result.id);
        if (!pending) return;
        this.pending.delete(result.id);
        clearTimeout(pending.timer);
        if (result.error) pending.reject(new Error(result.error));
        else pending.resolve(result);
      } catch (error) {
        this.stop(
          child,
          error instanceof Error ? error : new Error(String(error)),
        );
      }
    });
    child.stderr.on("data", (chunk: Buffer) => {
      if (this.child !== child) return;
      this.stderr = (this.stderr + chunk.toString()).slice(-8000);
    });
    child.on("error", (error) => this.stop(child, error));
    child.on("exit", (code) => {
      lines.close();
      this.stop(
        child,
        new Error(
          `Console completion service stopped (${code}). ${this.stderr}`,
        ),
      );
    });
    child.stdin.on("error", (error) => this.stop(child, error));
    return promise;
  }
  private async send(
    payload: Record<string, unknown>,
  ): Promise<ConsoleResponse> {
    const child = await this.start();
    if (this.child !== child || this.disposed)
      throw new Error("Console completion worker closed; retry completion.");
    const id = ++this.identity;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.stop(
          child,
          new Error(
            "Console completion timed out; the worker was stopped. Retry completion; see CTK Completion output.",
          ),
        );
      }, 30000);
      this.pending.set(id, { resolve, reject, timer });
      child.stdin.write(`${JSON.stringify({ id, ...payload })}\n`);
    });
  }
  private stop(child: ChildProcessWithoutNullStreams, error: Error): void {
    if (this.child !== child) return;
    this.child = undefined;
    this.ready = false;
    if (this.starting) {
      clearTimeout(this.starting.timer);
      this.starting.reject(error);
      this.starting = undefined;
      this.log(error.message);
    }
    this.fail(error);
    this.requests.clear();
    child.kill("SIGKILL");
  }
  private fail(error: Error): void {
    if (this.pending.size) this.log(error.message);
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }
  dispose(): void {
    this.disposed = true;
    if (this.child)
      this.stop(this.child, new Error("Console completion closed"));
  }
}
export async function findPython(
  configured: string,
  directory: string,
): Promise<string> {
  if (configured) return configured;
  const candidates: string[] = [];
  if (process.env.VIRTUAL_ENV)
    candidates.push(
      join(
        process.env.VIRTUAL_ENV,
        process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
      ),
    );
  let parent = directory;
  for (let depth = 0; depth < 9; depth++) {
    candidates.push(
      join(
        parent,
        ".venv",
        process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
      ),
    );
    const next = dirname(parent);
    if (next === parent) break;
    parent = next;
  }
  candidates.push(
    join(homedir(), ".local/share/uv/tools/clang-toolkit/bin/python"),
  );
  for (const candidate of candidates) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      /* Try the next console environment. */
    }
  }
  return process.platform === "win32" ? "python" : "python3";
}
export const toCodePointOffset = (source: string, offset: number): number =>
  [...source.slice(0, offset)].length;
export const toUtf16Offset = (source: string, offset: number): number =>
  [...source].slice(0, offset).join("").length;
