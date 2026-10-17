import {
  astBinding,
  field,
  nativeKind,
  readable,
  record,
  spelling,
} from "./ast-facts.js";
import type { AstEntry } from "./ast-model.js";
import type { Result } from "./model.js";

export interface SemanticRow {
  id?: string;
  values: string[];
}
export interface SemanticSection {
  title: string;
  columns: string[];
  rows: SemanticRow[];
}
export function astNode(result: Result): Record<string, unknown> {
  const binding = astBinding(result);
  return record(
    record(binding.node)[nativeKind(result)] ?? binding.baseSpecifier,
  );
}
export function nodeType(result: Result): string {
  const node = astNode(result);
  return (
    spelling(field(node, "type")) ?? spelling(field(node, "declaredType")) ?? ""
  );
}
const functions = new Set([
  "functionDecl",
  "cxxMethodDecl",
  "cxxConstructorDecl",
  "cxxDestructorDecl",
  "cxxConversionDecl",
  "cxxDeductionGuideDecl",
]);
const records = new Set([
  "recordDecl",
  "cxxRecordDecl",
  "classTemplateSpecializationDecl",
  "classTemplatePartialSpecializationDecl",
]);
export function semanticSections(
  result: Result,
  children?: AstEntry[],
): SemanticSection[] {
  const kind = nativeKind(result),
    node = astNode(result),
    sections: SemanticSection[] = [];
  if (functions.has(kind) && children) {
    sections.push({
      title: "Parameters",
      columns: ["Name", "Type"],
      rows: children
        .filter((child) => nativeKind(child) === "parmVarDecl")
        .map((child, index) => {
          const raw = astNode(child),
            identifier = record(field(raw, "name")).identifier;
          return {
            id: child.id,
            values: [
              typeof identifier === "string" && identifier
                ? identifier
                : `(unnamed ${index + 1})`,
              nodeType(child),
            ],
          };
        }),
    });
  }
  if (records.has(kind) && children) {
    let access =
      field(node, "tagKind") === "TAG_KIND_CLASS" ? "Private" : "Public";
    const groups = new Map<string, SemanticRow[]>();
    for (const child of children) {
      const childKind = nativeKind(child),
        raw = astNode(child);
      if (childKind === "accessSpecDecl") {
        if (typeof raw.access === "string") access = readable(raw.access);
        continue;
      }
      if (field(raw, "isImplicit") === true) continue;
      const member = functions.has(childKind)
        ? "Method"
        : childKind === "fieldDecl" || childKind === "varDecl"
          ? "Field"
          : childKind === "typeAliasDecl" || childKind === "typedefDecl"
            ? "Type alias"
            : records.has(childKind)
              ? "Nested type"
              : "";
      if (!member) continue;
      const qualifiers = [
        field(raw, "isStatic") === true ||
        field(raw, "storageClass") === "STORAGE_CLASS_STATIC"
          ? "static"
          : "",
        field(raw, "isVirtual") === true ? "virtual" : "",
        field(raw, "isMutable") === true ? "mutable" : "",
      ]
        .filter(Boolean)
        .join(" ");
      const rows = groups.get(access) ?? [];
      rows.push({
        id: child.id,
        values: [
          child.name,
          member,
          nodeType(child) || spelling(raw.underlyingType) || "",
          qualifiers,
        ],
      });
      groups.set(access, rows);
    }
    for (const access of ["Public", "Protected", "Private"])
      if (groups.has(access))
        sections.push({
          title: `${access} members`,
          columns: ["Name", "Kind", "Type / signature", "Qualifiers"],
          rows: groups.get(access) ?? [],
        });
  }
  if (kind === "enumDecl" && children)
    sections.push({
      title: "Enumerators",
      columns: ["Name", "Value"],
      rows: children
        .filter((child) => nativeKind(child) === "enumConstantDecl")
        .map((child) => ({
          id: child.id,
          values: [
            child.name,
            String(record(astNode(child).evaluatedValue).decimalValue ?? ""),
          ],
        })),
    });
  return sections;
}
