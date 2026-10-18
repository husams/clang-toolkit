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
});
