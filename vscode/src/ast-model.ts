import { z } from "zod";
import {
  astBinding,
  clangKind,
  field,
  nativeKind,
  readable,
  record,
  spelling,
} from "./ast-facts.js";

import { type SemanticSection, semanticSections } from "./ast-semantics.js";
import type { Result } from "./model.js";

export { astBinding, nativeKind } from "./ast-facts.js";

export const astReferenceSchema = z.object({
  name: z.string().min(1),
  symbol: z.string().min(1),
});
export type AstReference = z.infer<typeof astReferenceSchema>;

export const astSemanticsSchema = z
  .object({
    referencedDeclaration: z
      .object({
        name: z.string().min(1),
        nodeId: z.string().min(1),
        symbol: z.string().optional(),
      })
      .optional(),
    inheritance: z
      .array(
        z.object({
          name: z.string(),
          depth: z.number().int().min(0),
          access: z.string(),
          virtual: z.boolean(),
          unresolved: z.boolean().optional(),
          nodeId: z.string().min(1).optional(),
          declaration: astReferenceSchema.optional(),
        }),
      )
      .optional(),
    parameters: z
      .array(z.object({ name: z.string(), type: z.string() }))
      .optional(),
    notice: z.string().optional(),
  })
  .superRefine((semantics, context) => {
    const edges = semantics.inheritance;
    if (
      edges?.some(
        (edge, index) =>
          edge.depth > (index ? (edges[index - 1]?.depth ?? -1) + 1 : 0),
      )
    )
      context.addIssue({
        code: "custom",
        message: "Inheritance path is disconnected",
      });
  });
export type AstSemantics = z.infer<typeof astSemanticsSchema>;

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
  children: z.array(astEntrySchema),
  semantics: astSemanticsSchema.optional(),
});
export const astInspectionSchema = astPageSchema
  .extend({
    parseCount: z.number().int().nonnegative(),
    root: z.object({ id: z.string(), file: z.string(), label: z.string() }),
    path: z.array(astPageSchema).min(1).optional(),
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
  sections: SemanticSection[];
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
  if (["typeAliasDecl", "typedefDecl"].includes(kind))
    add("Underlying type", spelling(node.underlyingType));
  if (kind === "enumDecl") add("Underlying type", spelling(node.integerType));
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
    ["Static", "isStatic"],
    ["Const", "isConst"],
    ["Volatile", "isVolatile"],
    ["Pure virtual", "isPureVirtual"],
    ["Mutable", "isMutable"],
    ["Bit field", "isBitField"],
    ["Scoped enum", "isScoped"],
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
    sections: semanticSections(result, children),
  };
}
