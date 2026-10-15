import { type ChildProcess, spawn } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { Client } from "@clang-toolkit/sdk";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { runAnalysis } from "../src/engine.js";
import { predefined, type RunRequest, scriptAction } from "../src/model.js";
import { startWorker } from "../src/worker-client.js";

describe.skipIf(process.env.CTK_INTEGRATION !== "1")("native prototype", () => {
  let directory: string,
    endpoint: string,
    server: ChildProcess,
    fixture: string;
  beforeAll(async () => {
    directory = await mkdtemp(resolve(tmpdir(), "ctk-vscode-"));
    endpoint = `unix://${directory}/server.sock`;
    fixture = resolve(directory, "demo.cpp");
    await writeFile(
      fixture,
      "namespace demo { struct Order { int quantity; bool valid() const {return quantity>0;} }; Order createOrder(int n){return Order{n};} Order currentOrder{3}; }",
    );
    const yaml = resolve(directory, "server.yaml");
    await writeFile(
      yaml,
      `network:\n  transport: unix\n  unix:\n    socket_path: ${directory}/server.sock\n`,
    );
    server = spawn(
      process.env.CTK_SERVER ?? resolve("../build/dev/server/ctk-server"),
      ["-c", yaml],
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
  }, 20000);
  afterAll(async () => {
    if (server?.exitCode === null) {
      const exit = new Promise((done) => server.once("exit", done));
      server.kill();
      await exit;
    }
    if (directory) await rm(directory, { recursive: true, force: true });
  });
  const request = (
    id: string,
    values: Record<string, string> = {},
  ): RunRequest => ({
    action: predefined.find((a) => a.id === id)!,
    files: [fixture],
    directory,
    endpoint,
    values,
    kinds: ["variables", "classes", "functions"],
    compileArguments: ["-std=c++20"],
    timeoutMs: 30000,
    maxResults: 100,
  });
  it("returns genuine named source-located C++ symbols and members", async () => {
    const symbols = await runAnalysis(request("symbols", { NAME: "Order" }));
    expect(symbols.errors).toEqual([]);
    expect(symbols.results.map((r) => r.name)).toEqual(
      expect.arrayContaining([
        "demo::Order",
        "demo::createOrder",
        "demo::currentOrder",
      ]),
    );
    expect(
      symbols.results.every(
        (r) =>
          r.file === fixture &&
          r.line === 1 &&
          r.excerpt.includes("namespace demo"),
      ),
    ).toBe(true);
    const members = await runAnalysis(
      request("members", { CLASS_NAME: "demo::Order", MEMBER_KIND: "All" }),
    );
    expect(members.errors).toEqual([]);
    expect(members.results.map((r) => r.name)).toEqual(
      expect.arrayContaining(["demo::Order::quantity", "demo::Order::valid"]),
    );
    expect(members.results).toHaveLength(2);
  }, 30000);
  it("normalizes parameterized native script emissions", async () => {
    const source =
      '// @ctk {"parameters":[{"name":"CLASS_NAME","label":"Class","default":"demo::Order"}]}\nemit match fieldDecl(isExpansionInMainFile(), hasParent(cxxRecordDecl(hasName(${CLASS_NAME})))).bind("symbol");';
    const report = await runAnalysis({
      ...request("symbols"),
      action: scriptAction("example.ctk", source),
      values: {},
    });
    expect(report.errors).toEqual([]);
    expect(report.results.map((r) => r.name)).toEqual([
      "demo::Order::quantity",
    ]);
    expect(report.output[0]).toContain("quantity");
  }, 30000);
  it("preserves successful files and reports invalid scripts", async () => {
    const report = await runAnalysis({
      ...request("symbols"),
      files: [fixture, resolve(directory, "missing.cc")],
    });
    expect(report.results.length).toBeGreaterThan(0);
    expect(report.errors).toHaveLength(1);
    expect(report.files).toBe(1);
    expect(
      (
        await runAnalysis({
          ...request("symbols"),
          action: scriptAction("bad.ctk", "not valid syntax;"),
        })
      ).errors,
    ).toHaveLength(1);
  }, 30000);
  it("reports truncation and treats symbol input as a literal name", async () => {
    const limited = await runAnalysis({ ...request("symbols"), maxResults: 1 });
    expect(limited.errors).toEqual([]);
    expect(limited.results).toHaveLength(1);
    expect(limited.truncated).toBe(true);
    expect(
      (await runAnalysis(request("symbols", { NAME: ".*" }))).results,
    ).toEqual([]);
  }, 30000);
  it("runs the packaged worker and cancels without publishing results", async () => {
    expect(
      (
        await startWorker(
          resolve("dist/worker.js"),
          request("symbols"),
          () => {},
        ).completion
      ).results.length,
    ).toBeGreaterThan(0);
    const cancelled = startWorker(
      resolve("dist/worker.js"),
      request("symbols"),
      () => {},
    );
    cancelled.cancel();
    await expect(cancelled.completion).rejects.toThrow("cancelled");
  }, 30000);
});
