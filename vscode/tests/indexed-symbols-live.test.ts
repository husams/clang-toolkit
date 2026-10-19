import { type ChildProcess, spawn } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { IndexedSymbolSearch } from "../src/indexed-symbol-search.js";

describe.skipIf(process.env.CTK_INTEGRATION !== "1")(
  "indexed symbol search against the native server",
  () => {
    let directory = "";
    let endpoint = "";
    let socketPath = "";
    let server: ChildProcess;
    let serverStderr = "";
    const roots: string[] = [];
    const python = process.env.CTK_PYTHON ?? resolve("../.venv/bin/python");
    const pythonCall = (script: string, input: unknown) =>
      new Promise<string>((resolveOutput, reject) => {
        const child = spawn(
          python,
          [
            "-I",
            "-c",
            `import sys; sys.path.insert(0, ${JSON.stringify(resolve("console"))});\n${script}`,
          ],
          { cwd: process.cwd(), stdio: ["pipe", "pipe", "pipe"] },
        );
        let stdout = "";
        let stderr = "";
        child.stdout.on(
          "data",
          (chunk: Buffer) => (stdout += chunk.toString()),
        );
        child.stderr.on(
          "data",
          (chunk: Buffer) => (stderr += chunk.toString()),
        );
        child.once("error", reject);
        child.once("close", (code) =>
          code === 0
            ? resolveOutput(stdout)
            : reject(new Error(`${stderr}\nserver: ${serverStderr}`)),
        );
        child.stdin.end(JSON.stringify(input));
      });

    beforeAll(async () => {
      directory = await mkdtemp(resolve(tmpdir(), "ctk-indexed-symbols-"));
      socketPath = resolve(
        "/private/tmp",
        `ctk-index-${process.pid}-${Date.now()}.sock`,
      );
      endpoint = `unix://${socketPath}`;
      const config = resolve(directory, "server.yaml");
      await writeFile(
        config,
        `network:\n  transport: unix\n  unix:\n    socket_path: ${socketPath}\n`,
      );
      server = spawn(
        process.env.CTK_SERVER ?? resolve("../build/dev/server/ctk-server"),
        ["-c", config],
        {
          env: {
            ...process.env,
            CTK_STORAGE_ROOT: resolve(directory, "storage"),
          },
          stdio: ["ignore", "ignore", "pipe"],
        },
      );
      server.stderr?.on("data", (chunk: Buffer) => {
        serverStderr = (serverStderr + chunk.toString()).slice(-4000);
      });
      for (const [name, ns] of [
        ["alpha", "alpha"],
        ["beta", "beta"],
      ] as const) {
        const root = resolve(directory, name);
        roots.push(root);
        await mkdir(root);
        const include = resolve(root, "include");
        const build = resolve(root, "build");
        const dependency = resolve(directory, "dependency");
        await mkdir(include);
        await mkdir(build);
        await mkdir(dependency, { recursive: true });
        await writeFile(
          resolve(include, "shared.hpp"),
          `namespace ${ns} { using SharedHeaderAlias = int; }\n`,
        );
        await writeFile(
          resolve(build, "generated.hpp"),
          `namespace ${ns} { using BuildDirectoryAlias = int; }\n`,
        );
        await writeFile(
          resolve(dependency, "external.hpp"),
          `namespace ${ns} { using ExternalDependencyAlias = int; }\n`,
        );
        const bulkCount = name === "alpha" ? 1007 : 1;
        const bulkAliases = Array.from(
          { length: bulkCount },
          (_, index) => `using Bulk${String(index).padStart(4, "0")} = int;`,
        ).join(" ");
        const source = resolve(root, "main.cpp");
        const helper = resolve(root, "helper.cpp");
        const generated = resolve(build, "generated.cpp");
        await writeFile(
          source,
          `#include "shared.hpp"\n#include "external.hpp"\nnamespace ${ns} { int AliasFunction(int x) { return x; } using AliasType = int; AliasType value; ${bulkAliases} }\n`,
        );
        await writeFile(
          helper,
          `#include "shared.hpp"\nint helper() { return 0; }\n`,
        );
        await writeFile(
          generated,
          `#include "generated.hpp"\nint generated() { return 0; }\n`,
        );
        const compileCommands = resolve(root, "compile_commands.json");
        await writeFile(
          compileCommands,
          JSON.stringify(
            [source, helper, generated].map((file) => ({
              directory: root,
              file,
              arguments: [
                process.env.CTK_TEST_CLANG ?? "clang++",
                "-std=c++20",
                `-I${include}`,
                `-I${dependency}`,
                "-c",
                file,
              ],
            })),
          ),
        );
      }
      await pythonCall(
        `import json, sys, time\nfrom clang_toolkit import Client\nfrom clang_toolkit._generated.index.v1 import index_service_pb2 as pb\nrequest = json.loads(sys.stdin.readline())\nclient = Client(request["endpoint"])\ntry:\n  ready = time.monotonic() + 15\n  while True:\n    try:\n      client.server_status()\n      break\n    except Exception:\n      if time.monotonic() >= ready: raise\n      time.sleep(0.1)\n  for root, compile_commands in request["projects"]:\n    client.start_project_index(root, compile_commands=compile_commands)\n  for root, _ in request["projects"]:\n    deadline = time.monotonic() + 45\n    while time.monotonic() < deadline:\n      status = client.project_index_status(root)\n      if status.state == pb.INDEX_STATE_COMPLETE: break\n      if status.state in (pb.INDEX_STATE_FAILED, pb.INDEX_STATE_CANCELLED): raise RuntimeError(status.error or root)\n      time.sleep(0.05)\n    else: raise RuntimeError("index timed out: " + root)\n    if status.translation_units_indexed != 3: raise RuntimeError("unexpected indexed coverage: " + str(status.translation_units_indexed))\n  print(json.dumps({"projects": len(request["projects"])}))\nfinally:\n  client.close()`,
        {
          endpoint,
          projects: roots.map((root) => [
            root,
            resolve(root, "compile_commands.json"),
          ]),
        },
      );
    }, 60000);

    afterAll(async () => {
      if (server?.exitCode === null) {
        const exit = new Promise((done) => server.once("exit", done));
        server.kill();
        await exit;
      }
      if (socketPath) await rm(socketPath, { force: true });
      if (directory) await rm(directory, { recursive: true, force: true });
    });

    it("searches both indexed projects and filters aliases before the server limit", async () => {
      const aliases = JSON.parse(
        await pythonCall(
          `import json, sys\nfrom clang_toolkit import Client\nrequest = json.loads(sys.stdin.readline())\nclient = Client(request["endpoint"])\ntry:\n  results = []\n  for root in request["roots"]:\n    response = client.find_symbols(root, "Alias", prefix=True, kind="alias", unique_symbols=True, limit=1)\n    results.extend({"kind": item.kind, "qualified_name": item.qualified_name, "truncated": response.truncated} for item in response.symbols)\n  print(json.dumps(results))\nfinally:\n  client.close()`,
          { endpoint, roots },
        ),
      ) as { kind: string; qualified_name: string; truncated: boolean }[];
      expect(aliases).toHaveLength(2);
      expect(
        aliases.every((item) => item.qualified_name.includes("AliasType")),
      ).toBe(true);
      expect(aliases.every((item) => item.kind === "TypeAlias")).toBe(true);

      const search = new IndexedSymbolSearch(
        resolve("console/indexed_symbol_search.py"),
        python,
        {
          directory,
          endpoint,
          timeoutMs: 30000,
          maxResults: 100,
        },
        () => {},
      );
      try {
        await search.projects();
        await search.search({
          query: "Alias",
          scope: "global",
          kinds: ["aliases"],
          exact: false,
        });
        expect(search.state.results.map((item) => item.project).sort()).toEqual(
          roots.sort(),
        );
        expect(
          search.state.results.every((item) => item.kind === "TypeAlias"),
        ).toBe(true);
      } finally {
        search.cancel();
      }
    }, 60000);

    it("enumerates every blank alias page by scope and source-only mode", async () => {
      const search = new IndexedSymbolSearch(
        resolve("console/indexed_symbol_search.py"),
        python,
        {
          directory,
          endpoint,
          timeoutMs: 30000,
          maxResults: 100,
        },
        () => {},
      );
      try {
        await search.projects();
        for (const scope of ["global", "project"] as const) {
          for (const sourceOnly of [false, true]) {
            await search.search({
              query: "",
              scope,
              project: roots[0] ?? "",
              kinds: ["aliases"],
              exact: true,
              sourceOnly,
            });
            expect(search.state.errors).toEqual([]);
            expect(search.state.truncated).toBe(false);
            const results = search.state.results;
            expect(results.length).toBeGreaterThan(100);
            const expectedProjects = scope === "global" ? roots : [roots[0]];
            expect(
              [...new Set(results.map((item) => item.project))].sort(),
            ).toEqual([...expectedProjects].sort());
            for (const root of expectedProjects) {
              const ns = root === roots[0] ? "alpha" : "beta";
              expect(
                results.filter(
                  (item) => item.name === `${ns}::SharedHeaderAlias`,
                ),
              ).toHaveLength(1);
            }
            const sourceResults = results.filter(
              (item) => item.project === roots[0],
            );
            const sourceNamespace = sourceOnly
              ? ["main.cpp", "shared.hpp"]
              : ["main.cpp", "shared.hpp", "generated.hpp", "external.hpp"];
            for (const name of sourceNamespace) {
              expect(
                sourceResults.some((item) => item.file.endsWith(name)),
              ).toBe(true);
            }
            if (sourceOnly) {
              expect(
                sourceResults.some((item) => item.file.includes("/build/")),
              ).toBe(false);
              expect(
                sourceResults.some((item) =>
                  item.file.endsWith("external.hpp"),
                ),
              ).toBe(false);
            } else {
              expect(
                sourceResults.some((item) => item.file.includes("/build/")),
              ).toBe(true);
              expect(
                sourceResults.some((item) =>
                  item.file.endsWith("external.hpp"),
                ),
              ).toBe(true);
            }
          }
        }
      } finally {
        search.cancel();
      }
    }, 60000);
  },
);
