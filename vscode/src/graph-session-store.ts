import { randomUUID } from "node:crypto";
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import {
  type AnalysisGraph,
  type GraphKind,
  graphSchema,
} from "./graph-model.js";

const camera = z.object({
  scale: z.number().positive().finite(),
  ax: z.number().finite(),
  ay: z.number().finite(),
});
export const graphUiSchema = z.object({
  expanded: z
    .object({ out: z.array(z.string()), in: z.array(z.string()) })
    .optional(),
  trail: z.array(z.string()).optional(),
  cameras: z.record(z.string(), camera).optional(),
  view: camera.optional(),
  direction: z.enum(["out", "in"]).optional(),
});
export const graphSessionSchema = z.object({
  model: graphSchema,
  uiState: z
    .string()
    .max(2000000)
    .refine((text) => {
      try {
        return graphUiSchema.safeParse(text ? JSON.parse(text) : {}).success;
      } catch {
        return false;
      }
    }, "Invalid saved graph view"),
});
export type GraphSession = z.infer<typeof graphSessionSchema>;
const stored = z.object({
  version: z.literal(1),
  sessions: z.array(graphSessionSchema),
});
export function graphIdentity(model: AnalysisGraph): string {
  const root = model.nodes.find((node) => node.id === model.root);
  return JSON.stringify([
    model.kind,
    root?.file,
    root?.line,
    root?.column,
    model.name,
  ]);
}
export class GraphSessionStore {
  private readonly sessions = new Map<string, GraphSession>();
  private pending: Promise<void> = Promise.resolve();
  readonly ready: Promise<void>;
  constructor(
    private readonly directory: string,
    report: (error: unknown) => void = console.error,
  ) {
    this.ready = readFile(join(directory, "graph-sessions.json"), "utf8")
      .then((text) => {
        for (const session of stored.parse(JSON.parse(text)).sessions)
          this.sessions.set(graphIdentity(session.model), session);
      })
      .catch((error: unknown) => {
        if (
          !(
            error instanceof Error &&
            "code" in error &&
            error.code === "ENOENT"
          )
        )
          report(error);
      });
  }
  latest(kind?: GraphKind): GraphSession | undefined {
    return [...this.sessions.values()]
      .reverse()
      .find((session) => !kind || session.model.kind === kind);
  }
  byModelKey(key: string): GraphSession | undefined {
    return [...this.sessions.values()].find(
      (session) => session.model.key === key,
    );
  }
  async remember(input: GraphSession): Promise<void> {
    const session = graphSessionSchema.parse(input);
    await this.ready;
    const key = graphIdentity(session.model);
    this.sessions.delete(key);
    this.sessions.set(key, session);
    const write = async () => {
      await mkdir(this.directory, { recursive: true });
      const temporary = join(
        this.directory,
        `graph-sessions-${randomUUID()}.tmp`,
      );
      await writeFile(
        temporary,
        JSON.stringify({ version: 1, sessions: [...this.sessions.values()] }),
        "utf8",
      );
      await rename(temporary, join(this.directory, "graph-sessions.json"));
    };
    this.pending = this.pending.then(write, write);
    await this.pending;
  }
  async flush(): Promise<void> {
    await this.ready;
    await this.pending;
  }
}
