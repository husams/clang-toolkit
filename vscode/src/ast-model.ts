import { z } from "zod";
import type { Result } from "./model.js";

export const astEntrySchema = z.object({
  id: z.string(),
  name: z.string(),
  kind: z.string(),
  file: z.string(),
  line: z.number().int().positive(),
  column: z.number().int().positive(),
  excerpt: z.string(),
  raw: z.unknown(),
  locationValid: z.boolean(),
});
export const astPageSchema = z.object({
  node: astEntrySchema,
  children: z.array(astEntrySchema).max(1000),
});
export const astInspectionSchema = astPageSchema
  .extend({
    parseCount: z.number().int().nonnegative(),
    root: z.object({ id: z.string(), file: z.string(), label: z.string() }),
    path: z.array(astPageSchema).min(1).max(65).optional(),
  })
  .superRefine((inspection, context) => {
    const path = inspection.path;
    if (!path) return;
    if (
      path.at(-1)?.node.id !== inspection.node.id ||
      path.some((page, index) => {
        const next = path[index + 1];
        return (
          next && !page.children.some((child) => child.id === next.node.id)
        );
      })
    )
      context.addIssue({
        code: "custom",
        message: "AST source path is disconnected",
      });
  });
export type AstPage = z.infer<typeof astPageSchema>;
export type AstEntry = z.infer<typeof astEntrySchema>;
export type AstInspection = z.infer<typeof astInspectionSchema>;
export const sourceSelectionSchema = z
  .object({
    file: z.string().min(1),
    start: z.number().int().nonnegative(),
    end: z.number().int().nonnegative(),
  })
  .refine((span) => span.end >= span.start, "Source range is reversed");
export type SourceSelection = z.infer<typeof sourceSelectionSchema>;
type RecordValue = Record<string, unknown>;
const record = (value: unknown): RecordValue =>
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
const clangKind = (value: string) =>
  value
    .replace(/^cxx/, "CXX")
    .replace(/^objc/, "ObjC")
    .replace(/^./, (c) => c.toUpperCase());
function field(value: unknown, name: string, depth = 0): unknown {
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
function spelling(value: unknown): string | undefined {
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
function readable(value: string): string {
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
export interface AstProperty {
  label: string;
  value: string;
}
export interface AstDisplay {
  id: string;
  name: string;
  kind: string;
  signature: string;
  file: string;
  line: number;
  column: number;
  excerpt: string;
  locationValid: boolean;
  properties: AstProperty[];
  range: AstProperty[];
}
export function astDisplay(
  result: Result & { locationValid?: boolean },
  children?: AstEntry[],
): AstDisplay {
  const binding = astBinding(result),
    kind = nativeKind(result);
  const node = record(
    record(binding.node)[kind] ??
      binding.qualifiedType ??
      binding.baseSpecifier,
  );
  const properties: AstProperty[] = [];
  const add = (label: string, value: unknown) => {
    if (typeof value === "number" || typeof value === "boolean")
      value = String(value);
    if (typeof value === "string" && value && value.length <= 8192)
      properties.push({ label, value: readable(value) });
  };
  // This allowlist projects language semantics only. No protobuf wrappers,
  // availability states, cursor IDs, supported scopes or whole-match payloads.
  const ownType =
    spelling(field(node, "type")) ??
    spelling(field(node, "declaredType")) ??
    (kind === "qualType" ? spelling(node) : undefined);
  const returns = spelling(field(node, "returnType"));
  if (returns) add("Return type", returns);
  else add("Type", ownType);
  const canonical = field(field(node, "type"), "canonicalSpelling");
  if (typeof canonical === "string" && canonical !== ownType)
    add("Canonical type", canonical);
  add("Value category", field(node, "valueCategory"));
  add("Record kind", field(node, "tagKind"));
  add("Cast", record(node.cast).kind);
  if (["integerLiteral", "floatingLiteral"].includes(kind))
    add(
      "Literal value",
      record(node.value).unsignedDecimal ?? record(node.value).decimalValue,
    );
  for (const [label, key] of [
    ["Operator", "opcode"],
    ["Literal value", "value"],
    ["Cast", "castKind"],
    ["Access", "access"],
    ["Storage", "storageClass"],
  ]) {
    const value = field(node, key ?? "");
    if (
      typeof value === "string" &&
      /(?:UNSPECIFIED|UNKNOWN|NONE)$/.test(value)
    )
      continue;
    if (typeof value !== "object") add(label ?? "", value);
  }
  for (const [label, key] of [
    ["Definition", "isThisDeclarationADefinition"],
    ["Definition", "isCompleteDefinition"],
    ["Inline", "isInlineSpecified"],
    ["Constexpr", "isConstexpr"],
    ["Virtual", "isVirtual"],
    ["Variadic", "isVariadic"],
    ["Implicit", "isImplicit"],
    ["Deleted", "isDeleted"],
    ["Defaulted", "isDefaulted"],
  ])
    if (field(node, key ?? "") === true) add(label ?? "", "Yes");
  const call = record(binding.callSite);
  add("Dispatch", call.dispatch);
  add("Callee", call.staticCalleeName);
  add("Caller", call.callerName);
  const params = children?.filter(
    (child) => nativeKind(child) === "parmVarDecl",
  );
  if (returns && params?.length)
    add(
      "Parameters",
      params
        .map(
          (p) =>
            `${spelling(field(record(record(astBinding(p).node).parmVarDecl), "type")) ?? ""} ${p.name}`,
        )
        .join(", ")
        .trim(),
    );
  const range: AstProperty[] = [];
  const sourceRange = record(binding.range);
  for (const [label, key] of [
    ["Start", "expansionBegin"],
    ["End", "expansionEnd"],
  ]) {
    const location = record(sourceRange[key ?? ""]);
    if (
      location.valid === true &&
      typeof location.line === "number" &&
      typeof location.column === "number"
    )
      range.push({
        label: label ?? "",
        value: `Line ${location.line}, column ${location.column}`,
      });
  }
  const name =
    ["Node", "Match"].includes(result.name) && kind
      ? clangKind(kind)
      : result.name;
  const parameterText = properties.find(
    (property) => property.label === "Parameters",
  )?.value;
  return {
    id: result.id,
    name,
    kind: kind ? clangKind(kind) : result.kind,
    signature:
      returns && ownType?.startsWith(`${returns} (`)
        ? `${returns} ${name}${ownType.slice(returns.length + 1)}`
        : returns && parameterText
          ? `${returns} ${name}(${parameterText === "None" ? "" : parameterText})`
          : ownType
            ? `${name} · ${ownType}`
            : name,
    file: result.file,
    line: result.line,
    column: result.column,
    excerpt: result.excerpt,
    locationValid:
      "locationValid" in result
        ? result.locationValid === true
        : Boolean(result.file),
    properties,
    range,
  };
}
