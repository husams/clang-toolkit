import { describe, expect, it } from "vitest";
import type { Result } from "../src/model.js";
import {
  selectedSource,
  sourceOffsets,
  sourceTarget,
} from "../src/source-range.js";

const file = "/workspace/demo.cpp";
const node = (range: unknown): Result => ({
  id: "child",
  name: "CallExpr",
  kind: "Expression",
  file,
  line: 1,
  column: 1,
  excerpt: "",
  raw: { binding: { range } },
});
const point = (offset: number, line = 1, column = offset + 1) => ({
  valid: true,
  file,
  line,
  column,
  offset: String(offset),
});
describe("AST source ranges", () => {
  it("normalizes editor whitespace and a trailing statement terminator", () => {
    const text = "\n  return target(); \n";
    expect(selectedSource(file, text, 0, text.length)).toEqual({
      file,
      start: 3,
      end: 18,
    });
    expect(selectedSource(file, text, text.length, 0)).toEqual(
      selectedSource(file, text, 0, text.length),
    );
  });
  it("converts editor selections after Unicode to byte ranges", () => {
    const text = "// café 😀\ntarget()";
    const start = text.indexOf("target");
    expect(selectedSource(file, text, start, text.length)).toEqual({
      file,
      start: Buffer.byteLength(text.slice(0, start)),
      end: Buffer.byteLength(text),
    });
  });
  it("ignores empty and whitespace-only editor selections", () => {
    expect(selectedSource(file, "   ", 0, 3)).toBeUndefined();
    expect(selectedSource(file, "code", 2, 2)).toBeUndefined();
  });
  it("includes the final token using the server's exclusive end", () => {
    const text = "return secondTarget(2);";
    const target = sourceTarget(
      node({
        expansionBegin: point(7),
        expansionEnd: point(21),
        expansionEndExclusive: point(22),
      }),
    );
    expect(target).toBeDefined();
    const range = sourceOffsets(target!, text)!;
    expect(text.slice(range.start, range.end)).toBe("secondTarget(2)");
  });
  it("maps UTF-8 offsets to UTF-16 selections across lines and CRLF", () => {
    const text = '// café 😀\r\nreturn "é😀";';
    const start = text.indexOf('"é');
    const end = text.lastIndexOf('"') + 1;
    const target = sourceTarget(
      node({
        expansionBegin: point(Buffer.byteLength(text.slice(0, start))),
        expansionEndExclusive: point(Buffer.byteLength(text.slice(0, end))),
      }),
    )!;
    expect(sourceOffsets(target, text)).toEqual({ start, end });
  });
  it("uses byte-based columns when an older server omits offsets", () => {
    const text = "// 😀\r\n/* é😀 */ target();";
    const column = Buffer.byteLength("/* é😀 */ ") + 1;
    const target = sourceTarget(
      node({
        expansionBegin: { valid: true, file, line: 2, column },
        expansionEndExclusive: {
          valid: true,
          file,
          line: 2,
          column: column + 8,
        },
      }),
    )!;
    const range = sourceOffsets(target, text)!;
    expect(text.slice(range.start, range.end)).toBe("target()");
  });
  it("uses the complete macro expansion rather than its spelling in another file", () => {
    const text = "CALL(target)";
    const target = sourceTarget(
      node({
        expansionBegin: point(0),
        expansionEndExclusive: point(text.length),
        spellingBegin: { ...point(0), file: "/workspace/macros.hpp" },
      }),
    )!;
    expect(target.file).toBe(file);
    expect(sourceOffsets(target, text)).toEqual({ start: 0, end: text.length });
  });
  it("never guesses a final token length or spans different files", () => {
    for (const end of [
      undefined,
      { ...point(8), file: "/other.hpp" },
      point(1),
      point(500),
    ]) {
      const target = sourceTarget(
        node({
          expansionBegin: point(3),
          expansionEnd: point(8),
          expansionEndExclusive: end,
        }),
      )!;
      expect(sourceOffsets(target, "abcdefghij")).toEqual({ start: 3, end: 3 });
    }
  });
  it("rejects out-of-document and mid-codepoint positions", () => {
    const target = sourceTarget(
      node({ expansionBegin: point(1), expansionEndExclusive: point(4) }),
    )!;
    expect(sourceOffsets(target, "😀")).toBeUndefined();
    expect(
      sourceOffsets(
        { ...target, begin: { ...target.begin, offset: 100 } },
        "😀",
      ),
    ).toBeUndefined();
    const missingLine = sourceTarget(
      node({ expansionBegin: { valid: true, file, line: 3, column: 1 } }),
    )!;
    expect(sourceOffsets(missingLine, "only one line")).toBeUndefined();
  });
  it("does not invent a location for nodes without source", () => {
    expect(
      sourceTarget({ ...node({}), file: "", locationValid: false } as Result),
    ).toBeUndefined();
  });
});
