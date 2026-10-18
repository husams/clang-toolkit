import { type ChildProcess, execFile, spawn } from "node:child_process";
import { mkdir, mkdtemp, realpath, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { promisify } from "node:util";
import { Client } from "@clang-toolkit/sdk";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { ActionService, type ActionSettings } from "../src/action-service.js";
import { parseNodeAction } from "../src/actions.js";

describe.skipIf(process.env.CTK_INTEGRATION !== "1")(
  "batched retained node actions",
  () => {
    let directory: string,
      rootA: string,
      rootB: string,
      first: string,
      second: string,
      broken: string,
      extraA: string,
      extraB: string,
      header: string,
      socket: string,
      endpoint: string,
      server: ChildProcess,
      settings: ActionSettings,
      service: ActionService;

    beforeAll(async () => {
      directory = await mkdtemp(resolve(tmpdir(), "ctk-actions-batch-"));
      await mkdir(resolve(directory, "lib"));
      rootA = resolve(directory, "workspace-a");
      rootB = resolve(directory, "workspace-b");
      await mkdir(rootA);
      await mkdir(rootB);
      first = resolve(rootA, "first.cpp");
      second = resolve(rootB, "second.cpp");
      broken = resolve(rootA, "broken.cpp");
      extraA = resolve(rootA, "extra-a.cpp");
      extraB = resolve(rootB, "extra-b.cpp");
      header = resolve(rootA, "shared.hpp");
      const headerB = resolve(rootB, "shared.hpp");
      await writeFile(header, "inline int sharedA() { return 3; }\n");
      await writeFile(headerB, "inline int sharedB() { return 4; }\n");
      await writeFile(
        first,
        '#include "shared.hpp"\n#ifdef PROFILE_A\nint fromProfileA() { return sharedA(); }\n#else\n#error PROFILE_A was not applied\n#endif\n',
      );
      await writeFile(
        second,
        '#include "shared.hpp"\n#ifdef PROFILE_B\nint fromProfileB() { return sharedB(); }\n#else\n#error PROFILE_B was not applied\n#endif\n',
      );
      await writeFile(
        broken,
        "int brokenFunction() { return missing_name; }\n",
      );
      await writeFile(extraA, "int extraA() { return 5; }\n");
      await writeFile(extraB, "int extraB() { return 6; }\n");
      await writeFile(
        resolve(rootA, "compile_commands.json"),
        JSON.stringify([
          {
            directory: rootA,
            file: first,
            arguments: ["clang++", "-std=c++20", "-DPROFILE_A", "-c", first],
          },
          {
            directory: rootA,
            file: broken,
            arguments: ["clang++", "-std=c++20", "-DPROFILE_A", "-c", broken],
          },
          {
            directory: rootA,
            file: extraA,
            arguments: ["clang++", "-std=c++20", "-DPROFILE_A", "-c", extraA],
          },
        ]),
      );
      await writeFile(
        resolve(rootB, "compile_commands.json"),
        JSON.stringify([
          {
            directory: rootB,
            file: second,
            arguments: ["clang++", "-std=c++20", "-DPROFILE_B", "-c", second],
          },
          {
            directory: rootB,
            file: extraB,
            arguments: ["clang++", "-std=c++20", "-DPROFILE_B", "-c", extraB],
          },
        ]),
      );
      socket = resolve(`/private/tmp/ctk-batch-${process.pid}.sock`);
      endpoint = `unix://${socket}`;
      const config = resolve(directory, "server.yaml");
      await writeFile(
        config,
        `network:\n  transport: unix\n  unix:\n    socket_path: ${socket}\nsession:\n  max_files: 4\n`,
      );
      server = spawn(
        process.env.CTK_SERVER ?? resolve("../build/dev/server/ctk-server"),
        ["-c", config],
        {
          env: {
            ...process.env,
            CTK_STORAGE_ROOT: resolve(directory, "storage"),
          },
          stdio: "ignore",
        },
      );
      const client = new Client(endpoint);
      try {
        await client.ready(15000);
      } finally {
        await client.close();
      }
      settings = {
        directory,
        endpoint,
        libraryDirectory: resolve(directory, "lib"),
        timeoutMs: 90000,
        compileArguments: ["-std=c++20"],
      };
      service = new ActionService(
        resolve("console/action_service.py"),
        process.env.CTK_PYTHON ?? resolve("../.venv/bin/python"),
      );
    }, 20000);

    afterAll(async () => {
      service?.dispose();
      if (server?.exitCode === null) {
        const exit = new Promise((done) => server.once("exit", done));
        server.kill();
        await exit;
      }
      if (socket) await rm(socket, { force: true });
      if (directory) await rm(directory, { recursive: true, force: true });
    });

    const findFunctions = parseNodeAction(
      "functions.ctk-action",
      '---\nname: functions\ndescription: Find functions\narguments: []\n---\nmatch functionDecl(isDefinition()).bind("function") in node\n',
    );

    it("releases each file scope and returns inspectable detached matches", async () => {
      const profiles = {
        [await realpath(first)]: {
          directory: rootA,
          compileArguments: [],
          compilationDatabase: resolve(rootA, "compile_commands.json"),
        },
        [await realpath(broken)]: {
          directory: rootA,
          compileArguments: [],
          compilationDatabase: resolve(rootA, "compile_commands.json"),
        },
        [await realpath(extraA)]: {
          directory: rootA,
          compileArguments: [],
          compilationDatabase: resolve(rootA, "compile_commands.json"),
        },
        [await realpath(second)]: {
          directory: rootB,
          compileArguments: [],
          compilationDatabase: resolve(rootB, "compile_commands.json"),
        },
        [await realpath(extraB)]: {
          directory: rootB,
          compileArguments: [],
          compilationDatabase: resolve(rootB, "compile_commands.json"),
        },
      };
      const report = await service.run(
        findFunctions,
        {},
        [first, broken, second, extraA, extraB],
        settings,
        100,
        () => {},
        undefined,
        true,
        profiles,
      );
      expect(report.batch).toBe(true);
      expect(report.files).toBe(5);
      const errors = report.errors ?? [];
      expect(errors).toHaveLength(1);
      expect(errors[0]?.file).toBe(await realpath(broken));
      expect(errors[0]?.message).toContain("missing_name");
      expect(report.parseCount).toBe(4);
      expect(report.results.map((item) => item.name)).toEqual(
        expect.arrayContaining([
          "fromProfileA",
          "fromProfileB",
          "sharedA",
          "sharedB",
          "extraA",
          "extraB",
        ]),
      );
      const canonicalHeader = await realpath(header);
      const canonicalFirst = await realpath(first);
      expect(
        report.results.some(
          (item) =>
            item.file === canonicalHeader &&
            item.translationUnit === canonicalFirst,
        ),
      ).toBe(true);
      const canonicalHeaderB = await realpath(resolve(rootB, "shared.hpp"));
      const canonicalSecond = await realpath(second);
      expect(
        report.results.some(
          (item) =>
            item.file === canonicalHeaderB &&
            item.translationUnit === canonicalSecond,
        ),
      ).toBe(true);
      const cleared = await resourceStatus(endpoint);
      expect(cleared).toMatchObject({
        result_cursors: 0,
        active_work: 0,
        reserved_bytes: 0,
        opened_inputs: 0,
        explicit_file_leases: 0,
      });
      const capped = await service.run(
        findFunctions,
        {},
        [first, second],
        settings,
        1,
        () => {},
        undefined,
        true,
        profiles,
      );
      expect(capped.matches).toBe(1);
      expect(capped.truncated).toBe(true);
      expect(await resourceStatus(endpoint)).toMatchObject({
        result_cursors: 0,
        active_work: 0,
        reserved_bytes: 0,
      });

      const result = report.results.find(
        (item) => item.name === "fromProfileB",
      );
      if (!result) throw new Error("Missing second-root result");
      {
        expect(result.detached).toBe(true);
        const translationUnit = result.translationUnit;
        expect(translationUnit).toBe(result.file);
        if (!translationUnit) throw new Error("Missing translation unit");
        const inspected = await service.inspect(settings, {
          result,
          translationUnit,
        });
        expect(inspected.node.name).toBe(result.name);
      }
      await service.reset();
      expect(await resourceStatus(endpoint)).toMatchObject({
        result_cursors: 0,
        active_work: 0,
        reserved_bytes: 0,
      });
    }, 60000);

    it("cancels an active file group and releases its scope", async () => {
      const endless = parseNodeAction(
        "endless.ctk-action",
        "---\nname: endless\ndescription: Wait for cancellation\narguments: []\n---\nwhile true { continue }\n",
      );
      const running = service.run(
        endless,
        {},
        [first],
        settings,
        100,
        () => service.cancel(),
        undefined,
        true,
      );
      await expect(running).rejects.toThrow(/cancel/i);
      expect(await resourceStatus(endpoint)).toMatchObject({
        result_cursors: 0,
        active_work: 0,
        reserved_bytes: 0,
        opened_inputs: 0,
      });
    }, 60000);
  },
);

const execFileAsync = promisify(execFile);
async function resourceStatus(
  endpoint: string,
): Promise<Record<string, number>> {
  const python = process.env.CTK_PYTHON ?? resolve("../.venv/bin/python");
  const script = [
    "import json, sys",
    "from clang_toolkit.client import Client",
    "client = Client(sys.argv[1])",
    "try:",
    " status = client.resource_status()",
    " print(json.dumps({name: getattr(status, name) for name in ('result_cursors', 'active_work', 'reserved_bytes', 'opened_inputs', 'explicit_file_leases')}))",
    "finally:",
    " client.close()",
  ].join("\n");
  const { stdout } = await execFileAsync(python, ["-c", script, endpoint]);
  return JSON.parse(stdout) as Record<string, number>;
}
