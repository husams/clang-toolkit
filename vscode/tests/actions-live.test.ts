import { type ChildProcess, spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { Client } from "@clang-toolkit/sdk";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { ActionService, type ActionSettings } from "../src/action-service.js";
import { parseNodeAction, resolveArguments } from "../src/actions.js";

describe.skipIf(process.env.CTK_INTEGRATION !== "1")(
  "retained node actions",
  () => {
    let directory: string,
      file: string,
      server: ChildProcess,
      settings: ActionSettings;
    const services: ActionService[] = [];
    beforeAll(async () => {
      directory = await mkdtemp(resolve(tmpdir(), "ctk-actions-"));
      await mkdir(resolve(directory, "lib"));
      await writeFile(
        resolve(directory, "lib/helpers.ctk"),
        "let namedFunction(name) = functionDecl(hasName(name))",
      );
      file = resolve(directory, "demo.cpp");
      await writeFile(
        file,
        "int adjust(int value) { return value + 1; }\nint processOrder(int quantity) { return adjust(quantity); }\nint unrelated() { return 0; }\n",
      );
      const endpoint = `unix://${directory}/server.sock`,
        config = resolve(directory, "server.yaml");
      await writeFile(
        config,
        `network:\n  transport: unix\n  unix:\n    socket_path: ${directory}/server.sock\n`,
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
        timeoutMs: 30000,
        compileArguments: ["-std=c++20"],
      };
    }, 20000);
    afterAll(async () => {
      for (const service of services) service.dispose();
      if (server?.exitCode === null) {
        const exit = new Promise((done) => server.once("exit", done));
        server.kill();
        await exit;
      }
      if (directory) await rm(directory, { recursive: true, force: true });
    });
    const service = () => {
      const host = new ActionService(
        resolve("console/action_service.py"),
        process.env.CTK_PYTHON ?? resolve("../.venv/bin/python"),
      );
      services.push(host);
      return host;
    };
    const action = (name: string, body: string) =>
      parseNodeAction(
        `${name}.ctk-action`,
        `---\nname: ${name}\ndescription: Test action\narguments: []\n---\n${body}`,
      );
    it("reuses the parsed root and exact binding, preserves multi-binding rows and earlier results after errors", async () => {
      const host = service();
      const functions = parseNodeAction(
        "find-function.ctk-action",
        await readFile("actions/find-function.ctk-action", "utf8"),
      );
      const calls = parseNodeAction(
        "find-calls.ctk-action",
        await readFile("actions/find-calls.ctk-action", "utf8"),
      );
      const first = await host.run(
        functions,
        resolveArguments(functions, {}),
        [file],
        settings,
        100,
      );
      expect(first.parseCount).toBe(1);
      expect(first.matches).toBe(3);
      const node = first.results.find(
        (r) => r.binding === "function" && r.name === "processOrder",
      );
      expect(node, JSON.stringify(first)).toBeDefined();
      const second = await host.run(
        calls,
        {},
        [file],
        settings,
        100,
        () => {},
        node!.nodeId,
      );
      expect(second.parseCount).toBe(1);
      expect(second.matches).toBe(1);
      expect(
        second.results.some(
          (r) => r.binding === "call" && r.excerpt.includes("adjust(quantity)"),
        ),
      ).toBe(true);
      const multi = await host.run(
        action(
          "related",
          'match functionDecl(hasName("processOrder"), hasDescendant(callExpr().bind("call"))).bind("function") in node',
        ),
        {},
        [file],
        settings,
        100,
        () => {},
        first.input.id,
      );
      expect(multi.matches).toBe(1);
      expect(multi.results.map((r) => r.binding)).toEqual(
        expect.arrayContaining(["call", "function"]),
      );
      expect(new Set(multi.results.map((r) => r.matchId)).size).toBe(1);
      expect(new Set(multi.results.map((r) => r.nodeId)).size).toBe(
        multi.results.length,
      );
      await expect(
        host.run(
          action("bad-return", "42"),
          {},
          [file],
          settings,
          100,
          () => {},
          node!.nodeId,
        ),
      ).rejects.toThrow("must return retained CTK matches");
      const reused = await host.run(
        calls,
        {},
        [file],
        settings,
        100,
        () => {},
        node!.nodeId,
      );
      expect(reused.matches).toBe(1);
      expect(reused.parseCount).toBe(1);
      const helper = await host.run(
        action(
          "helper",
          'match namedFunction("processOrder").bind("function") in node',
        ),
        {},
        [file],
        settings,
        100,
        () => {},
        first.input.id,
      );
      expect(helper.matches).toBe(1);
      await host.reset();
      await expect(
        host.run(calls, {}, [file], settings, 100, () => {}, node!.nodeId),
      ).rejects.toThrow("expired");
    }, 60000);
    it.runIf(process.env.CTK_TEST_DEFAULT_LIBRARY === "1")(
      "also starts with the user's normal console helper preload",
      async () => {
        const host = service();
        const { libraryDirectory: _library, ...defaults } = settings;
        const report = await host.run(
          action(
            "normal-helpers",
            'match functionDecl(isDefinition()).bind("function") in node',
          ),
          {},
          [file],
          defaults,
          100,
        );
        expect(report.matches).toBeGreaterThan(0);
      },
      60000,
    );
    it("cancels a console loop without losing live nodes and rejects source changes until refresh", async () => {
      const host = service(),
        find = action(
          "functions",
          'match functionDecl(isDefinition()).bind("function") in node',
        );
      const first = await host.run(find, {}, [file], settings, 100);
      let started!: () => void;
      const running = new Promise<void>((resolve) => {
        started = resolve;
      });
      const infinite = host.run(
        action("loop", "while true { continue }"),
        {},
        [file],
        settings,
        100,
        () => started(),
        first.input.id,
      );
      const stopped = infinite.then(
        () => new Error("Unexpected success"),
        (error: unknown) => error,
      );
      await running;
      host.cancel();
      expect(String(await stopped)).toContain("cancelled");
      expect(
        (
          await host.run(
            find,
            {},
            [file],
            settings,
            1,
            () => {},
            first.input.id,
          )
        ).truncated,
      ).toBe(true);
      await writeFile(file, "int changed() { return 1; }");
      await expect(
        host.run(find, {}, [file], settings, 100, () => {}, first.input.id),
      ).rejects.toThrow("Source changed");
      await host.reset();
      const refreshed = await host.run(find, {}, [file], settings, 100);
      expect(refreshed.parseCount).toBe(1);
      expect(refreshed.results.some((r) => r.name === "changed")).toBe(true);
    }, 60000);
  },
);
