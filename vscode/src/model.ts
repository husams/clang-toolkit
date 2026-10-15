import { z } from "zod";

export const parameterSchema = z
  .object({
    name: z
      .string()
      .regex(/^[A-Z][A-Z0-9_]*$/)
      .refine((name) => name !== "FILE", "FILE is supplied by the target"),
    label: z.string().min(1),
    kind: z.enum(["text", "choice", "file", "folder"]).default("text"),
    required: z.boolean().default(true),
    default: z.string().optional(),
    choices: z.array(z.string().min(1)).min(1).optional(),
  })
  .refine(
    (p) => p.kind !== "choice" || p.choices !== undefined,
    "Choice parameters need choices",
  );
export type Parameter = z.infer<typeof parameterSchema>;
export interface Action {
  id: string;
  title: string;
  description: string;
  kind: "symbols" | "members" | "script";
  parameters: Parameter[];
  script?: string | undefined;
  source?: string | undefined;
  kinds?: string[] | undefined;
}
const text = (name: string, label: string, required = true): Parameter => ({
  name,
  label,
  required,
  kind: "text",
});
export const predefined: Action[] = [
  {
    id: "symbols",
    title: "Find symbols",
    description: "Search named C++ declarations",
    kind: "symbols",
    parameters: [text("NAME", "Name", false)],
    kinds: ["variables", "classes", "functions"],
  },
  ...["functions", "classes", "variables"].map(
    (kind): Action => ({
      id: kind,
      title: `Find ${kind}`,
      description: `Find symbols filtered to ${kind}`,
      kind: "symbols",
      parameters: [text("NAME", "Name", false)],
      kinds: [kind],
    }),
  ),
  {
    id: "members",
    title: "Find class members",
    description: "Fields and methods belonging to a class",
    kind: "members",
    parameters: [
      text("CLASS_NAME", "Class name"),
      {
        name: "MEMBER_KIND",
        label: "Member kind",
        kind: "choice",
        required: true,
        default: "All",
        choices: ["All", "Fields", "Methods"],
      },
    ],
  },
];
const metadataSchema = z.object({
  title: z.string().min(1).optional(),
  description: z.string().optional(),
  parameters: z.array(parameterSchema).default([]),
});
export function scriptAction(path: string, source: string): Action {
  const header = source
    .split(/\r?\n/)
    .find((line) => line.startsWith("// @ctk "));
  const metadata = metadataSchema.parse(
    header ? JSON.parse(header.slice(8)) : {},
  );
  if (
    new Set(metadata.parameters.map((p) => p.name)).size !==
    metadata.parameters.length
  )
    throw new Error("Script parameter names must be unique");
  return {
    id: `script:${path}`,
    title: metadata.title ?? path.split(/[\\/]/).at(-1) ?? path,
    description: metadata.description ?? "Console CTK script",
    kind: "script",
    parameters: metadata.parameters,
    script: path,
    source,
  };
}
export function validateParameters(
  action: Action,
  values: Record<string, string>,
): Record<string, string> {
  const resolved = { ...values };
  for (const p of action.parameters) {
    const value = values[p.name] ?? p.default ?? "";
    if (p.required && !value.trim()) throw new Error(`${p.label} is required`);
    if (p.kind === "choice" && value && !p.choices?.includes(value))
      throw new Error(`Invalid ${p.label}`);
    resolved[p.name] = value;
  }
  return resolved;
}
export function renderScript(
  source: string,
  values: Record<string, string>,
  file: string,
): string {
  return source.replace(
    /\/\/[^\n]*|\/\*[\s\S]*?\*\/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\$\{([A-Z][A-Z0-9_]*)\}/g,
    (_whole: string, name: string) => {
      if (!name) return _whole;
      const value = name === "FILE" ? file : values[name];
      if (value === undefined)
        throw new Error(`Missing script parameter ${name}`);
      return `arg.${name}`;
    },
  );
}
const quoted = (text: string): string => JSON.stringify(text);
export function queries(
  action: Action,
  values: Record<string, string>,
  kinds: string[],
  includeHeaders = false,
): string[] {
  values = validateParameters(action, values);
  const root = `${includeHeaders ? "" : "isExpansionInMainFile(), "}unless(isImplicit())`;
  if (action.kind === "members") {
    const record = `cxxRecordDecl(hasName(${quoted(values.CLASS_NAME ?? "")}))`;
    const selected = values.MEMBER_KIND ?? "All";
    return [
      ...(selected !== "Methods"
        ? [`fieldDecl(${root}, hasParent(${record})).bind("symbol")`]
        : []),
      ...(selected !== "Fields"
        ? [`cxxMethodDecl(${root}, ofClass(${record})).bind("symbol")`]
        : []),
    ];
  }
  const name = values.NAME ?? "";
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const filter = name ? `, matchesName(${quoted(escaped)})` : "";
  if (!kinds.length) throw new Error("Choose at least one symbol kind");
  return [
    ...(kinds.includes("variables")
      ? [
          `varDecl(${root}, unless(parmVarDecl())${filter}).bind("symbol")`,
          `fieldDecl(${root}${filter}).bind("symbol")`,
        ]
      : []),
    ...(kinds.includes("classes")
      ? [`cxxRecordDecl(${root}, isDefinition()${filter}).bind("symbol")`]
      : []),
    ...(kinds.includes("functions")
      ? [`functionDecl(${root}${filter}).bind("symbol")`]
      : []),
  ];
}
export const requestSchema = z.object({
  action: z.object({
    id: z.string(),
    title: z.string(),
    description: z.string(),
    kind: z.enum(["symbols", "members", "script"]),
    parameters: z.array(parameterSchema),
    script: z.string().optional(),
    source: z
      .string()
      .max(1024 * 1024)
      .optional(),
    kinds: z.array(z.string()).optional(),
  }),
  files: z.array(z.string().min(1)),
  values: z.record(z.string(), z.string()),
  kinds: z.array(z.enum(["variables", "classes", "functions"])),
  directory: z.string().min(1),
  endpoint: z.string().optional(),
  configPath: z.string().optional(),
  libraryDirectory: z.string().optional(),
  includeHeaders: z.boolean().optional(),
  compilationDatabase: z.string().optional(),
  compileArguments: z.array(z.string()),
  timeoutMs: z.number().int().min(1000),
  maxResults: z.number().int().min(1).max(50000),
});
export type RunRequest = z.infer<typeof requestSchema>;
export interface Result {
  id: string;
  name: string;
  kind: string;
  file: string;
  line: number;
  column: number;
  excerpt: string;
  raw: unknown;
}
export interface RunReport {
  results: Result[];
  errors: string[];
  output: string[];
  truncated: boolean;
  files: number;
}
export const reportSchema = z.object({
  results: z.array(
    z.object({
      id: z.string(),
      name: z.string(),
      kind: z.string(),
      file: z.string(),
      line: z.number().int().positive(),
      column: z.number().int().positive(),
      excerpt: z.string(),
      raw: z.unknown(),
    }),
  ),
  errors: z.array(z.string()),
  output: z.array(z.string()),
  truncated: z.boolean(),
  files: z.number().int().nonnegative(),
});
