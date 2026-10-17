import { describe, expect, it } from "vitest";
import { groupActionMatches } from "../src/action-results.js";
import type { ActionNode } from "../src/actions.js";

const binding = (
  matchId: string,
  name: string,
  file = "/caller.cpp",
): ActionNode => ({
  id: `${matchId}:${name}`,
  nodeId: `${matchId}:${name}`,
  matchId,
  binding: name,
  name: name === "callee" ? "sharedTarget" : "caller",
  file,
  kind: "FunctionDecl",
  line: 4,
  column: 1,
  excerpt: "",
  raw: {},
});

describe("action match outline", () => {
  it("hides only a root alias with an identical native payload and retains explicit aliases", () => {
    const payload = {
      node: { functionDecl: { name: "caller" } },
      symbolIdentity: "caller",
      range: { offset: 12 },
    };
    const nodes = ["caller", "alsoCaller", "root"].map((name) => ({
      ...binding("one", name),
      raw: { binding: structuredClone(payload) },
    }));
    const row = groupActionMatches(nodes)[0]?.matches[0];
    expect(row?.bindings.map((node) => node.binding)).toEqual([
      "caller",
      "alsoCaller",
    ]);
    expect(row?.anchor.binding).toBe("root");
    expect(nodes).toHaveLength(3);
  });

  it("keeps a unique root, even for nodes with the same symbol and source location", () => {
    const caller = {
      ...binding("one", "caller"),
      raw: {
        binding: {
          node: { functionDecl: {} },
          symbolIdentity: "caller",
          range: { offset: 12 },
        },
      },
    };
    const root = {
      ...binding("one", "root"),
      raw: {
        binding: {
          node: { functionDecl: {} },
          symbolIdentity: "caller",
          range: { offset: 13 },
        },
      },
    };
    expect(groupActionMatches([caller, root])[0]?.matches[0]?.bindings).toEqual(
      [caller, root],
    );
    expect(groupActionMatches([root])[0]?.matches[0]?.bindings).toEqual([root]);
  });

  it("keeps related bindings and repeated nodes in their original matches, including interleaved rows", () => {
    const results = [
      binding("one", "callee", "/callee.hpp"),
      binding("two", "callee", "/callee.hpp"),
      binding("one", "caller"),
      binding("two", "caller"),
      binding("one", "root"),
      binding("two", "root"),
    ];
    const files = groupActionMatches(results);
    expect(files).toHaveLength(1);
    expect(files[0]?.file).toBe("/caller.cpp");
    expect(
      files[0]?.matches.map((row) => ({
        id: row.id,
        anchor: row.anchor.binding,
        nodes: row.bindings.map((node) => node.nodeId),
      })),
    ).toEqual([
      {
        id: "one",
        anchor: "root",
        nodes: ["one:callee", "one:caller", "one:root"],
      },
      {
        id: "two",
        anchor: "root",
        nodes: ["two:callee", "two:caller", "two:root"],
      },
    ]);
    expect(results[0]?.file).toBe("/callee.hpp");
  });

  it("groups each complete match once under its root file even when all matches share a header binding", () => {
    const files = groupActionMatches([
      binding("one", "callee", "/shared.hpp"),
      binding("two", "callee", "/shared.hpp"),
      binding("one", "root", "/first.cpp"),
      binding("two", "root", "/second.cpp"),
    ]);
    expect(
      files.map((file) => [file.file, file.matches.map((row) => row.id)]),
    ).toEqual([
      ["/first.cpp", ["one"]],
      ["/second.cpp", ["two"]],
    ]);
    expect(
      files.flatMap((file) => file.matches.flatMap((row) => row.bindings)),
    ).toHaveLength(4);
  });

  it("uses the first binding when no automatic root exists and keeps identical locations in separate matches", () => {
    const files = groupActionMatches([
      binding("one", "caller"),
      binding("one", "callee", "/target.hpp"),
      binding("two", "caller"),
      binding("two", "callee", "/target.hpp"),
    ]);
    expect(files).toHaveLength(1);
    expect(files[0]?.matches).toHaveLength(2);
    expect(
      files[0]?.matches.every((row) => row.anchor.binding === "caller"),
    ).toBe(true);
    expect(groupActionMatches([])).toEqual([]);
  });
});
