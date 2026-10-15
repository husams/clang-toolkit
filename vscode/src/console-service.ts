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
});
export type ConsoleResponse = z.infer<typeof responseSchema>;
interface Pending {
  resolve(value: ConsoleResponse): void;
  reject(error: Error): void;
  timer: ReturnType<typeof setTimeout>;
}
export class ConsoleService {
  private child: ChildProcessWithoutNullStreams | undefined;
  private identity = 0;
  private readonly pending = new Map<number, Pending>();
  private stderr = "";
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
  ): Promise<ConsoleResponse> {
    if (!this.child) {
      const child = spawn(this.python, ["-I", "-B", "-u", this.script], {
        stdio: "pipe",
        env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
      });
      this.child = child;
      const lines = createInterface({ input: child.stdout });
      lines.on("line", (line) => {
        try {
          const result = responseSchema.parse(JSON.parse(line));
          const pending = this.pending.get(result.id);
          if (!pending) return;
          this.pending.delete(result.id);
          clearTimeout(pending.timer);
          if (result.error) pending.reject(new Error(result.error));
          else pending.resolve(result);
        } catch (error) {
          this.fail(error instanceof Error ? error : new Error(String(error)));
        }
      });
      child.stderr.on("data", (chunk: Buffer) => {
        this.stderr = (this.stderr + chunk.toString()).slice(-8000);
      });
      child.on("error", (error) => this.fail(error));
      child.on("exit", (code) => {
        lines.close();
        this.child = undefined;
        this.fail(
          new Error(
            `Console completion service stopped (${code}). ${this.stderr}`,
          ),
        );
      });
      child.stdin.on("error", (error) => this.fail(error));
    }
    const id = ++this.identity;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(
          new Error(
            "Console completion timed out; check CTK Completion output and ctk.pythonPath.",
          ),
        );
      }, 30000);
      this.pending.set(id, { resolve, reject, timer });
      this.child?.stdin.write(
        `${JSON.stringify({ id, source, cursor, directory, library, scriptDirectory, targetFile })}\n`,
      );
    });
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
    this.child?.kill();
    this.child = undefined;
    this.fail(new Error("Console completion closed"));
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
