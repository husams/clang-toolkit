import { type ChildProcessWithoutNullStreams, spawn } from "node:child_process";
import { EventEmitter } from "node:events";
import { PassThrough } from "node:stream";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ConsoleService } from "../src/console-service.js";

vi.mock("node:child_process", () => ({ spawn: vi.fn() }));

class Worker extends EventEmitter {
  stdin = new PassThrough();
  stdout = new PassThrough();
  stderr = new PassThrough();
  sent: { id: number; source: string }[] = [];
  kill = vi.fn(() => true);
  constructor() {
    super();
    this.stdin.on("data", (data: Buffer) => {
      this.sent.push(JSON.parse(data.toString()));
    });
  }
  reply(value: unknown): void {
    this.stdout.write(`${JSON.stringify(value)}\n`);
  }
}
const workers: Worker[] = [];
let service: ConsoleService;
let logs: string[];
beforeEach(() => {
  vi.useFakeTimers();
  workers.length = 0;
  logs = [];
  vi.mocked(spawn).mockImplementation(() => {
    const worker = new Worker();
    workers.push(worker);
    return worker as unknown as ChildProcessWithoutNullStreams;
  });
  service = new ConsoleService("editor_service.py", "python", (text) =>
    logs.push(text),
  );
});
afterEach(() => {
  service.dispose();
  vi.useRealTimers();
  vi.clearAllMocks();
});
const request = (source = "match functionD") =>
  service.request(source, source.length, "/workspace", "/library");
const ready = async (worker = workers.at(-1)!) => {
  worker.reply({ ready: true });
  await vi.advanceTimersByTimeAsync(0);
  return worker;
};
const respond = (worker: Worker, index = 0) => {
  const id = worker.sent[index]!.id;
  worker.reply({ id, items: [], functions: {} });
  return id;
};

it("gives a cold worker its own startup budget before timing completion", async () => {
  const pending = request();
  const worker = workers[0]!;
  expect(worker.sent).toEqual([]);
  await vi.advanceTimersByTimeAsync(29000);
  await ready(worker);
  expect(worker.sent).toHaveLength(1);
  await vi.advanceTimersByTimeAsync(29000);
  const id = respond(worker);
  await expect(pending).resolves.toMatchObject({ id });
  expect(worker.kill).not.toHaveBeenCalled();
});

it("shares identical in-flight requests without caching completed results", async () => {
  const first = request();
  expect(request()).toBe(first);
  const other = request("match recordD");
  const worker = await ready();
  expect(workers).toHaveLength(1);
  expect(worker.sent).toHaveLength(2);
  respond(worker, 1);
  respond(worker);
  await Promise.all([first, other]);
  const again = request();
  await vi.advanceTimersByTimeAsync(0);
  expect(worker.sent).toHaveLength(3);
  respond(worker, 2);
  await again;
});

it("kills a stalled worker, releases all queued callers and restarts on retry", async () => {
  const first = request();
  const old = await ready();
  const other = request("match recordD");
  const failures = Promise.all([
    expect(first).rejects.toThrow("worker was stopped"),
    expect(other).rejects.toThrow("worker was stopped"),
  ]);
  await vi.advanceTimersByTimeAsync(30000);
  await failures;
  expect(old.kill).toHaveBeenCalledExactlyOnceWith("SIGKILL");
  expect(logs.some((text) => text.includes("timed out"))).toBe(true);
  const retry = request();
  expect(workers).toHaveLength(2);
  old.emit("exit", null);
  old.reply({ id: old.sent[0]!.id, error: "late old response" });
  const fresh = await ready();
  respond(fresh);
  await expect(retry).resolves.toMatchObject({ items: [] });
  expect(fresh.kill).not.toHaveBeenCalled();
});

it("stops startup failures and allows another attempt", async () => {
  const pending = request();
  const failure = expect(pending).rejects.toThrow("startup timed out");
  await vi.advanceTimersByTimeAsync(30000);
  await failure;
  expect(workers[0]!.kill).toHaveBeenCalledWith("SIGKILL");
  const retry = request();
  const fresh = await ready();
  respond(fresh);
  await retry;
});

it("rejects malformed replies and replaces that worker on retry", async () => {
  const pending = request();
  const failure = expect(pending).rejects.toThrow();
  const old = await ready();
  old.reply({ id: "invalid" });
  await failure;
  expect(old.kill).toHaveBeenCalledWith("SIGKILL");
  const retry = request();
  const fresh = await ready();
  respond(fresh);
  await retry;
});

it("recovers from an interpreter launch error", async () => {
  const pending = request();
  const failure = expect(pending).rejects.toThrow("ENOENT");
  workers[0]!.emit("error", new Error("ENOENT"));
  await failure;
  const retry = request();
  const fresh = await ready();
  respond(fresh);
  await retry;
});

it("keeps a healthy worker after an individual completion error", async () => {
  const pending = request();
  const failure = expect(pending).rejects.toThrow("invalid draft");
  const worker = await ready();
  worker.reply({ id: worker.sent[0]!.id, error: "invalid draft" });
  await failure;
  const retry = request("match recordD");
  await vi.advanceTimersByTimeAsync(0);
  respond(worker, 1);
  await retry;
  expect(workers).toHaveLength(1);
  expect(worker.kill).not.toHaveBeenCalled();
});

it("closes a starting worker and never restarts a disposed service", async () => {
  const pending = request();
  const failure = expect(pending).rejects.toThrow("closed");
  service.dispose();
  await failure;
  await expect(request()).rejects.toThrow("closed");
  expect(workers).toHaveLength(1);
  expect(workers[0]!.kill).toHaveBeenCalledWith("SIGKILL");
});
