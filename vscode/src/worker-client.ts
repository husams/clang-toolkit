import { type ChildProcess, spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { z } from "zod";
import { type RunReport, type RunRequest, reportSchema } from "./model.js";

const eventSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("progress"),
    file: z.string(),
    index: z.number(),
  }),
  z.object({ type: z.literal("complete"), report: reportSchema }),
  z.object({ type: z.literal("error"), message: z.string() }),
]);
export interface WorkerRun {
  process: ChildProcess;
  completion: Promise<RunReport>;
  cancel(): void;
}
export function startWorker(
  path: string,
  request: RunRequest,
  progress: (text: string) => void,
): WorkerRun {
  const child = spawn(process.execPath, [path], {
    env: { ...process.env, ELECTRON_RUN_AS_NODE: "1" },
    stdio: ["pipe", "pipe", "pipe"],
    cwd: request.directory,
  });
  let cancelled = false,
    report: RunReport | undefined,
    failure: Error | undefined,
    stderr = "";
  const lines = createInterface({ input: child.stdout });
  const completion = new Promise<RunReport>((resolve, reject) => {
    lines.on("line", (line: string) => {
      try {
        const event = eventSchema.parse(JSON.parse(line));
        if (event.type === "progress")
          progress(
            `${event.index + 1}/${request.files.length} · ${event.file}`,
          );
        if (event.type === "complete") report = event.report;
        if (event.type === "error") failure = new Error(event.message);
      } catch (error) {
        failure = error instanceof Error ? error : new Error(String(error));
        child.kill();
      }
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr = (stderr + chunk.toString()).slice(-16000);
    });
    child.once("error", reject);
    child.once("close", (code) => {
      lines.close();
      if (cancelled) reject(new Error("Analysis cancelled"));
      else if (failure) reject(failure);
      else if (code !== 0 || !report)
        reject(new Error(stderr || `Analysis worker exited with code ${code}`));
      else resolve(report);
    });
    child.stdin.on("error", (error) => {
      failure = error;
    });
    child.stdin.end(JSON.stringify(request));
  });
  return {
    process: child,
    completion,
    cancel: () => {
      cancelled = true;
      child.kill("SIGTERM");
    },
  };
}
