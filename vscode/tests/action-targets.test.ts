import { describe, expect, it } from "vitest";
import {
  isExcludedActionPath,
  pathIsWithin,
  selectActionTargets,
} from "../src/action-targets.js";

describe("Action target discovery", () => {
  it("returns sorted unique translation units and excludes generated trees", () => {
    expect(
      selectActionTargets(
        [
          "/repo/src/z.cpp",
          "/repo/build/generated.cpp",
          "/repo/src/a.c",
          "/repo/src/z.cpp",
          "/repo/include/api.hpp",
        ],
        10,
      ),
    ).toEqual({
      files: ["/repo/src/a.c", "/repo/src/z.cpp"],
      sourceFiles: 2,
      headerFallback: false,
    });
    expect(isExcludedActionPath("C:\\repo\\.venv\\cache\\file.cpp")).toBe(true);
  });

  it("uses headers only when no translation units exist", () => {
    expect(
      selectActionTargets(["/repo/include/z.hpp", "/repo/include/a.h"], 2),
    ).toEqual({
      files: ["/repo/include/a.h", "/repo/include/z.hpp"],
      sourceFiles: 0,
      headerFallback: true,
    });
  });

  it("includes a header-only workspace folder beside a source project", () => {
    expect(
      selectActionTargets(["/a/main.cpp", "/a/api.hpp", "/b/api.hpp"], 10, [
        "/a",
        "/b",
      ]),
    ).toEqual({
      files: ["/a/main.cpp", "/b/api.hpp"],
      sourceFiles: 1,
      headerFallback: true,
    });
  });

  it("fails explicitly when the selected manifest exceeds its configured limit", () => {
    expect(() => selectActionTargets(["a.cpp", "b.cpp"], 1)).toThrow(
      "Action scope contains more than ctk.maxFiles (1) C++ files",
    );
  });

  it("excludes ignored descendants relative to the selected root, not the root name", () => {
    expect(
      selectActionTargets(
        [
          "/repo/build/selected.cpp",
          "/repo/build/nested.cpp",
          "/repo/build/build/generated.cpp",
        ],
        10,
        ["/repo/build"],
      ).files,
    ).toEqual(["/repo/build/nested.cpp", "/repo/build/selected.cpp"]);
  });

  it("checks directory membership by path segment", () => {
    expect(pathIsWithin("/repo/src/a.cpp", ["/repo/src"])).toBe(true);
    expect(pathIsWithin("/repo/src-other/a.cpp", ["/repo/src"])).toBe(false);
  });
});
