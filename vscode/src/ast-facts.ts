import type { Result } from "./model.js";

type RecordValue = Record<string, unknown>;
export const record = (value: unknown): RecordValue =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as RecordValue)
    : {};
export function astBinding(result: Result): RecordValue {
  const raw = record(result.raw);
  return record(raw.binding ?? raw);
}
export function nativeKind(result: Result): string {
  const binding = astBinding(result);
  const unsupported = record(binding.unsupported);
  return (
    Object.keys(record(binding.node))[0] ??
    (typeof unsupported.clangClass === "string"
      ? unsupported.clangClass
      : binding.qualifiedType
        ? "qualType"
        : binding.baseSpecifier
          ? "cxxBaseSpecifier"
          : "")
  );
}
export const clangKind = (value: string) =>
  value
    .replace(/^cxx/, "CXX")
    .replace(/^objc/, "ObjC")
    .replace(/^./, (c) => c.toUpperCase());
export function field(value: unknown, name: string, depth = 0): unknown {
  if (depth > 12) return undefined;
  const object = record(value);
  if (object[name] !== undefined) return object[name];
  for (const [key, child] of Object.entries(object)) {
    if (
      ["directCallee", "containingScope", "callee", "referencedDecl"].includes(
        key,
      )
    )
      continue;
    const found = field(child, name, depth + 1);
    if (found !== undefined) return found;
  }
  return undefined;
}
export function spelling(value: unknown): string | undefined {
  const text = field(value, "spelling");
  return typeof text === "string" && text ? text : undefined;
}
const enums: Record<string, string> = {
  VALUE_CATEGORY_LVALUE: "lvalue",
  VALUE_CATEGORY_XVALUE: "xvalue",
  VALUE_CATEGORY_PRVALUE: "prvalue",
  CALL_DISPATCH_DIRECT: "Direct",
  CALL_DISPATCH_VIRTUAL: "Virtual",
  CALL_DISPATCH_INDIRECT: "Indirect",
  STORAGE_CLASS_STATIC: "Static",
  STORAGE_CLASS_EXTERN: "Extern",
  ACCESS_SPECIFIER_PUBLIC: "Public",
  ACCESS_SPECIFIER_PRIVATE: "Private",
  ACCESS_SPECIFIER_PROTECTED: "Protected",
  BINARY_OPCODE_ADD: "+",
  BINARY_OPCODE_SUB: "-",
  BINARY_OPCODE_MUL: "*",
  BINARY_OPCODE_DIV: "/",
  BINARY_OPCODE_REM: "%",
  BINARY_OPCODE_ASSIGN: "=",
  BINARY_OPCODE_EQ: "==",
  BINARY_OPCODE_NE: "!=",
  BINARY_OPCODE_LT: "<",
  BINARY_OPCODE_LE: "<=",
  BINARY_OPCODE_GT: ">",
  BINARY_OPCODE_GE: ">=",
  BINARY_OPCODE_L_AND: "&&",
  BINARY_OPCODE_L_OR: "||",
  BINARY_OPCODE_AND: "&",
  BINARY_OPCODE_OR: "|",
  BINARY_OPCODE_XOR: "^",
  BINARY_OPCODE_SHL: "<<",
  BINARY_OPCODE_SHR: ">>",
  BINARY_OPCODE_COMMA: ",",
};
export function readable(value: string): string {
  return (
    enums[value] ??
    (/^(?:CAST_KIND|CALL_DISPATCH|STORAGE_CLASS|ACCESS_SPECIFIER|VALUE_CATEGORY|BINARY_OPCODE|UNARY_OPCODE|TAG_KIND)_/.test(
      value,
    )
      ? value
          .replace(
            /^(?:CAST_KIND|CALL_DISPATCH|STORAGE_CLASS|ACCESS_SPECIFIER|VALUE_CATEGORY|BINARY_OPCODE|UNARY_OPCODE|TAG_KIND)_/,
            "",
          )
          .toLowerCase()
          .replaceAll("_", " ")
          .replace(/^./, (c) => c.toUpperCase())
      : value)
  );
}
