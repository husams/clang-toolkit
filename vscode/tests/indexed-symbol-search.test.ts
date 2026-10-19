import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import {
  IndexedSymbolSearch,
  indexedNativeKind,
} from "../src/indexed-symbol-search.js";

const temporaryDirectories: string[] = [];
async function setup() {
  const directory = await mkdtemp(join(tmpdir(), "ctk-index-search-"));
  temporaryDirectories.push(directory);
  const script = join(directory, "worker.py");
  await writeFile(
    script,
    `import json, sys, time\nrequest = json.load(sys.stdin)\nif request["query"] == "slow": time.sleep(0.35)\nquery = request["query"]\nresult = {"id": query, "name": query, "kind": "TypeAlias", "file": "/repo/source.cpp", "line": 3, "column": 2, "excerpt": "using Alias = int;", "project": "/repo"}\nprint(json.dumps({"projects": ["/repo"], "results": [result] if query else [], "errors": [], "status": "", "truncated": False}))\n`,
  );
  return new IndexedSymbolSearch(
    script,
    "python3",
    { directory, timeoutMs: 1000, maxResults: 2000 },
    () => {},
  );
}
async function setupResponse(response: object) {
  const directory = await mkdtemp(join(tmpdir(), "ctk-index-status-"));
  temporaryDirectories.push(directory);
  const script = join(directory, "worker.py");
  await writeFile(
    script,
    `print(${JSON.stringify(JSON.stringify(response))})\n`,
  );
  return new IndexedSymbolSearch(
    script,
    "python3",
    { directory, timeoutMs: 1000, maxResults: 100 },
    () => {},
  );
}
afterEach(async () => {
  await Promise.all(
    temporaryDirectories
      .splice(0)
      .map((directory) => rm(directory, { recursive: true, force: true })),
  );
});

describe("IndexedSymbolSearch", () => {
  it("maps Clang declaration names to native AST payload kinds", () => {
    expect(indexedNativeKind("TypeAlias")).toBe("typeAliasDecl");
    expect(indexedNativeKind("NamespaceAlias")).toBe("namespaceAliasDecl");
    expect(indexedNativeKind("CXXRecord")).toBe("cxxRecordDecl");
    expect(indexedNativeKind("CXXMethod")).toBe("cxxMethodDecl");
  });

  it("keeps the newest query result when an older request completes later", async () => {
    const search = await setup();
    const old = search.search({ query: "slow" });
    await new Promise((resolve) => setTimeout(resolve, 25));
    const current = search.search({ query: "latest" });
    await Promise.all([old, current]);
    expect(search.state.results.map((result) => result.name)).toEqual([
      "latest",
    ]);
    expect(search.state.completed).toBe(true);
  });

  it("defaults source-only off and preserves it across indexed scope changes", async () => {
    const directory = await mkdtemp(join(tmpdir(), "ctk-index-source-only-"));
    temporaryDirectories.push(directory);
    const script = join(directory, "worker.py");
    await writeFile(
      script,
      `import json, sys\nrequest = json.load(sys.stdin)\nprint(json.dumps({"projects": ["/repo"], "results": [], "errors": [], "status": json.dumps({"sourceOnly": request.get("sourceOnly", False), "scope": request["scope"], "project": request["project"]}), "truncated": False}))\n`,
    );
    const search = new IndexedSymbolSearch(
      script,
      "python3",
      { directory, timeoutMs: 1000, maxResults: 100 },
      () => {},
    );
    expect(search.state.sourceOnly).toBe(false);
    await search.search({
      query: "",
      scope: "project",
      project: "/repo",
      kinds: ["aliases"],
      sourceOnly: true,
    });
    expect(JSON.parse(search.state.status)).toEqual({
      sourceOnly: true,
      scope: "project",
      project: "/repo",
    });
    await search.search({ scope: "global", project: "/repo" });
    expect(JSON.parse(search.state.status)).toEqual({
      sourceOnly: true,
      scope: "global",
      project: "/repo",
    });
  });

  it("defaults the selected project to the root containing its working directory", async () => {
    const directory = await mkdtemp(join(tmpdir(), "ctk-index-roots-"));
    temporaryDirectories.push(directory);
    const selectedRoot = join(directory, "zeta");
    await mkdir(join(selectedRoot, "src"), { recursive: true });
    const script = join(directory, "worker.py");
    await writeFile(
      script,
      `import json, sys\nrequest = json.load(sys.stdin)\nprint(json.dumps({"projects": [${JSON.stringify(join(directory, "alpha"))}, ${JSON.stringify(selectedRoot)}], "results": [], "errors": [], "status": "", "truncated": False}))\n`,
    );
    const search = new IndexedSymbolSearch(
      script,
      "python3",
      {
        directory: join(selectedRoot, "src"),
        timeoutMs: 1000,
        maxResults: 100,
      },
      () => {},
    );
    await search.projects();
    expect(search.state.project).toBe(selectedRoot);
  });

  it("cancels the active index request without accepting its late result", async () => {
    const search = await setup();
    const pending = search.search({ query: "slow" });
    await new Promise((resolve) => setTimeout(resolve, 25));
    search.cancel();
    await pending;
    expect(search.state.results).toEqual([]);
    expect(search.state.status).toBe("Search cancelled.");
  });

  it("explains a checking index with saved results and reused progress", async () => {
    const search = await setupResponse({
      projects: ["/repo"],
      results: [
        {
          id: "a",
          name: "Alias",
          kind: "TypeAlias",
          file: "/repo/a.hpp",
          line: 3,
          column: 2,
          excerpt: "using Alias = int;",
          project: "/repo",
        },
      ],
      errors: [],
      status:
        "These results came from a stale index. Reindex the project to refresh them. Results were truncated at the server limit.",
      truncated: true,
      indexStates: [
        {
          root: "/repo",
          state: 8,
          indexed: 629,
          total: 629,
          completed: 560,
          skipped: 559,
          failed: 0,
          stale: true,
        },
      ],
    });
    await search.search({ query: "Alias", scope: "project", project: "/repo" });
    expect(search.state.results).toHaveLength(1);
    expect(search.state.status).toContain(
      "Checking source changes; saved index results may be outdated (560/629 checked, 559 reused, 1 updated).",
    );
    expect(search.state.status).toContain("Results were truncated");
    expect(search.state.status).not.toContain("Reindex the project");
  });

  it.each([
    { state: 7, indexed: 629, total: 629, failed: 1 },
    { state: 5, indexed: 629, total: 629, failed: 0 },
    { state: 8, indexed: 628, total: 629, failed: 0 },
  ])(
    "keeps a real stale warning for state $state with incomplete or failed coverage",
    async ({ state, indexed, total, failed }) => {
      const warning =
        "These results came from a stale index. Reindex the project to refresh them.";
      const search = await setupResponse({
        projects: ["/repo"],
        results: [],
        errors: [],
        status: warning,
        indexStates: [
          {
            root: "/repo",
            state,
            indexed,
            total,
            completed: 560,
            skipped: 559,
            failed,
            stale: true,
          },
        ],
      });
      await search.search({
        query: "Alias",
        scope: "project",
        project: "/repo",
      });
      expect(search.state.status).toBe(warning);
    },
  );

  it("keeps the stale warning when a global search also has a failed project", async () => {
    const warning =
      "These results came from a stale index. Reindex the project to refresh them.";
    const search = await setupResponse({
      projects: ["/one", "/two"],
      results: [],
      errors: [],
      status: warning,
      indexStates: [
        {
          root: "/one",
          state: 8,
          indexed: 629,
          total: 629,
          completed: 560,
          skipped: 560,
          failed: 0,
          stale: true,
        },
        {
          root: "/two",
          state: 7,
          indexed: 8,
          total: 8,
          completed: 7,
          skipped: 0,
          failed: 1,
          stale: true,
        },
      ],
    });
    await search.search({ query: "Alias", scope: "global" });
    expect(search.state.status).toBe(warning);
  });
});
