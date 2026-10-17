import { expect, it } from "vitest";
import { compilerDiagnostics } from "../src/compiler-diagnostics.js";

it("extracts exact compiler locations and distinct errors from an RPC failure", () => {
  const first =
    "/source dir/λ.cpp:3:42: error: use of undeclared identifier 'missing'";
  expect(
    compilerDiagnostics(
      `Clang could not build an AST\n${first}\n${first}\ninclude/base.hpp:9:2: fatal error: 'absent.hpp' file not found\n  9 | #include "absent.hpp"\n    |  ^`,
    ),
  ).toEqual([
    {
      file: "/source dir/λ.cpp",
      line: 3,
      column: 42,
      message: "use of undeclared identifier 'missing'",
    },
    {
      file: "include/base.hpp",
      line: 9,
      column: 2,
      message: "'absent.hpp' file not found",
    },
  ]);
});
it("keeps Windows path colons and removes terminal colors", () => {
  expect(
    compilerDiagnostics(
      "\u001b[31mC:\\project\\demo.cpp:12:8: error: expected ';'\u001b[0m",
    ),
  ).toEqual([
    {
      file: "C:\\project\\demo.cpp",
      line: 12,
      column: 8,
      message: "expected ';'",
    },
  ]);
});
it("does not invent locations for service failures, source excerpts, or invalid coordinates", () => {
  expect(
    compilerDiagnostics(
      "Clang could not build an AST for /demo.cpp\nConnection refused\n/demo.cpp:0:1: error: invalid\n/demo.cpp:1:0: error: invalid\n/demo.cpp:9007199254740992:1: error: invalid\n/demo.cpp:1:1: note: context\n  int value = error;",
    ),
  ).toEqual([]);
});
