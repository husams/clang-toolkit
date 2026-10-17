import { mkdtemp, realpath, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Uri } from "vscode";
import { ParseProblems } from "../src/parse-problems.js";

const published = vi.hoisted(
  () =>
    new Map<
      string,
      {
        message: string;
        source: string;
        range: { start: { line: number; character: number } };
      }[]
    >(),
);
vi.mock("vscode", () => ({
  languages: {
    createDiagnosticCollection: () => ({
      clear: () => published.clear(),
      set: (
        entries: [
          { fsPath: string },
          typeof published extends Map<string, infer Items> ? Items : never,
        ][],
      ) => {
        for (const [uri, items] of entries) published.set(uri.fsPath, items);
      },
      dispose: () => published.clear(),
    }),
  },
  Uri: { file: (file: string) => ({ fsPath: file, toString: () => file }) },
  Position: class {
    constructor(
      public line: number,
      public character: number,
    ) {}
  },
  Range: class {
    constructor(
      public start: unknown,
      public end: unknown,
    ) {}
  },
  Diagnostic: class {
    constructor(
      public range: unknown,
      public message: string,
      public severity: number,
    ) {}
  },
  DiagnosticSeverity: { Error: 0 },
}));
let directory: string, problems: ParseProblems;
beforeEach(async () => {
  published.clear();
  directory = await mkdtemp(join(tmpdir(), "ctk-problems-unit-"));
  problems = new ParseProblems();
});
afterEach(async () => {
  problems.dispose();
  await rm(directory, { recursive: true, force: true });
});
it("converts native UTF-8 columns into exact VS Code UTF-16 positions", async () => {
  const file = join(directory, "unicode.cpp"),
    line = "int f() { /* λ😀 */ return missing; }";
  await writeFile(file, `// header\r\n${line}\r\n`);
  const character = line.indexOf("missing"),
    byteColumn = Buffer.byteLength(line.slice(0, character)) + 1;
  await problems.report(
    file,
    `${file}:2:${byteColumn}: error: undeclared 'missing'`,
    directory,
    () => true,
  );
  const items = [...published.values()].flat();
  expect(items).toHaveLength(1);
  expect(items[0]).toMatchObject({
    source: "CTK",
    message: "undeclared 'missing'",
    range: { start: { line: 1, character } },
  });
});
it("deduplicates shared-header errors without clearing another translation unit's errors", async () => {
  const header = join(directory, "shared.hpp");
  await writeFile(header, "#error bad header\n");
  const error = `${header}:1:2: error: bad header`;
  await problems.report("first.cpp", error, directory, () => true);
  await problems.report("second.cpp", error, directory, () => true);
  expect([...published.values()].flat()).toHaveLength(1);
  problems.clear("first.cpp");
  expect([...published.values()].flat()).toHaveLength(1);
  problems.clear("second.cpp");
  expect(published.size).toBe(0);
});
it("keeps the open source document URI when Clang uses a canonical path alias", async () => {
  const file = join(directory, "alias.cpp");
  await writeFile(file, "#error alias\n");
  const canonical = await realpath(file);
  await problems.report(
    canonical,
    `${canonical}:1:2: error: alias`,
    directory,
    () => true,
    Uri.file(file),
  );
  expect(published.has(file)).toBe(true);
});
it("discards diagnostics when an attempt is superseded, the file closes, or the extension disposes", async () => {
  const file = join(directory, "changed.cpp");
  await writeFile(file, "#error old\n");
  const error = `${file}:1:2: error: old`;
  let current = true;
  const first = problems.report(file, error, directory, () => current);
  current = false;
  await first;
  expect(published.size).toBe(0);
  const second = problems.report(file, error, directory, () => true);
  problems.clear(file);
  await second;
  expect(published.size).toBe(0);
  const third = problems.report(file, error, directory, () => true);
  problems.dispose();
  await third;
  expect(published.size).toBe(0);
});
it("does not create fake source locations for an offline server or invalid compiler coordinates", async () => {
  const file = join(directory, "bad.cpp");
  await writeFile(file, "int value;\n");
  await problems.report(
    file,
    `Connection refused\n${file}:20:1: error: stale range`,
    directory,
    () => true,
  );
  expect(published.size).toBe(0);
});
