import { readFile } from "node:fs/promises";
import { Client, type SemanticBinding } from "@clang-toolkit/sdk";
import {
  queries,
  type Result,
  type RunReport,
  type RunRequest,
  renderScript,
  validateParameters,
} from "./model.js";

function record(value: unknown): Record<string, unknown> | undefined {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}
function named(value: unknown, depth = 0): string | undefined {
  if (depth > 12) return undefined;
  const item = record(value);
  if (!item) return undefined;
  if (typeof item.qualifiedName === "string" && item.qualifiedName)
    return item.qualifiedName;
  for (const child of Object.values(item)) {
    const name = named(child, depth + 1);
    if (name) return name;
  }
  return undefined;
}
export function describeBinding(
  binding: SemanticBinding,
): Omit<Result, "excerpt"> | undefined {
  const location = binding.location;
  if (
    !location?.valid ||
    !location.file ||
    !Number.isInteger(Number(location.line)) ||
    Number(location.line) < 1
  )
    return undefined;
  const node = record(binding.node);
  const discriminator =
    typeof node?.node === "string"
      ? node.node
      : typeof node?.value === "string"
        ? node.value
        : (Object.keys(node ?? {}).find((key) => node?.[key] !== null) ??
          binding.value ??
          "Match");
  const kind = discriminator
    .replace(/Decl$/, "")
    .replace(/^cxx/, "")
    .replace(/^./, (c) => c.toUpperCase());
  const name = named(binding.node) || binding.symbolIdentity || kind;
  const file = location.file,
    line = Number(location.line),
    column = Number.isInteger(Number(location.column))
      ? Math.max(1, Number(location.column))
      : 1;
  return {
    id: `${file}:${line}:${column}:${name}`,
    name,
    kind,
    file,
    line,
    column,
    raw: binding,
  };
}
export async function runAnalysis(
  request: RunRequest,
  progress: (file: string, index: number) => void = () => {},
): Promise<RunReport> {
  const values = validateParameters(request.action, request.values);
  const options = {
    workingDirectory: request.directory,
    compileArguments: request.compileArguments,
    timeoutMs: request.timeoutMs,
    ...(request.configPath ? { configPath: request.configPath } : {}),
    ...(request.compilationDatabase
      ? { compilationDatabase: request.compilationDatabase }
      : {}),
  };
  const client = request.endpoint
    ? new Client(request.endpoint, options)
    : new Client(options);
  const report: RunReport = {
    results: [],
    errors: [],
    output: [],
    truncated: false,
    files: 0,
  };
  const seen = new Set<string>(),
    sources = new Map<string, string[]>();
  const add = async (binding: SemanticBinding): Promise<void> => {
    const result = describeBinding(binding);
    if (!result || seen.has(result.id)) return;
    seen.add(result.id);
    if (report.results.length >= request.maxResults) {
      report.truncated = true;
      return;
    }
    if (!sources.has(result.file)) {
      try {
        sources.set(
          result.file,
          (await readFile(result.file, "utf8")).split(/\r?\n/),
        );
      } catch {
        sources.set(result.file, []);
      }
    }
    report.results.push({
      ...result,
      excerpt: sources.get(result.file)?.[result.line - 1]?.trim() ?? "",
    });
  };
  const rows = async (value: unknown): Promise<void> => {
    if (Array.isArray(value)) {
      for (const item of value) await rows(item);
      return;
    }
    const item = record(value);
    if (!item) return;
    if (item.bindings) {
      const bindings = record(item.bindings);
      const binding =
        bindings?.symbol ?? bindings?.root ?? Object.values(bindings ?? {})[0];
      if (binding) await add(binding as SemanticBinding);
      return;
    }
    for (const child of Object.values(item)) await rows(child);
  };
  try {
    await client.ready(5000);
    for (const [index, file] of request.files.entries()) {
      progress(file, index);
      try {
        if (request.action.kind === "script") {
          const source = renderScript(
            request.action.source ?? "",
            values,
            file,
          );
          const response = await client.runScript(source, {
            file,
            maxSteps: 1000,
          });
          await rows(response.emissions);
          report.output.push(JSON.stringify(response.emissions, null, 2));
        } else {
          for (const query of queries(request.action, values, request.kinds)) {
            const matches = await client.match(query, file, {
              onRow: async (row) => {
                const binding =
                  row.bindings.symbol ??
                  row.bindings.root ??
                  Object.values(row.bindings)[0];
                if (binding) await add(binding);
              },
            });
            await matches.close();
          }
        }
        report.files += 1;
      } catch (error) {
        report.errors.push(
          `${file}: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    }
  } finally {
    await client.close();
  }
  report.results.sort(
    (a, b) =>
      a.file.localeCompare(b.file) || a.line - b.line || a.column - b.column,
  );
  return report;
}
