import { type ChildProcess, spawn } from "node:child_process";
import {
  mkdir,
  mkdtemp,
  readFile,
  realpath,
  rm,
  writeFile,
} from "node:fs/promises";
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
    it("preserves native parser file, line and UTF-8 column in worker failures", async () => {
      const broken = resolve(directory, "broken source.cpp"),
        line = "int broken() { /* λ😀 */ return missing_name; }";
      await writeFile(broken, `// native diagnostic\n${line}\n`);
      const column =
        Buffer.byteLength(line.slice(0, line.indexOf("missing_name"))) + 1;
      await expect(
        service().inspect(settings, { translationUnit: broken }),
      ).rejects.toThrow(
        `${broken}:2:${column}: error: use of undeclared identifier 'missing_name'`,
      );
      const header = resolve(directory, "broken header.hpp");
      await writeFile(header, "#error broken included header\n");
      await writeFile(broken, '#include "broken header.hpp"\n');
      await expect(
        service().inspect(settings, { translationUnit: broken }),
      ).rejects.toThrow(`${header}:1:2: error: broken included header`);
    }, 30000);
    it("resolves bases and source ranges from unsaved source and header snapshots without touching disk", async () => {
      const source = resolve(directory, "unsaved source.cpp"),
        header = resolve(directory, "unsaved base.hpp"),
        savedHeader = "struct Base { int oldField; };\n",
        savedSource =
          '#include "unsaved base.hpp"\nstruct Derived : Base {};\n';
      await writeFile(header, savedHeader);
      await writeFile(source, savedSource);
      const draftHeader =
          "// λ😀 buffer header\n\nstruct Base { int newField; };\n",
        draftSource =
          '#include "unsaved base.hpp"\n// unsaved position shift\n\nstruct Derived : Base { int changed; };\n',
        draftSettings = {
          ...settings,
          buffers: { [source]: draftSource, [header]: draftHeader },
        },
        host = service(),
        root = await host.inspect(draftSettings, { translationUnit: source }),
        derived = root.children.find((node) => node.name === "Derived");
      expect(derived?.line).toBe(4);
      const page = await host.inspect(draftSettings, derived!.id),
        baseId = page.semantics?.inheritance?.[0]?.nodeId;
      expect(baseId).toBeTruthy();
      const base = await host.inspect(draftSettings, baseId!);
      expect(base.node.file).toBe(await realpath(header));
      expect(base.node.line).toBe(3);
      expect(base.node.excerpt).toContain("newField");
      expect(base.children.some((node) => node.name === "Base::newField")).toBe(
        true,
      );
      expect(base.children.some((node) => node.name === "Base::oldField")).toBe(
        false,
      );
      expect(base.path?.at(-1)?.node.id).toBe(baseId);
      expect(await readFile(source, "utf8")).toBe(savedSource);
      expect(await readFile(header, "utf8")).toBe(savedHeader);
      expect(base.parseCount).toBe(1);
      const declaration = page.semantics?.inheritance?.[0]?.declaration;
      expect(declaration?.symbol).toBeTruthy();
      const rebound = await service().inspect(draftSettings, {
        translationUnit: source,
        reference: declaration!,
      });
      expect(rebound.node.name).toBe("Base");
      expect(rebound.node.line).toBe(3);
      expect(
        rebound.children.some((node) => node.name === "Base::newField"),
      ).toBe(true);
    }, 30000);
    it("shows access-grouped members, native transitive inheritance and typed parameters", async () => {
      const fixture = resolve(directory, "semantic-inspector.cpp");
      await writeFile(
        fixture,
        await readFile("examples/semantic-inspector.cpp", "utf8"),
      );
      const host = service(),
        root = await host.inspect(settings, { translationUnit: fixture });
      const find = (name: string) => {
        const node = root.children.find((child) => child.name === name);
        expect(node, name).toBeDefined();
        return node!;
      };
      const widget = await host.inspect(settings, find("Widget").id);
      const display = astDisplay(widget.node, widget.children);
      expect(widget.semantics?.inheritance).toMatchObject([
        {
          name: "MidAlias",
          depth: 0,
          access: "ACCESS_SPECIFIER_PUBLIC",
          virtual: false,
        },
        {
          name: "Root",
          depth: 1,
          access: "ACCESS_SPECIFIER_PUBLIC",
          virtual: true,
        },
        {
          name: "Hidden",
          depth: 0,
          access: "ACCESS_SPECIFIER_PROTECTED",
          virtual: false,
        },
      ]);
      const middleId = widget.semantics?.inheritance?.[0]?.nodeId;
      expect(middleId).toBe(find("Middle").id);
      const middle = await host.inspect(settings, middleId!);
      expect(middle.node.id).toBe(middleId);
      expect(middle.path?.[0]?.node.id).toBe(root.node.id);
      expect(middle.path?.at(-1)?.node.id).toBe(middleId);
      expect(astDisplay(middle.node).name).toBe("Middle");
      const rootBaseId = middle.semantics?.inheritance?.[0]?.nodeId;
      expect(rootBaseId).toBe(find("Root").id);
      const baseSpecifier = middle.children.find(
        (child) => astDisplay(child).kind === "CXXBaseSpecifier",
      );
      expect(baseSpecifier?.name).toBe("Root");
      const baseEdge = await host.inspect(settings, baseSpecifier!.id);
      expect(baseEdge.semantics?.referencedDeclaration).toMatchObject({
        name: "Root",
        nodeId: rootBaseId,
      });
      // Clang 21 retains an ElaboratedTypeLoc around the record location;
      // newer Clang versions expose RecordTypeLoc directly.
      let typeLocation = baseEdge.children.find((child) =>
        astDisplay(child).kind.endsWith("TypeLoc"),
      );
      expect(typeLocation?.name).toBe("Root");
      let typePage = await host.inspect(settings, typeLocation!.id);
      for (
        let depth = 0;
        astDisplay(typePage.node).kind !== "RecordTypeLoc" && depth < 8;
        depth++
      ) {
        expect(typePage.semantics?.referencedDeclaration).toEqual(
          baseEdge.semantics?.referencedDeclaration,
        );
        typeLocation = typePage.children.find((child) =>
          astDisplay(child).kind.endsWith("TypeLoc"),
        );
        expect(typeLocation?.name).toBe("Root");
        typePage = await host.inspect(settings, typeLocation!.id);
      }
      expect(astDisplay(typePage.node).kind).toBe("RecordTypeLoc");
      expect(typePage.semantics?.referencedDeclaration).toEqual(
        baseEdge.semantics?.referencedDeclaration,
      );
      expect(typePage.parseCount).toBe(1);
      const rootBase = await host.inspect(settings, rootBaseId!);
      const baseAction = await host.run(
        action("base-fields", 'match fieldDecl().bind("field") in node'),
        {},
        [fixture],
        settings,
        100,
        () => {},
        rootBase.node.id,
      );
      expect(baseAction.matches).toBe(1);
      expect(
        baseAction.results
          .filter((node) => node.binding === "field")
          .map((node) => node.name),
      ).toEqual(["Root::id"]);
      expect(baseAction.parseCount).toBe(1);
      expect(display.sections.map((section) => section.title)).toEqual([
        "Public members",
        "Protected members",
        "Private members",
      ]);
      const members = (access: string) =>
        display.sections.find(
          (section) => section.title === `${access} members`,
        )!.rows;
      expect(members("Private").map((row) => row.values[0])).toEqual([
        "Widget::secret",
        "Widget::reset",
        "Widget::flags",
      ]);
      expect(
        members("Public").find((row) => row.values[0] === "Widget::ready")
          ?.values,
      ).toEqual(["Widget::ready", "Field", "bool", "static"]);
      expect(members("Protected").map((row) => row.values[0])).toEqual([
        "Widget::ratio",
        "Widget::update",
      ]);
      const method = widget.children.find(
        (child) => child.name === "Widget::check",
      )!;
      const check = await host.inspect(settings, method.id);
      expect(check.semantics?.parameters).toEqual([
        { name: "limit", type: "int" },
        { name: "label", type: "const char *" },
      ]);
      expect(astDisplay(check.node, check.children).properties).toContainEqual({
        label: "Const",
        value: "Yes",
      });
      const fn = await host.inspect(settings, find("calculate").id);
      expect(fn.semantics?.parameters).toEqual([
        { name: "count", type: "int" },
        { name: "widget", type: "const Widget &" },
        { name: "", type: "double" },
      ]);
      const body = fn.children.find(
        (child) => astDisplay(child).kind === "CompoundStmt",
      )!;
      const statement = await host.inspect(settings, body.id);
      expect(astDisplay(statement.node, statement.children).sections).toEqual(
        [],
      );
      expect(statement.semantics).toBeUndefined();
      const enumPage = await host.inspect(settings, find("State").id);
      expect(
        astDisplay(enumPage.node, enumPage.children).sections[0]?.rows.map(
          (row) => row.values,
        ),
      ).toEqual([
        ["State::Idle", "1"],
        ["State::Running", "4"],
      ]);
      const alias = await host.inspect(settings, find("WidgetPointer").id);
      expect(astDisplay(alias.node, alias.children).properties).toContainEqual({
        label: "Underlying type",
        value: "const Widget *",
      });
      expect(
        (await host.inspect(settings, find("Widget").id)).semantics,
      ).toEqual(widget.semantics);
      expect(widget.parseCount).toBe(1);
      expect(alias.parseCount).toBe(1);
    }, 60000);
    it("reveals a header base definition through its real TU ancestry and rejects expired references", async () => {
      const header = resolve(directory, "base[decl].hpp"),
        derived = resolve(directory, "derived.cpp");
      await writeFile(
        header,
        "namespace vendor { struct Base; struct Base { int own; }; }\n",
      );
      await writeFile(
        derived,
        '#include "base[decl].hpp"\nnamespace other { struct Base { int wrong; }; }\nclass Derived : public vendor::Base { int local; };\n',
      );
      const host = service(),
        root = await host.inspect(settings, { translationUnit: derived });
      const child = root.children.find((node) => node.name === "Derived")!;
      const page = await host.inspect(settings, child.id);
      const baseId = page.semantics?.inheritance?.[0]?.nodeId;
      expect(baseId).toBeTruthy();
      const base = await host.inspect(settings, baseId!);
      expect(astDisplay(base.node).name).toBe("vendor::Base");
      expect(base.node.file).toBe(
        await import("node:fs/promises").then((fs) => fs.realpath(header)),
      );
      expect(
        base.children.some((node) => node.name === "vendor::Base::own"),
      ).toBe(true);
      expect(base.path?.map((part) => astDisplay(part.node).kind)).toEqual([
        "TranslationUnitDecl",
        "NamespaceDecl",
        "CXXRecordDecl",
      ]);
      expect(base.path?.at(-1)?.node.id).toBe(baseId);
      const report = await host.run(
        action("header-base-fields", 'match fieldDecl().bind("field") in node'),
        {},
        [derived],
        settings,
        100,
        () => {},
        base.node.id,
      );
      expect(report.matches).toBe(1);
      expect(
        report.results
          .filter((node) => node.binding === "field")
          .map((node) => node.name),
      ).toEqual(["vendor::Base::own"]);
      expect(report.parseCount).toBe(1);
      await host.reset();
      await expect(host.inspect(settings, baseId!)).rejects.toThrow(/expired/);
    }, 60000);
    it("loads large file and namespace ASTs with included header declarations", async () => {
      const host = service();
      const source = resolve(directory, "large.cpp");
      const header = resolve(directory, "large.h");
      const largeSettings = settings;
      const declarations = (prefix: string, count: number) =>
        Array.from({ length: count }, (_, i) => `int ${prefix}${i};`).join(
          "\n",
        );
      await writeFile(header, declarations("header_", 2000));
      const text = `#include "large.h"\n${declarations("file_", 10001)}\nnamespace wide {\n${declarations("member_", 1001)}\n}\n`;
      await writeFile(source, text);
      const root = await host.inspect(largeSettings, {
        translationUnit: source,
      });
      expect(root.children).toHaveLength(10002);
      expect(root.children.some((node) => node.name === "file_10000")).toBe(
        true,
      );
      expect(
        root.children.some((node) => node.name.startsWith("header_")),
      ).toBe(false);
      const namespace = root.children.find((node) => node.name === "wide");
      const page = await host.inspect(largeSettings, namespace!.id);
      expect(page.children).toHaveLength(1001);
      const last = page.children.find(
        (node) => node.name === "wide::member_1000",
      );
      expect(last).toBeDefined();
      const selected = await host.inspect(largeSettings, last!.id);
      expect(selected.node.id).toBe(last!.id);
      expect(selected.parseCount).toBe(1);
      expect(
        (await host.inspect(largeSettings, root.node.id)).children,
      ).toEqual(root.children);
      const headerText = await readFile(header, "utf8");
      const offset = headerText.indexOf("header_1999");
      const headerNode = await host.selectSource(largeSettings, root.node.id, {
        file: header,
        start: offset,
        end: offset,
      });
      expect(headerNode?.node.name).toBe("header_1999");
      expect(headerNode?.path?.[0]?.children).toHaveLength(12002);
      expect(headerNode?.parseCount).toBe(1);
      await host.reset();
    }, 240000);
    it("opens a file AST without running an action and fetches unvisited children lazily", async () => {
      const host = service();
      const root = await host.inspect(settings, { translationUnit: file });
      expect(astDisplay(root.node).kind).toBe("TranslationUnitDecl");
      expect(root.parseCount).toBe(1);
      const rootAction = await host.run(
        action(
          "file-root-functions",
          'match functionDecl(isDefinition()).bind("function") in node',
        ),
        {},
        [file],
        settings,
        100,
        () => {},
        root.node.id,
      );
      expect(rootAction.matches).toBe(3);
      expect(rootAction.parseCount).toBe(1);
      const functionNode = root.children.find(
        (node) => node.name === "processOrder",
      );
      expect(functionNode).toBeDefined();
      const functionPage = await host.inspect(settings, functionNode!.id);
      const body = functionPage.children.find(
        (node) => astDisplay(node).kind === "CompoundStmt",
      );
      expect(body).toBeDefined();
      const bodyPage = await host.inspect(settings, body!.id);
      expect(
        bodyPage.children.some(
          (node) => astDisplay(node).kind === "ReturnStmt",
        ),
      ).toBe(true);
      expect(bodyPage.parseCount).toBe(1);
      expect((await host.inspect(settings, body!.id)).children).toEqual(
        bodyPage.children,
      );
      const followed = await host.run(
        action("file-child-calls", 'match callExpr().bind("call") in node'),
        {},
        [file],
        settings,
        100,
        () => {},
        body!.id,
      );
      expect(followed.matches).toBe(1);
      expect(followed.parseCount).toBe(1);
      await host.reset();
      await expect(host.inspect(settings, body!.id)).rejects.toThrow(/expired/);
    }, 60000);
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
      expect(call!.path?.map((page) => astDisplay(page.node).kind)).toEqual([
        "TranslationUnitDecl",
        "FunctionDecl",
        "CompoundStmt",
        "ReturnStmt",
        "CallExpr",
      ]);
      for (const [index, page] of call!.path!.entries()) {
        const next = call!.path![index + 1];
        if (next)
          expect(page.children.some((child) => child.id === next.node.id)).toBe(
            true,
          );
      }
      const fileRoot = await host.inspect(settings, { translationUnit: file });
      expect(call!.path![0]!.node.id).toBe(fileRoot.node.id);
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
