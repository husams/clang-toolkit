import { type ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { isAbsolute, relative } from "node:path";
import { createInterface } from "node:readline";
import { z } from "zod";

const resultSchema = z.object({
  id: z.string(),
  name: z.string(),
  kind: z.string(),
  file: z.string(),
  line: z.number().int().positive(),
  column: z.number().int().positive(),
  excerpt: z.string(),
  project: z.string(),
  translationUnit: z.string().optional(),
  displayFile: z.string().optional(),
});
export const indexedSearchResponseSchema = z.object({
  projects: z.array(z.string()).default([]),
  results: z.array(resultSchema).default([]),
  errors: z.array(z.string()).default([]),
  status: z.string().default(""),
  truncated: z.boolean().default(false),
  error: z.string().optional(),
});
export type IndexedSymbol = z.infer<typeof resultSchema>;
function projectForDirectory(roots: string[], directory: string): string {
  return (
    roots
      .filter((root) => {
        const path = relative(root, directory);
        return path === "" || (!path.startsWith("..") && !isAbsolute(path));
      })
      .sort((left, right) => right.length - left.length)[0] ??
    roots[0] ??
    ""
  );
}
export function indexedNativeKind(kind: string): string {
  const clangKind = kind.replace(/^CXX/, "cxx").replace(/^ObjC/, "objc");
  return `${clangKind.slice(0, 1).toLowerCase()}${clangKind.slice(1)}Decl`;
}
export interface IndexedSearchState {
  projects: { root: string; label: string }[];
  results: IndexedSymbol[];
  query: string;
  scope: "project" | "global";
  project: string;
  kinds: ("variables" | "classes" | "functions" | "aliases")[];
  exact: boolean;
  running: boolean;
  status: string;
  errors: string[];
  truncated: boolean;
  completed: boolean;
}
interface SearchRequest {
  mode: "projects" | "search";
  query: string;
  scope: "project" | "global";
  project: string;
  kinds: IndexedSearchState["kinds"];
  exact: boolean;
  maximum: number;
  timeoutMs: number;
  directory: string;
  endpoint?: string;
  configPath?: string;
  compilationDatabase?: string;
}
type Response = z.infer<typeof indexedSearchResponseSchema>;
interface ActiveRun {
  child: ChildProcessWithoutNullStreams;
  completion: Promise<Response>;
  cancel(): void;
}
function start(
  script: string,
  python: string,
  request: SearchRequest,
): ActiveRun {
  const child = spawn(python, ["-I", "-B", "-u", script], {
    cwd: request.directory,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
    stdio: "pipe",
  });
  let timer: ReturnType<typeof setTimeout> | undefined;
  let cancelled = false,
    response: Response | undefined,
    failure: Error | undefined,
    stderr = "";
  const lines = createInterface({ input: child.stdout });
  const completion = new Promise<Response>((resolve, reject) => {
    lines.on("line", (line) => {
      try {
        const parsed = indexedSearchResponseSchema.parse(JSON.parse(line));
        if (parsed.error) failure = new Error(parsed.error);
        else response = parsed;
      } catch (error) {
        failure = error instanceof Error ? error : new Error(String(error));
      }
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr = (stderr + chunk.toString()).slice(-8000);
    });
    child.once("error", reject);
    child.once("close", (code) => {
      clearTimeout(timer);
      lines.close();
      if (cancelled) reject(new Error("Indexed symbol search cancelled"));
      else if (failure) reject(failure);
      else if (code !== 0 || !response)
        reject(new Error(stderr || `Index search exited with code ${code}`));
      else resolve(response);
    });
    child.stdin.on("error", (error) => {
      failure = error;
    });
    child.stdin.end(JSON.stringify(request));
  });
  return {
    child,
    completion,
    cancel: () => {
      if (cancelled) return;
      cancelled = true;
      child.kill("SIGTERM");
      timer = setTimeout(() => child.kill("SIGKILL"), 3000);
      timer.unref();
    },
  };
}

export class IndexedSymbolSearch {
  readonly state: IndexedSearchState = {
    projects: [],
    results: [],
    query: "",
    scope: "project",
    project: "",
    kinds: ["variables", "classes", "functions", "aliases"],
    exact: false,
    running: false,
    status: "Connect to the CTK server to search indexed symbols.",
    errors: [],
    truncated: false,
    completed: false,
  };
  private revision = 0;
  private active: ActiveRun | undefined;
  constructor(
    private readonly script: string,
    private readonly python: string,
    private readonly settings: Omit<
      SearchRequest,
      "mode" | "query" | "scope" | "project" | "kinds" | "exact" | "maximum"
    > & { maxResults: number },
    private readonly publish: () => void,
  ) {}
  async projects(): Promise<void> {
    await this.execute({
      mode: "projects",
      query: "",
      scope: this.state.scope,
      project: this.state.project,
      kinds: this.state.kinds,
      exact: false,
      maximum: Math.min(1000, this.settings.maxResults),
    });
  }
  async search(
    update: Partial<
      Pick<
        IndexedSearchState,
        "query" | "scope" | "project" | "kinds" | "exact"
      >
    >,
  ): Promise<void> {
    Object.assign(this.state, update);
    this.state.results = [];
    this.state.errors = [];
    this.state.completed = false;
    this.state.status = "Searching indexed symbols…";
    await this.execute({
      mode: "search",
      query: this.state.query,
      scope: this.state.scope,
      project: this.state.project,
      kinds: this.state.kinds,
      exact: this.state.exact,
      maximum: Math.min(1000, this.settings.maxResults),
    });
  }
  cancel(): void {
    ++this.revision;
    this.active?.cancel();
    this.active = undefined;
    this.state.running = false;
    this.state.status = "Search cancelled.";
    this.state.completed = true;
    this.publish();
  }
  private async execute(
    request: Pick<
      SearchRequest,
      "mode" | "query" | "scope" | "project" | "kinds" | "exact" | "maximum"
    >,
  ): Promise<void> {
    const revision = ++this.revision;
    this.active?.cancel();
    this.state.running = true;
    this.state.errors = [];
    this.publish();
    const run = start(this.script, this.python, {
      ...this.settings,
      ...request,
    });
    this.active = run;
    try {
      const response = await run.completion;
      if (revision !== this.revision) return;
      this.state.projects = response.projects.map((root) => ({
        root,
        label:
          root.replace(/\\/g, "/").split("/").filter(Boolean).at(-1) || root,
      }));
      if (!this.state.project && this.state.projects.length)
        this.state.project = projectForDirectory(
          this.state.projects.map(({ root }) => root),
          this.settings.directory,
        );
      this.state.results = response.results.map((result) => ({
        ...result,
        displayFile: result.file,
      }));
      this.state.errors = response.errors;
      this.state.status =
        response.status ||
        (request.mode === "projects"
          ? `${this.state.projects.length} indexed ${this.state.projects.length === 1 ? "project" : "projects"} available.`
          : `${this.state.results.length} indexed ${this.state.results.length === 1 ? "symbol" : "symbols"} found${response.truncated ? " · result limit reached" : ""}.`);
      this.state.truncated = response.truncated;
      this.state.completed = true;
    } catch (error) {
      if (revision === this.revision) {
        this.state.errors = [
          error instanceof Error ? error.message : String(error),
        ];
        this.state.status = "Indexed symbol search failed.";
        this.state.completed = true;
      }
    } finally {
      if (revision === this.revision) {
        this.state.running = false;
        this.active = undefined;
        this.publish();
      }
    }
  }
}
