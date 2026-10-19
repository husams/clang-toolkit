const SOURCE = /\.(?:c|cc|cpp|cxx)$/i;
const HEADER = /\.(?:h|hh|hpp|hxx)$/i;
const EXCLUDED = new Set([
  ".git",
  ".hg",
  ".svn",
  ".venv",
  ".cache",
  ".vscode-test",
  "build",
  "dist",
  "node_modules",
  "out",
  "target",
]);
export type ActionSourceScope = "file" | "directory" | "workspace";

export interface ActionSourceContext {
  scope: ActionSourceScope;
  workspaceRoots: readonly string[];
  target?: string;
  directoryTarget?: string;
}

export interface ActionTargetManifest {
  files: string[];
  sourceFiles: number;
  headerFallback: boolean;
}

export function isExcludedActionPath(
  path: string,
  roots: readonly string[] = [],
): boolean {
  const normalized = path.replaceAll("\\", "/").replace(/\/$/, "");
  const root = [...roots]
    .map((value) => value.replaceAll("\\", "/").replace(/\/$/, ""))
    .filter(
      (value) => normalized === value || normalized.startsWith(`${value}/`),
    )
    .sort((left, right) => right.length - left.length)[0];
  const relative = root
    ? normalized.slice(root.length).replace(/^\//, "")
    : normalized;
  return relative.split("/").some((part) => EXCLUDED.has(part));
}

/** Whether a source edit can affect an input discovered for an Action scope. */
export function isRelevantActionSource(
  path: string,
  context: ActionSourceContext,
): boolean {
  if (HEADER.test(path)) return true;
  if (!SOURCE.test(path)) return false;
  if (context.target && samePath(path, context.target)) return true;
  if (context.scope === "file") return false;
  if (context.scope === "directory") {
    const directory = context.directoryTarget;
    return Boolean(
      directory &&
        pathIsWithin(path, [directory]) &&
        !isExcludedActionPath(path, [directory]),
    );
  }
  return (
    pathIsWithin(path, context.workspaceRoots) &&
    !isExcludedActionPath(path, context.workspaceRoots)
  );
}

function samePath(left: string, right: string): boolean {
  return (
    left.replaceAll("\\", "/").replace(/\/$/, "") ===
    right.replaceAll("\\", "/").replace(/\/$/, "")
  );
}

/** Sort and deduplicate discovered files, preferring translation units to headers. */
export function selectActionTargets(
  candidates: readonly string[],
  maximum: number,
  roots: readonly string[] = [],
): ActionTargetManifest {
  const unique = [...new Set(candidates)]
    .filter((path) => !isExcludedActionPath(path, roots))
    .sort((left, right) => left.localeCompare(right));
  const sources = unique.filter((path) => SOURCE.test(path));
  const groups = roots.length
    ? roots.map((root) => unique.filter((path) => pathIsWithin(path, [root])))
    : [unique];
  const files = [
    ...new Set(
      groups.flatMap((group) => {
        const units = group.filter((path) => SOURCE.test(path));
        return units.length ? units : group.filter((path) => HEADER.test(path));
      }),
    ),
  ].sort((left, right) => left.localeCompare(right));
  if (files.length > maximum)
    throw new Error(
      `Action scope contains more than ctk.maxFiles (${maximum}) C++ files; narrow the scope or increase the limit.`,
    );
  return {
    files,
    sourceFiles: sources.length,
    headerFallback: files.some((path) => HEADER.test(path)),
  };
}

export function pathIsWithin(path: string, roots: readonly string[]): boolean {
  const normalized = path.replaceAll("\\", "/").replace(/\/$/, "");
  return roots.some((root) => {
    const candidate = root.replaceAll("\\", "/").replace(/\/$/, "");
    return normalized === candidate || normalized.startsWith(`${candidate}/`);
  });
}
