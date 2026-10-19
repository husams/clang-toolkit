import { type ChildProcess, execFile, spawn } from "node:child_process";
import {
  mkdir,
  mkdtemp,
  readFile,
  realpath,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { promisify } from "node:util";
import { gunzipSync } from "node:zlib";
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
      spillRoot: string,
      first: string,
      second: string,
      broken: string,
      extraA: string,
      extraB: string,
      spillFile: string,
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
      spillRoot = resolve(directory, "workspace-spill");
      await mkdir(rootA);
      await mkdir(rootB);
      await mkdir(spillRoot);
      first = resolve(rootA, "first.cpp");
      second = resolve(rootB, "second.cpp");
      broken = resolve(rootA, "broken.cpp");
      extraA = resolve(rootA, "extra-a.cpp");
      extraB = resolve(rootB, "extra-b.cpp");
      spillFile = resolve(spillRoot, "spill.cpp");
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
      const largeContext = "x".repeat(64 * 1024);
      const spillSource = Array.from(
        { length: 80 },
        (_, index) =>
          `int spill_function_${String(index).padStart(3, "0")}() { static const char payload[] = "${largeContext}"; return payload[0]; }\n`,
      ).join("");
      await writeFile(spillFile, spillSource);
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
      await writeFile(
        resolve(spillRoot, "compile_commands.json"),
        JSON.stringify([
          {
            directory: spillRoot,
            file: spillFile,
            arguments: ["clang++", "-std=c++20", "-c", spillFile],
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
      if (report.completedFiles !== 4 || report.failedFiles !== 1)
        console.error(
          "Native batch failures:",
          JSON.stringify(report.fileStatuses),
        );
      expect(report.batch).toBe(true);
      expect(report.files).toBe(5);
      expect(report.completedFiles).toBe(4);
      expect(report.failedFiles).toBe(1);
      expect(report.attemptedFiles).toBe(5);
      expect(report.unattemptedFiles).toBe(0);
      expect(report.coverageComplete).toBe(true);
      expect(report.complete).toBe(false);
      expect(report.fileStatuses).toHaveLength(5);
      const canonicalBroken = await realpath(broken);
      expect(
        report.fileStatuses?.filter((file) => file.status === "succeeded"),
      ).toHaveLength(4);
      expect(
        report.fileStatuses?.find((file) => file.file === canonicalBroken)
          ?.status,
      ).toBe("failed");
      expect(report.fileStatuses?.every((file) => file.attempted)).toBe(true);
      const errors = report.errors ?? [];
      if (
        report.completedFiles !== 4 ||
        report.failedFiles !== 1 ||
        errors.length !== 1 ||
        errors[0]?.file !== canonicalBroken ||
        !errors[0]?.message.includes("missing_name")
      ) {
        console.error(
          "Unexpected batch outcome:",
          JSON.stringify({ fileStatuses: report.fileStatuses, errors }),
        );
      }
      expect(errors).toHaveLength(1);
      expect(errors[0]?.file).toBe(canonicalBroken);
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
      expect(capped.matches).toBe(capped.totalMatches);
      expect(capped.totalMatches).toBeGreaterThan(1);
      expect(capped.truncated).toBe(false);
      expect(capped.complete).toBe(true);
      expect(capped.coverageComplete).toBe(true);
      expect(capped.pageSize).toBe(1);
      expect(capped.hasMore).toBe(true);
      expect(capped.resultHandle).toBe(capped.runId);
      expect(capped.resultFile).toBeTruthy();
      const totalMatches = capped.totalMatches ?? capped.matches;
      const firstPageMatchIds = new Set(
        capped.results.map((item) => item.matchId),
      );
      expect(firstPageMatchIds.size).toBe(1);
      const secondPage = await service.pageActionResults(
        settings,
        capped.resultHandle!,
        1,
        1,
      );
      expect(secondPage.offset).toBe(1);
      expect(secondPage.totalMatches).toBe(capped.totalMatches);
      expect(new Set(secondPage.results.map((item) => item.matchId)).size).toBe(
        1,
      );
      expect(secondPage.results[0]?.matchId).not.toBe(
        capped.results[0]?.matchId,
      );
      expect(secondPage.results[0]?.detached).toBe(true);
      const secondPageResult = secondPage.results[0];
      expect(secondPageResult?.translationUnit).toBeTruthy();
      if (!secondPageResult?.translationUnit)
        throw new Error("Paged result lost its translation unit");
      const lastPage = await service.pageActionResults(
        settings,
        capped.resultHandle!,
        totalMatches - 1,
        1,
      );
      expect(lastPage.offset).toBe(totalMatches - 1);
      expect(lastPage.results.length).toBeGreaterThan(0);
      expect(
        lastPage.results.every(
          (item) => item.translationUnit && item.translationUnit.length > 0,
        ),
      ).toBe(true);
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

    it("spills all 80 large-context matches and pages to the final native result", async () => {
      await service.reset();
      const canonicalSpill = await realpath(spillFile);
      const spillSettings: ActionSettings = {
        ...settings,
        directory: spillRoot,
      };
      const report = await service.run(
        findFunctions,
        {},
        [spillFile],
        spillSettings,
        5,
        () => {},
        undefined,
        true,
        {
          [canonicalSpill]: {
            directory: spillRoot,
            compileArguments: [],
            compilationDatabase: resolve(spillRoot, "compile_commands.json"),
          },
        },
      );
      expect(report.matches).toBe(80);
      expect(report.totalMatches).toBe(80);
      expect(report.pageSize).toBe(5);
      expect(report.hasMore).toBe(true);
      expect(report.complete).toBe(true);
      expect(report.coverageComplete).toBe(true);
      expect(report.completedFiles).toBe(1);
      expect(report.failedFiles).toBe(0);
      expect(report.attemptedFiles).toBe(1);
      expect(report.unattemptedFiles).toBe(0);
      expect(report.fileStatuses).toHaveLength(1);
      expect(report.fileStatuses?.[0]).toMatchObject({
        file: canonicalSpill,
        status: "succeeded",
        attempted: true,
        totalMatches: 80,
      });
      if (!report.resultHandle || !report.resultFile)
        throw new Error(
          "Large result spill did not return its full result paths",
        );

      const resultBytes = await readFile(report.resultFile);
      const uncompressed = report.resultFile.endsWith(".gz")
        ? gunzipSync(resultBytes)
        : resultBytes;
      const diskRows = uncompressed
        .toString("utf8")
        .trim()
        .split("\n")
        .map(
          (line) =>
            JSON.parse(line) as {
              format: string;
              protobuf: string;
              matchId: string;
              translationUnit: string;
            },
        );
      expect(new Set(diskRows.map((row) => row.matchId))).toHaveLength(80);
      expect(
        diskRows.every((row) => row.translationUnit === canonicalSpill),
      ).toBe(true);
      expect(diskRows).toHaveLength(80);
      expect(
        diskRows.every(
          (row) =>
            row.format === "ctk-match-protobuf-v1" &&
            Buffer.from(row.protobuf, "base64").length > 0,
        ),
      ).toBe(true);
      const expectedFunctionNames = new Set(
        Array.from(
          { length: 80 },
          (_, index) => `spill_function_${String(index).padStart(3, "0")}`,
        ),
      );

      const pagedFunctionNames = new Set<string>();
      let hydratedBytes = 0;
      let finalPage:
        | Awaited<ReturnType<ActionService["pageActionResults"]>>
        | undefined;
      for (let offset = 0; offset < 80; offset += 5) {
        const page = await service.pageActionResults(
          spillSettings,
          report.resultHandle,
          offset,
          5,
        );
        expect(page.offset).toBe(offset);
        expect(page.totalMatches).toBe(80);
        expect(new Set(page.results.map((item) => item.matchId))).toHaveLength(
          5,
        );
        expect(page.hasMore).toBe(offset + 5 < 80);
        hydratedBytes += Buffer.byteLength(JSON.stringify(page.results));
        for (const item of page.results) {
          expect(item.translationUnit).toBe(canonicalSpill);
          if (item.binding === "function") pagedFunctionNames.add(item.name);
        }
        finalPage = page;
      }
      expect(pagedFunctionNames).toEqual(expectedFunctionNames);
      expect(hydratedBytes).toBeGreaterThan(1024 * 1024);
      if (!finalPage) throw new Error("Final results page was not fetched");
      const finalFunction = finalPage.results.find(
        (item) => item.binding === "function",
      );
      if (!finalFunction?.translationUnit)
        throw new Error("Final page lost the native translation-unit identity");
      const inspection = await service.inspect(spillSettings, {
        result: finalFunction,
        translationUnit: finalFunction.translationUnit,
      });
      expect(inspection.node.name).toBe(finalFunction.name);
      await service.reset();
      expect(await resourceStatus(endpoint)).toMatchObject({
        result_cursors: 0,
        active_work: 0,
        reserved_bytes: 0,
        opened_inputs: 0,
        explicit_file_leases: 0,
      });
    }, 120000);

    it("cancels an active file and releases its scope", async () => {
      await service.reset();
      const endless = parseNodeAction(
        "endless.ctk-action",
        "---\nname: endless\ndescription: Wait for cancellation\narguments: []\n---\nwhile true { continue }\n",
      );
      const cancellationProfiles = {
        [await realpath(extraB)]: {
          directory: rootB,
          compileArguments: [],
          compilationDatabase: resolve(rootB, "compile_commands.json"),
        },
      };
      const running = service.run(
        endless,
        {},
        [extraB],
        settings,
        5,
        (text) => {
          if (text.includes("extra-b.cpp") && !text.includes("completed"))
            setTimeout(() => service.cancel(), 300);
        },
        undefined,
        true,
        cancellationProfiles,
      );
      const partial = await running;
      expect(partial.cancelled).toBe(true);
      expect(partial.complete).toBe(false);
      expect(partial.coverageComplete).toBe(false);
      expect(partial.attemptedFiles).toBe(1);
      expect(partial.unattemptedFiles).toBe(0);
      expect(partial.fileStatuses).toHaveLength(1);
      expect(partial.fileStatuses?.[0]).toMatchObject({
        file: await realpath(extraB),
        status: "cancelled",
        attempted: true,
      });
      if (!partial.resultHandle || !partial.resultFile)
        throw new Error("Cancelled run did not retain its partial results");
      expect((await stat(partial.resultFile)).isFile()).toBe(true);
      const partialPage = await service.pageActionResults(
        settings,
        partial.resultHandle,
        0,
        5,
      );
      expect(partialPage.totalMatches).toBe(partial.totalMatches);
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
