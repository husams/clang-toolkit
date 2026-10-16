import { describe, expect, it } from "vitest";
import {
  actionCompletionSource,
  ctkLiteral,
  newActionName,
  parseNodeAction,
  resolveArguments,
  updatedActionValues,
  validateCatalog,
} from "../src/actions.js";

const source = (
  yaml: string,
  body = 'match functionDecl().bind("function") in node',
) =>
  `---\nname: find-function\ndescription: Find function definitions.\n${yaml}\n---\n${body}`;
describe("YAML action files", () => {
  it("updates argument defaults while preserving explicit values and removing obsolete inputs", () => {
    const previous = parseNodeAction(
      "action",
      source(
        "arguments:\n  - name: name\n    description: Name\n    default: before\n  - name: count\n    description: Count\n    type: number\n    default: 2\n  - name: removed\n    description: Removed\n    default: old",
      ),
    );
    const next = parseNodeAction(
      "action",
      source(
        "arguments:\n  - name: name\n    description: Renamed hint\n    default: after\n  - name: count\n    description: Count\n    type: number\n    default: 3\n  - name: added\n    description: Added\n    type: boolean\n    default: true",
      ),
    );
    expect(
      updatedActionValues(
        previous,
        { name: "chosen", count: "2", removed: "old" },
        next,
      ),
    ).toEqual({ name: "chosen", count: "3", added: "true" });
    expect(
      updatedActionValues(previous, { name: "before", count: "4" }, next),
    ).toEqual({ name: "after", count: "4", added: "true" });
    const changedType = parseNodeAction(
      "action",
      source(
        "arguments:\n  - name: count\n    description: Count\n    default: text",
      ),
    );
    expect(updatedActionValues(previous, { count: "4" }, changedType)).toEqual({
      count: "text",
    });
    const required = parseNodeAction(
      "action",
      source("arguments:\n  - name: name\n    description: Name"),
    );
    expect(updatedActionValues(undefined, {}, required)).toEqual({});
    expect(updatedActionValues(required, { name: "chosen" }, required)).toEqual(
      { name: "chosen" },
    );
  });
  it("creates unique names without overwriting existing or invalid action files", () => {
    expect(newActionName([], [])).toBe("my-action");
    const existing = parseNodeAction(
      "alias.ctk-action",
      source("arguments: []").replace("find-function", "my_action"),
    );
    expect(newActionName([existing], ["MY-ACTION-2.ctk-action"])).toBe(
      "my-action-3",
    );
    expect(newActionName([], ["my-action.ctk-action"])).toBe("my-action-2");
  });
  it("maps completion edits back across YAML and Unicode without evaluating the body", () => {
    const original = source("arguments: []", "// 🧭\nmatch functionDecl(isDef");
    const mapped = actionCompletionSource(
      "example.ctk-action",
      original,
      [...original].length,
    );
    expect(mapped).toBeDefined();
    expect(mapped!.source).toContain("let find_function(node)");
    const editStart = [
      ...mapped!.source.slice(0, mapped!.source.indexOf("isDef")),
    ].length;
    expect(editStart + mapped!.delta).toBe(
      [...original.slice(0, original.indexOf("isDef"))].length,
    );
    expect(actionCompletionSource("example", original, 4)).toBeUndefined();
    expect(
      actionCompletionSource("example", "---\nname: bad\n---\n", 30),
    ).toBeUndefined();
    expect(
      actionCompletionSource("example", source("arguments: []", ""), 1000),
    ).toBeDefined();
  });
  it("generates a callable with an implicit node and typed defaults", () => {
    const action = parseNodeAction(
      "example.ctk-action",
      source(
        'arguments:\n  - name: name\n    description: Exact function name\n    default: ""',
      ),
    );
    expect(action.generated).toBe(
      "let find_function(node, name = '') = {\n    match functionDecl().bind(\"function\") in node\n}",
    );
    expect(action.arguments.map((arg) => arg.name)).toEqual(["name"]);
    expect(resolveArguments(action, {})).toEqual({ name: "" });
    expect(
      parseNodeAction(
        "example",
        source("arguments: []").replaceAll("\n", "\r\n"),
      ).body,
    ).toContain("match functionDecl");
  });
  it("rejects missing delimiters, duplicated/reserved names, aliases and invalid defaults", () => {
    expect(() => parseNodeAction("bad", "name: bad")).toThrow("front matter");
    for (const yaml of [
      "name: duplicated",
      "arguments:\n  - name: node\n    description: Cannot override input",
      "arguments:\n  - name: name\n    description: First\n  - name: name\n    description: Duplicate",
      "arguments:\n  - name: count\n    description: Count\n    type: number\n    default: nope",
      'arguments:\n  - name: optional\n    description: Optional\n    default: ""\n  - name: required\n    description: Required',
      "arguments: &args []\nother: *args",
    ])
      expect(() => parseNodeAction("bad", source(yaml))).toThrow();
    expect(() => parseNodeAction("bad", source("arguments: []", ""))).toThrow(
      "body",
    );
  });
  it("does not execute bodies while discovering actions and rejects catalog collisions", () => {
    const action = parseNodeAction(
      "safe",
      source("arguments: []", 'print "not executed"'),
    );
    expect(action.body).toBe('print "not executed"');
    const alias = parseNodeAction(
      "alias",
      source("arguments: []").replace("find-function", "find_function"),
    );
    expect(() => validateCatalog([action, alias])).toThrow(
      "Duplicate action name",
    );
  });
  it("resolves typed values without interpreting string contents as code", () => {
    const action = parseNodeAction(
      "typed",
      source(
        "arguments:\n  - name: name\n    description: Name\n  - name: count\n    description: Count\n    type: number\n    default: 2\n  - name: enabled\n    description: Enabled\n    type: boolean\n    default: false",
      ),
    );
    const input = 'x"; print 999; {1 + 2}';
    expect(
      resolveArguments(action, { name: input, count: "4", enabled: "true" }),
    ).toEqual({ name: input, count: 4, enabled: true });
    expect(() => resolveArguments(action, {})).toThrow("required");
    expect(() =>
      resolveArguments(action, { name: "x", enabled: "yes" }),
    ).toThrow("true or false");
    expect(() =>
      resolveArguments(action, { name: "x", count: "Infinity" }),
    ).toThrow("number");
    expect(ctkLiteral("a'b\\c\n{test}")).toBe("'a\\'b\\\\c\\n{test}'");
  });
});
