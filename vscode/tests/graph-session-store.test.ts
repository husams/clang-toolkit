import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, expect, it, vi } from "vitest";
import type { AnalysisGraph } from "../src/graph-model.js";
import {
  type GraphSession,
  GraphSessionStore,
  graphSessionSchema,
} from "../src/graph-session-store.js";

const directories: string[] = [];
afterEach(async () => {
  await Promise.all(
    directories
      .splice(0)
      .map((directory) => rm(directory, { recursive: true, force: true })),
  );
});
async function directory() {
  const path = await mkdtemp(join(tmpdir(), "ctk-graph-session-"));
  directories.push(path);
  return path;
}
function session(kind: "callgraph" | "cfg" = "callgraph"): GraphSession {
  const model: AnalysisGraph = {
    key: `native-${kind}`,
    kind,
    root: "0",
    name: "submit",
    complete: true,
    warnings: [],
    nodes: Array.from({ length: 302 }, (_, index) => ({
      id: String(index),
      name: `fn_${index}`,
      file: "/orders.cpp",
      line: index + 1,
      column: 1,
      detail: "",
    })),
    edges: Array.from({ length: 301 }, (_, index) => ({
      id: `edge_${index}`,
      from: String(Math.floor(index / 4)),
      to: String(index + 1),
      label: "",
    })),
  };
  return {
    model,
    uiState: JSON.stringify({
      expanded: { out: model.nodes.map((node) => node.id), in: [model.root] },
      trail: ["0", "1", "4"],
      direction: "out",
      cameras: {
        "out:0": { scale: 0.0349, ax: 0.16, ay: 0.66 },
        "out:1": { scale: 0.4, ax: -0.2, ay: 1.1 },
      },
      view: { scale: 1, ax: 0.34, ay: 0.5 },
    }),
  };
}
it("restores all 302 expanded functions, breadcrumbs and exact cameras from workspace storage", async () => {
  const path = await directory(),
    saved = session(),
    first = new GraphSessionStore(path);
  await first.remember(saved);
  await first.flush();
  const restarted = new GraphSessionStore(path);
  await restarted.ready;
  expect(restarted.latest()).toEqual(saved);
  expect(JSON.parse(restarted.latest()!.uiState)).toEqual(
    JSON.parse(saved.uiState),
  );
  expect(restarted.byModelKey(saved.model.key)).toEqual(saved);
});
it("keeps the latest complete view during overlapping updates and a subsequent restart", async () => {
  const path = await directory(),
    store = new GraphSessionStore(path),
    saved = session();
  await Promise.all(
    Array.from({ length: 8 }, (_, index) =>
      store.remember({
        ...saved,
        uiState: JSON.stringify({
          ...JSON.parse(saved.uiState),
          view: { scale: index + 1, ax: index / 10, ay: 0.5 },
        }),
      }),
    ),
  );
  const restarted = new GraphSessionStore(path);
  await restarted.ready;
  expect(JSON.parse(restarted.latest()!.uiState).view).toEqual({
    scale: 8,
    ax: 0.7,
    ay: 0.5,
  });
  expect(
    JSON.parse(await readFile(join(path, "graph-sessions.json"), "utf8"))
      .sessions,
  ).toHaveLength(1);
});
it("retains separate call graph and CFG sessions and replaces a re-parsed function by source identity", async () => {
  const path = await directory(),
    store = new GraphSessionStore(path),
    callgraph = session(),
    cfg = session("cfg");
  await store.remember(callgraph);
  await store.remember(cfg);
  const replacement = {
    ...callgraph,
    model: { ...callgraph.model, key: "fresh-native-session" },
  };
  await store.remember(replacement);
  const restarted = new GraphSessionStore(path);
  await restarted.ready;
  expect(restarted.latest("callgraph")).toEqual(replacement);
  expect(restarted.latest("cfg")).toEqual(cfg);
  expect(
    JSON.parse(await readFile(join(path, "graph-sessions.json"), "utf8"))
      .sessions,
  ).toHaveLength(2);
});
it("reports damaged storage and can save a new valid session afterwards", async () => {
  const path = await directory(),
    report = vi.fn();
  await writeFile(join(path, "graph-sessions.json"), "{broken");
  const store = new GraphSessionStore(path, report);
  await store.ready;
  expect(report).toHaveBeenCalledOnce();
  expect(store.latest()).toBeUndefined();
  await store.remember(session());
  const restarted = new GraphSessionStore(path);
  await restarted.ready;
  expect(restarted.latest()).toEqual(session());
});
it("rejects invalid graph endpoints, malformed state and non-finite or non-positive cameras", () => {
  const saved = session();
  expect(
    graphSessionSchema.safeParse({
      ...saved,
      model: { ...saved.model, root: "missing" },
    }).success,
  ).toBe(false);
  for (const uiState of [
    "{broken",
    JSON.stringify({ view: { scale: -1, ax: 0, ay: 0 } }),
    JSON.stringify({ cameras: { "out:0": { scale: 1, ax: "NaN", ay: 0 } } }),
  ])
    expect(graphSessionSchema.safeParse({ ...saved, uiState }).success).toBe(
      false,
    );
});
