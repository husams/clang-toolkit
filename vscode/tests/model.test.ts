import { describe, expect, it } from "vitest";
import { describeBinding } from "../src/engine.js";
import {
  predefined,
  queries,
  renderScript,
  scriptAction,
  validateParameters,
} from "../src/model.js";

describe("shared action catalog", () => {
  it("uses presets and rejects an empty symbol filter", () => {
    expect(predefined.filter((a) => a.kind === "symbols")).toHaveLength(4);
    expect(queries(predefined[0]!, { NAME: 'A.*"' }, ["classes"])[0]).toContain(
      "matchesName(",
    );
    expect(() => queries(predefined[0]!, {}, [])).toThrow("symbol kind");
  });
  it("scopes members to their owning class and selected kind", () => {
    const action = predefined.find((a) => a.id === "members")!;
    const result = queries(
      action,
      { CLASS_NAME: "demo::Order", MEMBER_KIND: "Fields" },
      [],
    );
    expect(result).toHaveLength(1);
    expect(result[0]).toContain(
      'hasParent(cxxRecordDecl(hasName("demo::Order")))',
    );
    expect(result[0]).not.toContain("cxxMethodDecl");
    expect(() => validateParameters(action, {})).toThrow(
      "Class name is required",
    );
    expect(() =>
      validateParameters(action, { CLASS_NAME: "X", MEMBER_KIND: "bad" }),
    ).toThrow("Invalid Member kind");
  });
  it("rejects reserved, duplicate and incomplete parameter definitions", () => {
    expect(() =>
      scriptAction(
        "a.ctk",
        '// @ctk {"parameters":[{"name":"FILE","label":"File"}]}',
      ),
    ).toThrow();
    expect(() =>
      scriptAction(
        "a.ctk",
        '// @ctk {"parameters":[{"name":"X","label":"X"},{"name":"X","label":"X"}]}',
      ),
    ).toThrow("unique");
    expect(() =>
      scriptAction(
        "a.ctk",
        '// @ctk {"parameters":[{"name":"X","label":"X","kind":"choice"}]}',
      ),
    ).toThrow();
  });
  it("escapes parameters so their contents cannot become script code", () => {
    const value = 'x"; emit "injected';
    const source = renderScript("emit ${NAME};", { NAME: value }, "a.cc");
    expect(JSON.parse(source.slice(5, -1))).toBe(value);
    expect(renderScript("parse ${FILE};", {}, "/tmp/a b.cc")).toBe(
      'parse "/tmp/a b.cc";',
    );
    expect(() => renderScript("emit ${MISSING};", {}, "a.cc")).toThrow(
      "MISSING",
    );
  });
  it("does not fabricate source locations for unsupported values", () => {
    expect(describeBinding({ location: null } as never)).toBeUndefined();
  });
  it("resolves script defaults and optional empty values before execution", () => {
    const action = scriptAction(
      "a.ctk",
      '// @ctk {"parameters":[{"name":"NAME","label":"Name","default":"Order"},{"name":"OPTIONAL","label":"Optional","required":false}]}',
    );
    expect(validateParameters(action, {})).toEqual({
      NAME: "Order",
      OPTIONAL: "",
    });
  });
});
