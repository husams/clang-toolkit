import { describe, expect, it } from "vitest";
import {
  isExcludedActionPath,
  isRelevantActionSource,
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

  it("ignores source change events in excluded build and metadata trees", () => {
    const context = {
      scope: "workspace" as const,
      workspaceRoots: ["/repo"],
    };
    expect(isRelevantActionSource("/repo/src/lib.cpp", context)).toBe(true);
    expect(isRelevantActionSource("/repo/build/generated.cpp", context)).toBe(
      false,
    );
    expect(isRelevantActionSource("/repo/.git/scratch.cpp", context)).toBe(
      false,
    );
    expect(
      isRelevantActionSource("/repo/node_modules/pkg/index.cc", context),
    ).toBe(false);
    expect(isRelevantActionSource("/repo/src/README.md", context)).toBe(false);
  });

  it("conservatively invalidates for headers, including generated build headers", () => {
    expect(
      isRelevantActionSource("/repo/build/dev/api/generated/api.hpp", {
        scope: "workspace",
        workspaceRoots: ["/repo"],
      }),
    ).toBe(true);
    expect(
      isRelevantActionSource("/external/generated/config.h", {
        scope: "directory",
        workspaceRoots: ["/repo"],
        directoryTarget: "/repo/src",
      }),
    ).toBe(true);
  });

  it("keeps explicit build-root directory and file targets relevant", () => {
    expect(
      isRelevantActionSource("/repo/build/selected.cpp", {
        scope: "directory",
        workspaceRoots: ["/repo"],
        directoryTarget: "/repo/build",
      }),
    ).toBe(true);
    expect(
      isRelevantActionSource("/repo/build/selected.cpp", {
        scope: "file",
        workspaceRoots: ["/repo"],
        target: "/repo/build/selected.cpp",
      }),
    ).toBe(true);
    expect(
      isRelevantActionSource("/repo/build/nested/build/generated.cpp", {
        scope: "directory",
        workspaceRoots: ["/repo"],
        directoryTarget: "/repo/build",
      }),
    ).toBe(false);
    expect(
      isRelevantActionSource("/repo/build/other.cpp", {
        scope: "file",
        workspaceRoots: ["/repo"],
        target: "/repo/build/selected.cpp",
      }),
    ).toBe(false);
  });
});
