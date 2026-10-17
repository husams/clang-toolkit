import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { afterAll, beforeAll, expect, it } from "vitest";
import { type RunRequest, scriptAction } from "../src/model.js";
import { startConsoleWorker } from "../src/worker-client.js";

const python = process.env.CTK_PYTHON ?? resolve("../.venv/bin/python");
const worker = resolve("console/run_service.py");
let directory: string;
beforeAll(async () => {
  directory = await mkdtemp(resolve(tmpdir(), "ctk-console-"));
  await mkdir(resolve(directory, "lib"));
  await writeFile(
    resolve(directory, "lib/preload.ctk"),
    "let triple(value) = value * 3",
  );
  await writeFile(
    resolve(directory, "relative.ctk"),
    "let increment(value) = value + 1",
  );
});
afterAll(async () => {
  await rm(directory, { recursive: true, force: true });
});
function request(source: string): RunRequest {
  return {
    action: scriptAction(resolve(directory, "unsaved.ctk"), source),
    files: [],
    values: {},
    kinds: [],
    directory,
    endpoint: `unix://${directory}/unavailable.sock`,
    libraryDirectory: resolve(directory, "lib"),
    compileArguments: [],
    timeoutMs: 30000,
    maxResults: 100,
  };
}
const execute = (source: string, values = {}) =>
  startConsoleWorker(worker, python, { ...request(source), values }, () => {})
    .completion;

it("runs defaults, callbacks, closures, preloaded helpers and relative imports without a C++ file or server", async () => {
  const report = await execute(
    'import "relative.ctk"\nlet scale(value, factor = 2) = { value * factor }\nlet apply(operation, value) = operation(value)\nprint scale(triple(7))\nprint apply((x) = increment(x), 8)',
  );
  expect(report.errors).toEqual([]);
  expect(report.output).toEqual(["42\n9"]);
  expect(report.results).toEqual([]);
}, 30000);
it("passes parameter contents as literal strings rather than console interpolation or code", async () => {
  const value = 'x"; print 999; {1 + 2}\n${MISSING}\\tail';
  const report = await execute("print ${NAME}", { NAME: value });
  expect(report.errors).toEqual([]);
  expect(report.output).toEqual([value]);
}, 30000);
it("stops on errors, retains earlier output and identifies the script", async () => {
  const report = await execute(
    'print "before"\nmissingFunction()\nprint "after"',
  );
  expect(report.errors[0]).toContain("unsaved.ctk");
  expect(report.output.join("\n")).toContain("before");
  expect(report.output.join("\n")).toContain("missingFunction");
  expect(report.output.join("\n")).not.toContain("after");
}, 30000);
it("uses console lexical captures, recovery and exit handlers", async () => {
  const report = await execute(
    "let makeAdder(base) = (value, extra = base) = value + extra\nlet addTen = makeAdder(10)\nprint addTen(5)\nlet events = [0]\nlet divide() = { on error 9; on exit { events[0] += 1 }; 1 / 0 }\nprint divide()\nprint events[0]",
  );
  expect(report.errors).toEqual([]);
  expect(report.output).toEqual(["15\n9\n1"]);
}, 30000);
it("cancels an actively executing console loop", async () => {
  let running!: () => void;
  const started = new Promise<void>((done) => {
    running = done;
  });
  const run = startConsoleWorker(
    worker,
    python,
    request("while true { let x = 1 }"),
    () => running(),
  );
  const rejection = expect(run.completion).rejects.toThrow("cancelled");
  await started;
  await new Promise((done) => setTimeout(done, 250));
  run.cancel();
  await rejection;
  expect(run.process.signalCode).not.toBe("SIGKILL");
}, 20000);
