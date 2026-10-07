import { type ChildProcess, spawn } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { credentials, status } from "@grpc/grpc-js";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { handleOwner } from "../src/cursor-handle.js";
import { GrpcTransport } from "../src/grpc-transport.js";
import { Client, type MatchValue, type ParsedTree } from "../src/index.js";

const live = process.env.CTK_INTEGRATION === "1";
async function port(): Promise<number> {
  const server = createServer();
  await new Promise<void>((resolveReady, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolveReady);
  });
  const address = server.address();
  if (!address || typeof address === "string")
    throw new Error("cannot allocate test TCP port");
  await new Promise<void>((resolveClosed, reject) =>
    server.close((error) => (error ? reject(error) : resolveClosed())),
  );
  return address.port;
}

for (const transport of ["unix", "tcp"] as const) {
  describe.skipIf(!live)(`native server over ${transport}`, () => {
    let directory: string;
    let endpoint: string;
    let configPath: string;
    let processHandle: ChildProcess;
    let logs = "";
    beforeAll(async () => {
      directory = await mkdtemp(resolve(tmpdir(), "ctk-ts-"));
      await writeFile(
        resolve(directory, "fixture.cc"),
        "int one(){return 1;} int two(){return one()+2;} int three(){return one()+two()+3;}",
      );
      await writeFile(resolve(directory, "second.cc"), "int only(){return 9;}");
      await writeFile(
        resolve(directory, "profile.cc"),
        "#ifdef CTK_TS_PROFILE\nint profile_enabled() { return 1; }\n#else\nint profile_disabled() { return 0; }\n#endif\n",
      );
      await mkdir(resolve(directory, "storage"));
      const socket = resolve(directory, "server.sock");
      const selectedPort = await port();
      endpoint =
        transport === "unix" ? `unix://${socket}` : `127.0.0.1:${selectedPort}`;
      const network =
        transport === "unix"
          ? `network:\n  transport: unix\n  unix:\n    socket_path: ${socket}\n`
          : `network:\n  transport: tcp\n  tcp:\n    host: 127.0.0.1\n    port: ${selectedPort}\n`;
      configPath = resolve(directory, "server.yaml");
      await writeFile(configPath, network);
      await writeFile(resolve(directory, "clang-toolkit.yaml"), network);
      processHandle = spawn(
        resolve(process.cwd(), "../build/dev/server/ctk-server"),
        ["-c", configPath],
        {
          env: {
            ...process.env,
            CTK_STORAGE_ROOT: resolve(directory, "storage"),
          },
          stdio: ["ignore", "pipe", "pipe"],
        },
      );
      processHandle.stdout?.on("data", (data: Buffer) => {
        logs += data.toString();
      });
      processHandle.stderr?.on("data", (data: Buffer) => {
        logs += data.toString();
      });
      const client = new Client(endpoint);
      try {
        await client.ready(15_000);
      } catch (error) {
        throw new Error(`server did not become ready: ${logs}`, {
          cause: error,
        });
      } finally {
        await client.close();
      }
    }, 25_000);

    afterAll(async () => {
      if (processHandle && processHandle.exitCode === null) {
        const exit = new Promise<void>((resolveExit) =>
          processHandle.once("exit", () => resolveExit()),
        );
        processHandle.kill("SIGTERM");
        await exit;
      }
      if (directory) await rm(directory, { recursive: true, force: true });
    });

    function client(): Client {
      return new Client(endpoint, {
        workingDirectory: directory,
        credentials: credentials.createInsecure(),
      });
    }

    it("captures roots and named bindings from large included results", async () => {
      const source = resolve(directory, "large.cc");
      await writeFile(
        resolve(directory, "large.hpp"),
        Array.from({ length: 3000 }, (_, index) =>
          `void function_${index}_${"x".repeat(1000)}();`,
        ).join("\n"),
      );
      await writeFile(source, '#include "large.hpp"\nvoid source_function();\n');
      await using connected = client();
      await using tree = await connected.parse(source);
      await using rows = await connected.match('functionDecl().bind("x")', tree);
      expect(rows.length).toBe(3001);
      expect(Object.keys(rows.rows[0]?.bindings ?? {}).sort()).toEqual(["root", "x"]);
      await using roots = await connected.match("functionDecl()", tree);
      expect(roots.length).toBe(3001);
      expect(Object.keys(roots.rows[0]?.bindings ?? {})).toEqual(["root"]);
    }, 20_000);

    it("connects from shared discovery and an optional config path without an address", async () => {
      await using configured = await Client.connect({
        configPath,
        workingDirectory: directory,
      });
      expect(configured.endpoint).toBe(endpoint);
      expect(
        (await configured.match("functionDecl()", "fixture.cc")).length,
      ).toBe(3);
      await using constructed = new Client({
        configPath,
        workingDirectory: directory,
      });
      expect((await constructed.parse("fixture.cc")).closed).toBe(false);

      const moduleUrl = pathToFileURL(
        resolve(process.cwd(), "dist/index.js"),
      ).href;
      const child = spawn(
        process.execPath,
        [
          "--input-type=module",
          "-e",
          `import { Client } from ${JSON.stringify(moduleUrl)};
           const client = await Client.connect();
           try {
             const functions = await client.match('functionDecl()', 'fixture.cc');
             console.log(JSON.stringify({ endpoint: client.endpoint, length: functions.length }));
           } finally { await client.close(); }`,
        ],
        { cwd: directory, stdio: ["ignore", "pipe", "pipe"] },
      );
      let output = "";
      let errors = "";
      child.stdout?.on("data", (data: Buffer) => {
        output += data.toString();
      });
      child.stderr?.on("data", (data: Buffer) => {
        errors += data.toString();
      });
      const exit = await new Promise<number | null>((resolveExit, reject) => {
        child.once("error", reject);
        child.once("exit", resolveExit);
      });
      expect(exit, errors).toBe(0);
      expect(JSON.parse(output)).toEqual({ endpoint, length: 3 });
    });

    it("applies YAML gRPC limits and preserves explicit channel overrides", async () => {
      const limitedConfig = resolve(directory, "limited.yaml");
      await writeFile(
        limitedConfig,
        "client:\n  grpc:\n    max_receive_message_bytes: 1\n  rpc_timeout_ms: 20000\n",
      );
      const discovery = {
        cwd: directory,
        home: directory,
        configPath: limitedConfig,
      };
      await using limited = await Client.connect(discovery);
      await expect(
        limited.parse("fixture.cc", { workingDirectory: directory }),
      ).rejects.toMatchObject({
        code: status.RESOURCE_EXHAUSTED,
      });
      await using overridden = await Client.connect({
        ...discovery,
        channelOptions: { "grpc.max_receive_message_length": 1_048_576 },
        workingDirectory: directory,
      });
      expect(
        (await overridden.match("functionDecl()", "fixture.cc")).length,
      ).toBe(3);
    });

    it("loads automatic and explicit databases and refreshes changed commands", async () => {
      const project = resolve(directory, "database-project");
      const build = resolve(project, "build");
      await mkdir(resolve(build, "include with spaces"), { recursive: true });
      await writeFile(
        resolve(build, "include with spaces/profile.hpp"),
        "#define HEADER_VALUE 17\n",
      );
      const file = resolve(project, "profile.cc");
      await writeFile(
        file,
        "#include <profile.hpp>\nstatic_assert(HEADER_VALUE == 17);\n#if VALUE == 1\nint before(){return 1;}\n#else\nint after(){return 2;}\n#endif\n",
      );
      const command = {
        directory: build,
        file: "../profile.cc",
        arguments: [
          "clang++",
          "-std=c++20",
          "-Iinclude with spaces",
          "-DVALUE=1",
          "-c",
          "../profile.cc",
          "-o",
          "unused.o",
        ],
      };
      const database = resolve(build, "compile_commands.json");
      await writeFile(database, JSON.stringify([command]));
      await using client = new Client(endpoint);
      await using automatic = await client.parse(file);
      await using before = await client.match(
        'functionDecl(hasName("before")).bind("f")',
        automatic,
      );
      expect(before.length).toBe(1);
      await using explicitClient = new Client(endpoint, {
        compilationDatabase: database,
      });
      await using explicit = await explicitClient.parse(file);
      command.arguments[3] = "-DVALUE=22";
      await writeFile(database, JSON.stringify([command]));
      await using updated = await client.match(
        'functionDecl(hasName("after")).bind("f")',
        file,
        { compilationDatabase: build },
      );
      expect(updated.length).toBe(1);
      await using pinned = await explicitClient.match(
        'functionDecl(hasName("before")).bind("f")',
        explicit,
      );
      expect(pinned.length).toBe(1);
    });

    it("parses once, forks immutable all/indexed bindings, and survives parent close", async () => {
      await using sdk = client();
      const tree = await sdk.parse("fixture.cc");
      const functions = await sdk.match(
        'functionDecl(isDefinition()).bind("f")',
        tree,
      );
      expect(functions.length).toBe(3);
      const all = await sdk.match(
        'callExpr().bind("call")',
        functions.binding("f"),
      );
      expect(all.length).toBe(3);
      const first = await sdk.match(
        'integerLiteral().bind("n")',
        functions.row(0).binding("f"),
      );
      expect(first.length).toBe(1);
      const duplicate = await sdk.match(
        'callExpr().bind("call")',
        functions.binding("f"),
      );
      expect(duplicate.rows).toEqual(all.rows);
      expect(functions.length).toBe(3);
      await tree.close();
      const child = await sdk.match(
        'declRefExpr().bind("ref")',
        all.binding("call"),
      );
      expect(child.length).toBe(3);
      await functions.close();
      expect(
        (await sdk.match('declRefExpr().bind("ref")', all.binding("call")))
          .length,
      ).toBe(3);
    });

    it("matches explicit files independently and pins generation despite source changes", async () => {
      await using sdk = client();
      const tree = await sdk.parse("fixture.cc");
      expect((await sdk.match("functionDecl()", "second.cc")).length).toBe(1);
      await writeFile(
        resolve(directory, "fixture.cc"),
        "int replacement(){return 99;}",
      );
      try {
        expect((await sdk.match("functionDecl()", tree)).length).toBe(3);
        expect((await sdk.match("functionDecl()", "fixture.cc")).length).toBe(
          1,
        );
      } finally {
        await writeFile(
          resolve(directory, "fixture.cc"),
          "int one(){return 1;} int two(){return one()+2;} int three(){return one()+two()+3;}",
        );
      }
    });

    it("continues empty collections, reports structured errors and preserves source", async () => {
      await using sdk = client();
      const tree = await sdk.parse("fixture.cc");
      const empty = await sdk.match('cxxRecordDecl().bind("record")', tree);
      expect(
        (await sdk.match('fieldDecl().bind("field")', empty.binding("record")))
          .length,
      ).toBe(0);
      const functions = await sdk.match('functionDecl().bind("f")', tree);
      await expect(
        sdk.match("callExpr()", functions.binding("missing")),
      ).rejects.toMatchObject({ code: status.NOT_FOUND });
      expect(() => functions.row(3)).toThrow();
      await expect(
        sdk.match("unknownNativeMatcher()", tree),
      ).rejects.toMatchObject({ code: status.INVALID_ARGUMENT });
      expect((await sdk.match("functionDecl()", tree)).length).toBe(3);
      await tree.close();
      expect(() => sdk.match("functionDecl()", tree)).toThrow(
        expect.objectContaining({ code: status.FAILED_PRECONDITION }),
      );
    });

    it("returns reusable scoped matches and selections, closes locals, and cleans failures", async () => {
      await using sdk = client();
      let local: MatchValue | undefined;
      let scopedTree: ParsedTree | undefined;
      const calls = await sdk.withTree("fixture.cc", async (scope) => {
        scopedTree = scope.tree;
        local = await scope.match('functionDecl().bind("f")');
        return scope.match('callExpr().bind("call")', local.binding("f"));
      });
      expect(local?.closed).toBe(true);
      expect(scopedTree?.closed).toBe(true);
      expect(calls.closed).toBe(false);
      expect(
        (await sdk.match('declRefExpr().bind("ref")', calls.binding("call")))
          .length,
      ).toBe(3);
      const selection = await sdk.withTree("fixture.cc", async (scope) =>
        (await scope.match('functionDecl().bind("f")')).row(0).binding("f"),
      );
      expect((await sdk.match("integerLiteral()", selection)).length).toBe(1);
      let failedTree: ParsedTree | undefined;
      await expect(
        sdk.withTree("fixture.cc", async (scope) => {
          failedTree = scope.tree;
          await scope.match("badMatcher()");
          return calls;
        }),
      ).rejects.toMatchObject({ code: status.INVALID_ARGUMENT });
      expect(failedTree?.closed).toBe(true);
      expect(calls.closed).toBe(false);
    });

    it("executes native scoped text atomically with detached emitted semantics", async () => {
      await using sdk = client();
      const result = await sdk.runScript(
        `let analysis = in parse "fixture.cc" {
        let functions = match functionDecl(isDefinition()).bind("f");
        let calls = match callExpr().bind("call") in $functions.f;
        yield calls;
      }; let more = match declRefExpr().bind("ref") in $analysis.call; emit more;`,
        { file: "fixture.cc" },
      );
      expect(result.emissions[0]?.value?.matches?.rows.length).toBe(3);
      expect(Object.isFrozen(result.emissions)).toBe(true);
      await expect(
        sdk.runScript(
          'emit 7; let analysis = in parse "fixture.cc" { yield missing; };',
          { file: "fixture.cc" },
        ),
      ).rejects.toMatchObject({ code: status.INVALID_ARGUMENT });
      expect(
        (await sdk.runScript("emit 8;")).emissions[0]?.value?.scalar?.integer,
      ).toBe("8");
    });

    it("applies the client compilation profile to explicit script parses", async () => {
      await using sdk = new Client(endpoint, {
        workingDirectory: directory,
        compileArguments: ["-DCTK_TS_PROFILE"],
        credentials: credentials.createInsecure(),
      });
      const result = await sdk.runScript(
        `let analysis = in parse "profile.cc" {
          let functions = match functionDecl(isDefinition(), hasName("profile_enabled")).bind("function");
          yield functions;
        }; emit analysis;`,
      );
      expect(result.emissions[0]?.value?.matches?.rows).toHaveLength(1);
    });

    it("releases a local yield when a pending scoped operation fails", async () => {
      await using sdk = client();
      let selected: MatchValue | undefined;
      await expect(
        sdk.withTree("fixture.cc", async (scope) => {
          selected = await scope.match('functionDecl().bind("f")');
          scope.match("unknownBackgroundMatcher()");
          return selected;
        }),
      ).rejects.toBeInstanceOf(AggregateError);
      expect(selected?.closed).toBe(true);
    });

    it("releases every session on close and handles repeated scope cleanup", async () => {
      const sdk = client();
      const tree = await sdk.parse("fixture.cc");
      const sessionId = tree[handleOwner].sessionId;
      for (let index = 0; index < 105; index++) {
        const value = await sdk.withTree("fixture.cc", (scope) =>
          scope.match("functionDecl()"),
        );
        await value.close();
      }
      await sdk.close();
      await sdk.close();
      const wire = new GrpcTransport(endpoint, {});
      try {
        await expect(
          wire.invoke((metadata, options, callback) =>
            wire.matches.Match(
              { query: "functionDecl()", session: { sessionId } },
              metadata,
              options,
              callback,
            ),
          ),
        ).rejects.toMatchObject({ code: status.NOT_FOUND });
      } finally {
        wire.close();
      }
      expect(tree.closed).toBe(true);
    }, 30_000);
  });
}
