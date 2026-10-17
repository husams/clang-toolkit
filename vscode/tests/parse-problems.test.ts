import { mkdtemp, realpath, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Diagnostic, DiagnosticSeverity, Position, Range, Uri } from "vscode";
import { ParseProblems } from "../src/parse-problems.js";

const published = vi.hoisted(() => new Map<string, Diagnostic[]>());
const external = vi.hoisted(() => new Map<string, Diagnostic[]>());
const events = vi.hoisted(() => ({
  writes: 0,
  listeners: new Set<(event: { uris: Uri[] }) => void>(),
}));
vi.mock("vscode", () => {
  const uri = (file: string) =>
    ({ scheme: "file", fsPath: file, toString: () => file }) as Uri;
  const changed = (files: string[]) => {
    for (const listener of events.listeners) listener({ uris: files.map(uri) });
  };
  return {
    languages: {
      onDidChangeDiagnostics: (listener: (event: { uris: Uri[] }) => void) => {
        events.listeners.add(listener);
        return { dispose: () => events.listeners.delete(listener) };
      },
      getDiagnostics: (resource?: Uri) =>
        resource
          ? [
              ...(published.get(resource.fsPath) ?? []),
              ...(external.get(resource.fsPath) ?? []),
            ]
          : [...new Set([...published.keys(), ...external.keys()])].map(
              (file) => [
                uri(file),
                [...(published.get(file) ?? []), ...(external.get(file) ?? [])],
              ],
            ),
      createDiagnosticCollection: () => ({
        clear: () => {
          const files = [...published.keys()];
          published.clear();
          changed(files);
        },
        set: (
          entries: [
            { fsPath: string },
            typeof published extends Map<string, infer Items> ? Items : never,
          ][],
        ) => {
          for (const [uri, items] of entries) published.set(uri.fsPath, items);
          events.writes++;
          changed(entries.map(([uri]) => uri.fsPath));
        },
        dispose: () => published.clear(),
      }),
    },
    Uri: { file: uri },
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
    DiagnosticSeverity: { Error: 0, Warning: 1 },
  };
});
let directory: string, problems: ParseProblems;
beforeEach(async () => {
  published.clear();
  external.clear();
  events.listeners.clear();
  events.writes = 0;
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
function otherError(
  message = "Bad header",
  character = 1,
  severity = DiagnosticSeverity.Error,
) {
  const diagnostic = new Diagnostic(
    new Range(new Position(0, character), new Position(0, character + 4)),
    message,
    severity,
  );
  diagnostic.source = "clang";
  return diagnostic;
}
function externalChanged(file: string, diagnostics: Diagnostic[]) {
  if (diagnostics.length) external.set(file, diagnostics);
  else external.delete(file);
  for (const listener of events.listeners) listener({ uris: [Uri.file(file)] });
}
it("keeps an already published clang error instead of adding a duplicate CTK error", async () => {
  const file = join(directory, "existing.cpp");
  await writeFile(file, "#error bad header\n");
  problems.dispose();
  external.set(file, [otherError("Bad   ‘header’")]);
  problems = new ParseProblems();
  await problems.report(
    file,
    `${file}:1:2: error: bad 'header'`,
    directory,
    () => true,
  );
  await vi.waitFor(() =>
    expect([...published.values()].flat()).toHaveLength(0),
  );
  expect(external.get(file)).toHaveLength(1);
});
it("withdraws CTK when clang arrives later and restores it when clang removes the error", async () => {
  const file = join(directory, "late.cpp");
  await writeFile(file, "#error bad header\n");
  await problems.report(
    file,
    `${file}:1:2: error: bad header`,
    directory,
    () => true,
  );
  expect([...published.values()].flat()).toHaveLength(1);
  externalChanged(file, [otherError()]);
  await vi.waitFor(() =>
    expect([...published.values()].flat()).toHaveLength(0),
  );
  const writes = events.writes;
  for (let index = 0; index < 5; index++) externalChanged(file, [otherError()]);
  expect(
    events.writes,
    "unchanged diagnostics must not start a notification loop",
  ).toBe(writes);
  externalChanged(file, []);
  expect([...published.values()].flat()).toHaveLength(1);
});
it.each([
  ["different message", "Different failure", 1, DiagnosticSeverity.Error],
  ["different location", "Bad header", 2, DiagnosticSeverity.Error],
  ["different severity", "Bad header", 1, DiagnosticSeverity.Warning],
])(
  "keeps a CTK-only error alongside clang's %s",
  async (_label, message, character, severity) => {
    const file = join(directory, "distinct.cpp");
    await writeFile(file, "#error bad header\n");
    externalChanged(file, [otherError(message, character, severity)]);
    await problems.report(
      file,
      `${file}:1:2: error: bad header`,
      directory,
      () => true,
    );
    expect([...published.values()].flat()).toHaveLength(1);
    expect(external.get(file)).toHaveLength(1);
  },
);
it("recognizes a matching clang error published through a different filesystem alias", async () => {
  const file = join(directory, "physical.cpp"),
    alias = join(directory, "alias.cpp");
  await writeFile(file, "#error bad header\n");
  await symlink(file, alias);
  await problems.report(
    file,
    `${file}:1:2: error: bad header`,
    directory,
    () => true,
  );
  externalChanged(alias, [otherError()]);
  await vi.waitFor(() =>
    expect([...published.values()].flat()).toHaveLength(0),
  );
  problems.dispose();
  expect(events.listeners.size).toBe(0);
  externalChanged(alias, []);
  expect([...published.values()].flat()).toHaveLength(0);
});
it("does not merge errors for C++ identifiers that differ only in case", async () => {
  const file = join(directory, "identifier-case.cpp");
  await writeFile(file, "#error example\n");
  externalChanged(file, [otherError("Use of undeclared identifier 'widget'")]);
  await problems.report(
    file,
    `${file}:1:2: error: use of undeclared identifier 'Widget'`,
    directory,
    () => true,
  );
  expect([...published.values()].flat()).toHaveLength(1);
});
