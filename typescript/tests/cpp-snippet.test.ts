import {
  type CallOptions,
  type ClientUnaryCall,
  Metadata,
  type requestCallback,
} from "@grpc/grpc-js";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ParseRequest } from "../src/generated/ctk/match/v1/ParseRequest.js";
import { Client } from "../src/index.js";

const wire = vi.hoisted(() => ({ parse: vi.fn(), closeSession: vi.fn() }));

vi.mock("../src/grpc-transport.js", () => ({
  GrpcTransport: class {
    matches = { Parse: wire.parse, CloseSession: wire.closeSession };
    invoke<T>(
      start: (
        metadata: Metadata,
        options: CallOptions,
        callback: requestCallback<T>,
      ) => ClientUnaryCall,
    ): Promise<T> {
      return new Promise((resolve, reject) => {
        start(new Metadata(), {}, (error, response) => {
          if (error) reject(error);
          else if (response === undefined)
            reject(new Error("missing response"));
          else resolve(response);
        });
      });
    }
    close(): void {}
  },
}));

beforeEach(() => {
  wire.parse.mockReset();
  wire.closeSession.mockReset();
  wire.parse.mockImplementation((_request, _metadata, _options, callback) => {
    callback(null, {
      sessionId: "31f15cce-29b0-4b05-bbf9-5cae8ddcb1ca",
      resultRevision: "1",
      sourceFile: "/tmp/ctk-snippet/code.cpp",
    });
    return {};
  });
  wire.closeSession.mockImplementation(
    (_request, _metadata, _options, callback) => {
      callback(null, {});
      return {};
    },
  );
});

describe("temporary C++ snippets", () => {
  it("borrows file settings and preserves literal source and returned path", async () => {
    await using client = new Client("unix:///unused.sock", {
      workingDirectory: "/project",
      compileArguments: ["-std=c++20"],
    });
    // biome-ignore lint/suspicious/noTemplateCurlyInString: C++ source is passed literally.
    const code = "TemplateType<MyTest> test;\ntest.add(MyTest{}); // ${raw}";
    await using tree = await client.parseCpp(code, {
      file: "src/example.cpp",
      includes: ["template_type.hpp"],
    });
    const request = wire.parse.mock.calls[0]?.[0] as ParseRequest;
    expect(request).toEqual({
      workingDirectory: "/project",
      compileArguments: ["-std=c++20"],
      compilationDatabase: "",
      cppSnippet: {
        code,
        settingsFile: "src/example.cpp",
        includes: ["template_type.hpp"],
        translationUnit: false,
      },
    });
    expect(tree.file).toBe("/tmp/ctk-snippet/code.cpp");
    expect(tree.options.workingDirectory).toBe("/project");
    expect(tree.closed).toBe(false);
  });

  it("supports optional borrowing and headers and explicit translation units", async () => {
    await using client = new Client("unix:///unused.sock");
    await using tree = await client.parseCpp("int answer() { return 42; }", {
      translationUnit: true,
      compileArguments: ["-DANSWER=42"],
      compilationDatabase: "/project/build",
    });
    const request = wire.parse.mock.calls[0]?.[0] as ParseRequest;
    expect(request.cppSnippet).toMatchObject({
      settingsFile: "",
      includes: [],
      translationUnit: true,
    });
    expect(request.compileArguments).toEqual(["-DANSWER=42"]);
    expect(request.compilationDatabase).toBe("/project/build");
    expect(tree.closed).toBe(false);
  });

  it("rejects malformed snippet options before submitting a parse", async () => {
    await using client = new Client("unix:///unused.sock");
    expect(() => client.parseCpp("int value;", { file: "" })).toThrow();
    expect(() => client.parseCpp("int value;", { includes: [""] })).toThrow();
    expect(wire.parse).not.toHaveBeenCalled();
  });
});
