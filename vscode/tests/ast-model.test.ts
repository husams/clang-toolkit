import { describe, expect, it } from "vitest";
import {
  type AstEntry,
  astDisplay,
  astInspectionSchema,
} from "../src/ast-model.js";

const result = (binding: unknown): AstEntry => ({
  id: "retained-id",
  name: "secondCaller",
  kind: "Function",
  file: "demo.cpp",
  line: 5,
  column: 1,
  excerpt: "int secondCaller() { return secondTarget(2); }",
  raw: { binding, match: { secretCursor: "do not show" } },
  locationValid: true,
});
describe("AST inspector projection", () => {
  it("shows readable language facts while excluding transport and CTK metadata", () => {
    const node = result({
      node: {
        functionDecl: {
          function: {
            returnType: { description: { spelling: "int" } },
            isThisDeclarationADefinition: true,
            isInlineSpecified: false,
            declarator: { type: { description: { spelling: "int ()" } } },
          },
        },
      },
      availability: [
        {
          fieldPath: "FunctionDeclInfo.body",
          state: "FIELD_STATE_UNREQUESTED",
        },
      ],
      supportedScopes: ["BINDING_MATCH_SCOPE_SUBTREE"],
      isComplete: true,
      symbolIdentity: "internal-usr",
      range: {
        expansionBegin: { valid: true, line: 5, column: 1 },
        expansionEnd: { valid: true, line: 5, column: 48 },
      },
    });
    const shallow = astDisplay(node);
    expect(shallow.properties).not.toContainEqual({
      label: "Parameters",
      value: "None",
    });
    const display = astDisplay(node, []);
    expect(display.kind).toBe("FunctionDecl");
    expect(display.signature).toBe("int secondCaller()");
    expect(display.properties).toEqual([
      { label: "Return type", value: "int" },
      { label: "Definition", value: "Yes" },
    ]);
    expect(display.range).toEqual([
      { label: "Start", value: "Line 5, column 1" },
      { label: "End", value: "Line 5, column 48" },
    ]);
    expect(JSON.stringify(display)).not.toMatch(
      /FIELD_STATE|supportedScopes|internal-usr|secretCursor|availability|isComplete/,
    );
  });
  it("keeps call expression types separate from a callee's declaration and normalizes enum labels", () => {
    const display = astDisplay(
      result({
        node: {
          callExpr: {
            call: {
              expression: {
                type: { description: { spelling: "int" } },
                valueCategory: "VALUE_CATEGORY_PRVALUE",
              },
              directCallee: {
                type: { description: { spelling: "int (int)" } },
              },
            },
          },
        },
        callSite: {
          staticCalleeName: "secondTarget",
          callerName: "secondCaller",
          dispatch: "CALL_DISPATCH_DIRECT",
        },
      }),
    );
    expect(display.kind).toBe("CallExpr");
    expect(display.properties).toEqual([
      { label: "Type", value: "int" },
      { label: "Value category", value: "prvalue" },
      { label: "Dispatch", value: "Direct" },
      { label: "Callee", value: "secondTarget" },
      { label: "Caller", value: "secondCaller" },
    ]);
  });
  it("represents auxiliary AST kinds honestly without exposing protobuf support reasons", () => {
    const display = astDisplay({
      ...result({
        unsupported: {
          clangClass: "FunctionProtoTypeLoc",
          reason: "UNSUPPORTED_TYPE_LOC",
          detail: "internal registry",
        },
      }),
      name: "Node",
      locationValid: false,
      file: "",
    });
    expect(display.kind).toBe("FunctionProtoTypeLoc");
    expect(display.name).toBe("FunctionProtoTypeLoc");
    expect(display.locationValid).toBe(false);
    expect(display.properties).toEqual([]);
    expect(JSON.stringify(display)).not.toMatch(/UNSUPPORTED|registry/);
  });
  it("rejects malformed or unbounded native inspection responses", () => {
    expect(() =>
      astInspectionSchema.parse({ node: {}, children: [], parseCount: 0 }),
    ).toThrow();
    expect(() =>
      astInspectionSchema.parse({
        node: result({}),
        children: Array(1001).fill(result({})),
        parseCount: 1,
      }),
    ).toThrow();
  });
  it("formats record kinds, casts, operators and literal values as AST facts", () => {
    expect(
      astDisplay(
        result({
          node: {
            cxxRecordDecl: {
              record: {
                tag: { tagKind: "TAG_KIND_STRUCT", isCompleteDefinition: true },
              },
            },
          },
        }),
      ).properties,
    ).toEqual([
      { label: "Record kind", value: "Struct" },
      { label: "Definition", value: "Yes" },
    ]);
    expect(
      astDisplay(
        result({
          node: {
            implicitCastExpr: {
              cast: { kind: "CAST_KIND_FUNCTION_TO_POINTER_DECAY" },
            },
          },
        }),
      ).properties,
    ).toContainEqual({ label: "Cast", value: "Function to pointer decay" });
    expect(
      astDisplay(
        result({ node: { binaryOperator: { opcode: "BINARY_OPCODE_MUL" } } }),
      ).properties,
    ).toContainEqual({ label: "Operator", value: "*" });
    const literal = astDisplay(
      result({
        node: {
          integerLiteral: {
            value: {
              bitWidth: 32,
              littleEndianBits: "AgAAAA==",
              unsignedDecimal: "2",
            },
          },
        },
      }),
    );
    expect(literal.properties).toEqual([
      { label: "Literal value", value: "2" },
    ]);
    expect(JSON.stringify(literal)).not.toContain("AgAAAA==");
  });
});
