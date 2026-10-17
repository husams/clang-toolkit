import { stat } from "node:fs/promises";
import type { RunReport, RunRequest } from "./model.js";
import { startWorker, type WorkerRun } from "./worker-client.js";

interface Entry {
  key: string;
  prefix: string;
  expires: number;
  run: WorkerRun;
  report?: RunReport;
}

/** Native queries stay in a worker; drafts are never evaluated for completion. */
export class ClassNameService {
  private readonly entries: Entry[] = [];
  constructor(private readonly worker: string) {}

  async complete(request: RunRequest, prefix: string): Promise<RunReport> {
    const file = request.files[0];
    if (!file) throw new Error("Class completion requires a C++ file");
    const info = await stat(file);
    const query: RunRequest = {
      ...request,
      files: [file],
      kinds: ["classes"],
      values: { NAME: prefix },
      includeHeaders: true,
    };
    const key = JSON.stringify({
      ...query,
      values: {},
      modified: info.mtimeMs,
      size: info.size,
    });
    for (const entry of [...this.entries]) {
      if (entry.expires <= Date.now()) this.remove(entry);
    }
    let entry = this.entries.find(
      (candidate) =>
        candidate.key === key &&
        prefix.startsWith(candidate.prefix) &&
        (!candidate.report?.truncated || prefix === candidate.prefix),
    );
    if (!entry) {
      while (this.entries.length >= 8) {
        const oldest = this.entries[0];
        if (oldest) this.remove(oldest);
      }
      entry = {
        key,
        prefix,
        expires: Date.now() + request.timeoutMs + 5000,
        run: startWorker(this.worker, query, () => {}),
      };
      this.entries.push(entry);
    }
    try {
      const report = entry.report ?? (await entry.run.completion);
      if (report.errors.length) throw new Error(report.errors.join("\n"));
      entry.report = report;
      entry.expires = Date.now() + 2000;
      if (report.truncated && prefix !== entry.prefix) {
        this.remove(entry);
        return this.complete(request, prefix);
      }
      const seen = new Set<string>();
      return {
        ...report,
        results: report.results
          .filter((result) => {
            if (!result.name.includes(prefix) || seen.has(result.name))
              return false;
            seen.add(result.name);
            return true;
          })
          .sort((a, b) => a.name.localeCompare(b.name)),
      };
    } catch (error) {
      this.remove(entry);
      throw error;
    }
  }

  private remove(entry: Entry): void {
    const index = this.entries.indexOf(entry);
    if (index >= 0) this.entries.splice(index, 1);
    if (!entry.report) entry.run.cancel();
  }

  invalidate(): void {
    for (const entry of [...this.entries]) this.remove(entry);
  }

  dispose(): void {
    this.invalidate();
  }
}
