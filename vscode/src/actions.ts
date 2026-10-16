import { createHash } from "node:crypto";
import { parseDocument } from "yaml";
import { z } from "zod";

const identifier = /^[A-Za-z_][A-Za-z0-9_]*$/;
const reserved = new Set([
  "node",
  "let",
  "if",
  "else",
  "in",
  "match",
  "parse",
  "true",
  "false",
  "null",
  "foreach",
  "while",
  "import",
  "__proto__",
  "constructor",
  "prototype",
]);
const scalar = z.union([z.string(), z.number().finite(), z.boolean()]);
export type ArgumentValue = z.infer<typeof scalar>;
const argumentSchema = z
  .object({
    name: z
      .string()
      .regex(identifier)
      .refine(
        (name) => !reserved.has(name) && !name.startsWith("__ctk_"),
        "Reserved argument name",
      ),
    description: z.string().min(1),
    type: z.enum(["string", "number", "boolean"]).default("string"),
    default: scalar.optional(),
  })
  .strict();
const metadataSchema = z
  .object({
    name: z.string().regex(/^[A-Za-z_][A-Za-z0-9_-]*$/),
    description: z.string().min(1),
    arguments: z.array(argumentSchema).default([]),
  })
  .strict();
export type ActionArgument = z.infer<typeof argumentSchema>;
export interface NodeAction {
  id: string;
  title: string;
  description: string;
  callable: string;
  arguments: ActionArgument[];
  body: string;
  generated: string;
  path: string;
  origin: "Predefined" | "Workspace";
  revision: string;
  bodyLine: number;
}
export function ctkLiteral(value: ArgumentValue): string {
  if (typeof value !== "string") return String(value);
  return `'${value.replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/\r/g, "\\r").replace(/\n/g, "\\n").replace(/\t/g, "\\t")}'`;
}
export function parseNodeAction(
  path: string,
  source: string,
  origin: NodeAction["origin"] = "Workspace",
): NodeAction {
  if (Buffer.byteLength(source) > 1024 * 1024)
    throw new Error("Action exceeds 1 MiB");
  const parts =
    /^\uFEFF?---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)([\s\S]*)$/.exec(
      source,
    );
  if (!parts)
    throw new Error(`${path}: expected YAML front matter between --- lines`);
  const yaml = parseDocument(parts[1] ?? "", {
    uniqueKeys: true,
    version: "1.2",
  });
  if (yaml.errors.length || yaml.warnings.length)
    throw new Error(
      `${path}: ${[...yaml.errors, ...yaml.warnings].map((e) => e.message).join("; ")}`,
    );
  const metadata = metadataSchema.parse(yaml.toJS({ maxAliasCount: 0 }));
  const callable = metadata.name.replaceAll("-", "_");
  if (reserved.has(callable) || callable.startsWith("__ctk_"))
    throw new Error("Reserved action name");
  const names = new Set<string>();
  let optional = false;
  for (const argument of metadata.arguments) {
    if (names.has(argument.name))
      throw new Error("Argument names must be unique");
    names.add(argument.name);
    if (argument.default !== undefined) {
      if (typeof argument.default !== argument.type)
        throw new Error(
          `Default for ${argument.name} must be ${argument.type}`,
        );
      optional = true;
    } else if (optional)
      throw new Error(
        "Required arguments must precede arguments with defaults",
      );
  }
  const body = (parts[2] ?? "").trim();
  if (!body) throw new Error(`${path}: action needs a CTK body`);
  const parameters = [
    "node",
    ...metadata.arguments.map(
      (arg) =>
        `${arg.name}${arg.default === undefined ? "" : ` = ${ctkLiteral(arg.default)}`}`,
    ),
  ];
  return {
    id: metadata.name,
    title: metadata.name
      .replaceAll(/[-_]/g, " ")
      .replace(/^./, (letter) => letter.toUpperCase()),
    description: metadata.description,
    callable,
    arguments: metadata.arguments,
    body,
    generated: `let ${callable}(${parameters.join(", ")}) = {\n${body
      .split("\n")
      .map((line) => `    ${line}`)
      .join("\n")}\n}`,
    path,
    origin,
    revision: createHash("sha256").update(source).digest("hex"),
    bodyLine: source
      .slice(0, source.length - (parts[2]?.length ?? 0))
      .split("\n").length,
  };
}
export function resolveArguments(
  action: NodeAction,
  values: Record<string, string>,
): Record<string, ArgumentValue> {
  const resolved: Record<string, ArgumentValue> = {};
  for (const arg of action.arguments) {
    const value = values[arg.name];
    if (value === undefined || (value === "" && arg.type !== "string")) {
      if (arg.default === undefined)
        throw new Error(`${arg.description} is required`);
      resolved[arg.name] = arg.default;
    } else if (arg.type === "string") {
      if (arg.default === undefined && !value.trim())
        throw new Error(`${arg.description} is required`);
      resolved[arg.name] = value;
    } else if (arg.type === "boolean") {
      if (value !== "true" && value !== "false")
        throw new Error(`${arg.name} must be true or false`);
      resolved[arg.name] = value === "true";
    } else {
      if (
        !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim()) ||
        !Number.isFinite(Number(value))
      )
        throw new Error(`${arg.name} must be a number`);
      resolved[arg.name] = Number(value);
    }
  }
  return resolved;
}
export function updatedActionValues(
  previous: NodeAction | undefined,
  values: Record<string, string>,
  next: NodeAction,
): Record<string, string> {
  const updated: Record<string, string> = {};
  for (const argument of next.arguments) {
    const before = previous?.arguments.find(
      (item) => item.name === argument.name,
    );
    const value = values[argument.name];
    if (
      before?.type === argument.type &&
      value !== undefined &&
      (before.default === undefined || value !== String(before.default))
    )
      updated[argument.name] = value;
    else if (argument.default !== undefined)
      updated[argument.name] = String(argument.default);
  }
  return updated;
}
export function validateCatalog(actions: NodeAction[]): NodeAction[] {
  const seen = new Set<string>();
  for (const action of actions) {
    if (seen.has(action.callable))
      throw new Error(
        `Duplicate action name: ${action.id}; rename one definition`,
      );
    seen.add(action.callable);
  }
  return actions;
}
export const actionResultSchema = z.object({
  id: z.string(),
  nodeId: z.string(),
  matchId: z.string(),
  binding: z.string(),
  name: z.string(),
  kind: z.string(),
  file: z.string(),
  line: z.number().int().positive(),
  column: z.number().int().positive(),
  excerpt: z.string(),
  raw: z.unknown(),
});
export type ActionNode = z.infer<typeof actionResultSchema>;
export const actionReportSchema = z.object({
  results: z.array(actionResultSchema),
  output: z.array(z.string()),
  runId: z.string(),
  input: z.object({ id: z.string(), label: z.string(), file: z.string() }),
  matches: z.number().int().nonnegative(),
  truncated: z.boolean(),
  parseCount: z.number().int().nonnegative(),
});
export type ActionReport = z.infer<typeof actionReportSchema>;

export const actionTemplate = `---\nname: my-action\ndescription: Find function definitions under the selected node.\narguments: []\n---\nmatch functionDecl(isDefinition()).bind("function") in node\n`;

export function newActionName(
  actions: readonly NodeAction[],
  files: readonly string[],
): string {
  const callables = new Set(actions.map((action) => action.callable));
  const paths = new Set(files.map((file) => file.toLowerCase()));
  for (let index = 1; ; index++) {
    const name = index === 1 ? "my-action" : `my-action-${index}`;
    if (
      !callables.has(name.replaceAll("-", "_")) &&
      !paths.has(`${name}.ctk-action`)
    )
      return name;
  }
}

// Completion inspects a normal CTK function without executing the YAML or body.
// Offsets are code points, matching the console completion protocol.
export function actionCompletionSource(
  path: string,
  source: string,
  cursor: number,
): { source: string; cursor: number; delta: number } | undefined {
  const header = /^\uFEFF?---\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/.exec(
    source,
  )?.[0];
  if (!header) return undefined;
  const start = [...header].length;
  if (cursor < start) return undefined;
  let action: NodeAction;
  try {
    action = parseNodeAction(path, `${source}\n0`);
  } catch {
    return undefined;
  }
  const prefix = `let ${action.callable}(node${action.arguments.map((a) => `, ${a.name}`).join("")}) = {\n`;
  const delta = start - [...prefix].length;
  return {
    source: `${prefix}${source.slice(header.length)}\n}`,
    cursor: cursor - delta,
    delta,
  };
}
