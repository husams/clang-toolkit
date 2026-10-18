import { type ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import { PassThrough } from "node:stream";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ActionService } from "../src/action-service.js";

vi.mock("node:child_process", () => ({ spawn: vi.fn() }));
class Worker extends EventEmitter {
  stdin = new PassThrough();
  stdout = new PassThrough();
  stderr = new PassThrough();
  sent: { id: number; type: string }[] = [];
  kill = vi.fn(() => true);
  constructor() {
    super();
    this.stdin.on("data", (data: Buffer) =>
      this.sent.push(JSON.parse(data.toString())),
    );
  }
  reply(value: Record<string, unknown>, index = this.sent.length - 1): void {
    this.stdout.write(
      `${JSON.stringify({ id: this.sent[index]!.id, ...value })}\n`,
    );
  }
}
const inspection = {
  node: {
    id: "node",
    name: "Order",
    kind: "Class",
    file: "/demo.cpp",
    line: 1,
    column: 1,
    excerpt: "",
    raw: {},
    locationValid: true,
  },
  children: [],
  parseCount: 1,
  root: { id: "root", file: "/demo.cpp", label: "File root" },
};
const settings = {
  directory: "/workspace",
  compileArguments: [],
  timeoutMs: 30000,
};
let worker: Worker;
let host: ActionService;
beforeEach(() => {
  vi.useFakeTimers();
  worker = new Worker();
  vi.mocked(spawn).mockReturnValue(
    worker as unknown as ChildProcessWithoutNullStreams,
  );
  host = new ActionService("actions.py", "python");
});
afterEach(() => {
  host.dispose();
  vi.useRealTimers();
  vi.clearAllMocks();
});
async function open() {
  const pending = host.inspect(settings, "node");
  worker.reply({ inspection });
  await pending;
}
it("allows initial file inspection to finish its parse, root lookup and child RPCs", async () => {
  const pending = host
    .inspect(settings, { translationUnit: "/large.cpp" })
    .then(
      (value) => ({ value }),
      (error: unknown) => ({ error }),
    );
  await vi.advanceTimersByTimeAsync(45000);
  expect(worker.kill).not.toHaveBeenCalled();
  worker.reply({ inspection });
  expect(await pending).toEqual({ value: inspection });
});
it("renews retained sessions each minute and stops when disposed", async () => {
  await open();
  await vi.advanceTimersByTimeAsync(60000);
  expect(worker.sent.map((request) => request.type)).toEqual([
    "inspect",
    "keepAlive",
  ]);
  worker.reply({ keptAlive: 4 });
  await vi.advanceTimersByTimeAsync(60000);
  expect(worker.sent.at(-1)?.type).toBe("keepAlive");
  worker.reply({ keptAlive: 4 });
  await vi.advanceTimersByTimeAsync(0);
  host.dispose();
  const count = worker.sent.length;
  await vi.advanceTimersByTimeAsync(600000);
  expect(worker.sent).toHaveLength(count);
});
it("lets foreground inspection wait for renewal instead of rejecting it as busy", async () => {
  await open();
  const renewal = host.keepAlive();
  const pending = host.inspect(settings, "node");
  expect(worker.sent).toHaveLength(2);
  worker.reply({ keptAlive: 4 });
  await vi.advanceTimersByTimeAsync(0);
  expect(worker.sent.at(-1)?.type).toBe("inspect");
  worker.reply({ inspection });
  expect(await renewal).toBe(4);
  expect((await pending).node.id).toBe("node");
});
it("skips renewal during foreground work and stops after reset", async () => {
  await open();
  const pending = host.inspect({ ...settings, timeoutMs: 120000 }, "node");
  await vi.advanceTimersByTimeAsync(60000);
  expect(worker.sent.map((request) => request.type)).toEqual([
    "inspect",
    "inspect",
  ]);
  worker.reply({ inspection });
  await pending;
  const reset = host.reset();
  worker.reply({ reset: true });
  await reset;
  await vi.advanceTimersByTimeAsync(120000);
  expect(worker.sent.map((request) => request.type)).toEqual([
    "inspect",
    "inspect",
    "reset",
  ]);
});
it("reports a lost session and stops background renewal", async () => {
  const invalidated = vi.fn();
  host.setCallbacks(invalidated, () => {});
  await open();
  await vi.advanceTimersByTimeAsync(60000);
  worker.reply({ error: "Analysis session expired" });
  await vi.advanceTimersByTimeAsync(0);
  expect(invalidated).toHaveBeenCalled();
  const count = worker.sent.length;
  await vi.advanceTimersByTimeAsync(180000);
  expect(worker.sent).toHaveLength(count);
});
it("does not report a stale session after closing during renewal", async () => {
  const invalidated = vi.fn();
  host.setCallbacks(invalidated, () => {});
  await open();
  await vi.advanceTimersByTimeAsync(60000);
  host.dispose();
  const count = worker.sent.length;
  await vi.advanceTimersByTimeAsync(180000);
  expect(invalidated).not.toHaveBeenCalled();
  expect(worker.sent).toHaveLength(count);
});
it("keeps the worker termination deadline when both owners close the shared session", async () => {
  await open();
  host.dispose();
  host.dispose();
  await vi.advanceTimersByTimeAsync(3000);
  expect(worker.kill).toHaveBeenCalledOnce();
});
it("keeps the file owner's callbacks when an action observes its shared session", async () => {
  const owner = vi.fn(),
    action = vi.fn(),
    output = vi.fn();
  host.setCallbacks(owner, () => {});
  const release = host.subscribe(action, output);
  await open();
  const first = host.inspect(settings, "node");
  worker.reply({ error: "cursor unavailable", output: ["action output"] });
  await expect(first).rejects.toThrow("cursor unavailable");
  expect(owner).toHaveBeenCalledTimes(1);
  expect(action).toHaveBeenCalledTimes(1);
  expect(output).toHaveBeenCalledWith("action output");
  release();
  const second = host.inspect(settings, "node");
  worker.reply({ error: "cursor unavailable" });
  await expect(second).rejects.toThrow("cursor unavailable");
  expect(owner).toHaveBeenCalledTimes(2);
  expect(action).toHaveBeenCalledTimes(1);
});
