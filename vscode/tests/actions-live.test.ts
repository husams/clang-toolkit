import { type ChildProcess, spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { Client } from "@clang-toolkit/sdk";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { ActionService, type ActionSettings } from "../src/action-service.js";
import { parseNodeAction, resolveArguments } from "../src/actions.js";
import { astDisplay } from "../src/ast-model.js";

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
    it("resolves source selections to native nodes across the parsed file without reparsing", async () => {
      const host = service();
      const found = await host.run(
        action(
          "source-functions",
          'match functionDecl(isDefinition()).bind("function") in node',
        ),
        {},
        [file],
        settings,
        100,
      );
      const reference = found.results.find(
        (node) => node.name === "processOrder",
      )!;
      const text = await readFile(file, "utf8");
      const select = (code: string, last = false) => {
        const index = last ? text.lastIndexOf(code) : text.indexOf(code);
        expect(index).toBeGreaterThanOrEqual(0);
        return host.selectSource(settings, reference.nodeId, {
          file,
          start: Buffer.byteLength(text.slice(0, index)),
          end: Buffer.byteLength(text.slice(0, index + code.length)),
        });
      };
      const call = await select("adjust(quantity)");
      expect(call, "an exact call selection must resolve").toBeDefined();
      expect(astDisplay(call!.node).kind).toBe("CallExpr");
      expect(call!.parseCount).toBe(1);
      const argument = await select("quantity", true);
      expect(astDisplay(argument!.node).kind).toBe("DeclRefExpr");
      const returned = await select("return adjust(quantity)");
      expect(astDisplay(returned!.node).kind).toBe("ReturnStmt");
      const otherFunction = await select("int unrelated() { return 0; }");
      expect(astDisplay(otherFunction!.node).kind).toBe("FunctionDecl");
      expect(otherFunction!.node.name).toBe("unrelated");
      const repeated = await select("adjust(quantity)");
      expect(repeated!.node.id).toBe(call!.node.id);
      const cursor = (offset: number) =>
        host.selectSource(settings, reference.nodeId, {
          file,
          start: offset,
          end: offset,
        });
      const atArgument = await cursor(text.lastIndexOf("quantity") + 2);
      expect(atArgument!.node.id).toBe(argument!.node.id);
      const atCallParenthesis = await cursor(text.lastIndexOf("adjust(") + 6);
      expect(atCallParenthesis!.node.id).toBe(call!.node.id);
      const atFileStart = await cursor(0);
      expect(astDisplay(atFileStart!.node).kind).toBe("FunctionDecl");
      expect(atFileStart!.node.name).toBe("adjust");
      expect(await cursor(text.length)).toBeUndefined();
      const followed = await host.run(
        action("selected-calls", 'match callExpr().bind("call") in node'),
        {},
        [file],
        settings,
        100,
        () => {},
        call!.node.id,
      );
      expect(followed.input.id).toBe(call!.node.id);
      expect(followed.matches).toBe(1);
      expect(followed.parseCount).toBe(1);
      const newline = text.indexOf("\n");
      expect(
        await host.selectSource(settings, reference.nodeId, {
          file,
          start: newline,
          end: newline + 1,
        }),
      ).toBeUndefined();
      await host.reset();
      await expect(select("quantity", true)).rejects.toThrow(/expired/);
    }, 60000);
    it("resolves UTF-8 selections in paths containing regex metacharacters", async () => {
      const host = service();
      const unicodeFile = resolve(directory, "source [1].cpp");
      const text = "// café 😀\nint unicode() { return 42; }\n";
      await writeFile(unicodeFile, text);
      const first = await host.run(
        action(
          "unicode-source",
          'match functionDecl().bind("function") in node',
        ),
        {},
        [unicodeFile],
        settings,
        100,
      );
      const start = Buffer.byteLength(text.slice(0, text.indexOf("42")));
      const selected = await host.selectSource(
        settings,
        first.results[0]!.nodeId,
        { file: unicodeFile, start, end: start + 2 },
      );
      expect(selected).toBeDefined();
      expect(astDisplay(selected!.node).kind).toBe("IntegerLiteral");
      expect(astDisplay(selected!.node).properties).toContainEqual({
        label: "Literal value",
        value: "42",
      });
      expect(selected!.parseCount).toBe(1);
      const atLiteral = await host.selectSource(
        settings,
        first.results[0]!.nodeId,
        { file: unicodeFile, start: start + 1, end: start + 1 },
      );
      expect(atLiteral!.node.id).toBe(selected!.node.id);
      const afterLiteral = await host.selectSource(
        settings,
        first.results[0]!.nodeId,
        { file: unicodeFile, start: start + 2, end: start + 2 },
      );
      expect(astDisplay(afterLiteral!.node).kind).toBe("CompoundStmt");
      expect(afterLiteral!.parseCount).toBe(1);
    }, 60000);
    it("inspects actual AST children, reuses native handles and rejects stale navigation", async () => {
      const host = service();
      const first = await host.run(
        action(
          "inspect",
          'match functionDecl(hasName("processOrder")).bind("function") in node',
        ),
        {},
        [file],
        settings,
        100,
      );
      const selected = first.results.find(
        (node) => node.binding === "function",
      );
      expect(selected).toBeDefined();
      const start = await host.inspect(settings, selected!.nodeId);
      expect(astDisplay(start.node, start.children).kind).toBe("FunctionDecl");
      expect(astDisplay(start.node, start.children).signature).toBe(
        "int processOrder(int)",
      );
      expect(
        astDisplay(start.node, start.children).properties,
      ).not.toContainEqual({ label: "Parameters", value: "None" });
      const body = start.children.find(
        (node) => astDisplay(node).kind === "CompoundStmt",
      );
      expect(body).toBeDefined();
      const returned = await host.inspect(settings, body!.id);
      const statement = returned.children.find(
        (node) => astDisplay(node).kind === "ReturnStmt",
      );
      expect(statement).toBeDefined();
      const call = await host.inspect(settings, statement!.id);
      const expression = call.children.find(
        (node) => astDisplay(node).kind === "CallExpr",
      );
      expect(expression).toBeDefined();
      const callPage = await host.inspect(settings, expression!.id);
      expect(
        astDisplay(callPage.node, callPage.children).properties,
      ).toContainEqual({ label: "Callee", value: "adjust" });
      expect(callPage.parseCount).toBe(1);
      expect(callPage.root.id).toBe(first.input.id);
      const followed = await host.run(
        action("child-calls", 'match callExpr().bind("call") in node'),
        {},
        [file],
        settings,
        100,
        () => {},
        statement!.id,
      );
      expect(followed.input.id).toBe(statement!.id);
      expect(followed.parseCount).toBe(1);
      expect(followed.matches).toBe(1);
      expect(
        followed.results.find((node) => node.binding === "call")?.name,
      ).toBe("adjust");
      expect(
        (await host.inspect(settings, selected!.nodeId)).children.map(
          (node) => node.id,
        ),
      ).toEqual(start.children.map((node) => node.id));
      const located = await host.inspect(settings, {
        result: selected!,
        translationUnit: file,
      });
      expect(located.children.length).toBe(start.children.length);
      expect(located.root.id).toBe(first.input.id);
      await host.reset();
      await expect(host.inspect(settings, expression!.id)).rejects.toThrow(
        /expired/,
      );
      host.dispose();
      await expect(host.inspect(settings, expression!.id)).rejects.toThrow(
        "Action session closed",
      );
    }, 60000);
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
        const helperFile = resolve(directory, "helpers.cpp");
        await writeFile(
          helperFile,
          "namespace demo { struct Order { int quantity; bool valid() const { return quantity > 0; } }; }\n",
        );
        const report = await host.run(
          action(
            "normal-helpers",
            'let normalise(items) = items | map(trim) | to_list\nlet names = normalise([" demo::Order "])\nlet selected = classByName(node, names[0])\nlet fields = classFields(selected)\nif fields.length == 1 then { match fieldDecl().bind("field") in selected } else { 42 }',
          ),
          {},
          [helperFile],
          defaults,
          100,
        );
        expect(report.matches).toBe(1);
        const field = report.results.find((r) => r.binding === "field");
        expect(field?.name).toBe("demo::Order::quantity");
        const again = await host.run(
          action("field-again", 'match fieldDecl().bind("field") in node'),
          {},
          [helperFile],
          defaults,
          100,
          () => {},
          field!.nodeId,
        );
        expect(again.parseCount).toBe(1);
        expect(again.matches).toBe(1);
      },
      60000,
    );
    it("invalidates a closed analysis context and recovers after refresh", async () => {
      const invalidated: string[] = [];
      const host = new ActionService(
        resolve("console/action_service.py"),
        process.env.CTK_PYTHON ?? resolve("../.venv/bin/python"),
        (reason) => invalidated.push(reason),
      );
      services.push(host);
      const find = action(
        "custom",
        'match functionDecl(isDefinition()).bind("function") in node',
      );
      const first = await host.run(find, {}, [file], settings, 100);
      await expect(
        host.run(
          action("close-input", "session close node\n42"),
          {},
          [file],
          settings,
          100,
          () => {},
          first.input.id,
        ),
      ).rejects.toThrow();
      await expect(
        host.run(find, {}, [file], settings, 100, () => {}, first.input.id),
      ).rejects.toThrow(/closed|unavailable|expired/);
      expect(invalidated).toEqual([
        "Analysis context expired or closed; click Refresh, then Run to parse the same C++ file again.",
      ]);
      await host.reset();
      const recovered = await host.run(find, {}, [file], settings, 100);
      expect(recovered.matches).toBe(3);
      expect(recovered.parseCount).toBe(1);
    }, 60000);
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
