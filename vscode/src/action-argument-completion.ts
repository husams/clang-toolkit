import { readdir, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";
import type { ActionSettings } from "./action-service.js";
import type { NodeAction } from "./actions.js";
import { ClassNameService } from "./class-name-service.js";
import { ConsoleService } from "./console-service.js";

export interface ArgumentSuggestion {
  label: string;
  text: string;
  kind: "file" | "folder" | "class";
  detail: string;
}
export interface ArgumentCompletionContext extends ActionSettings {
  file: string | undefined;
  cppDirty: boolean;
  maximum: number;
}

/** Options contain literal strings, so filenames need no CTK quoting. */
export async function pathArgumentSuggestions(
  value: string,
  directory: string,
  foldersOnly = false,
): Promise<ArgumentSuggestion[]> {
  if (value.includes("\0")) return [];
  if (value === "~")
    return [{ label: "~/", text: "~/", kind: "folder", detail: "Home folder" }];
  const slash = Math.max(
    value.lastIndexOf("/"),
    sep === "\\" ? value.lastIndexOf("\\") : -1,
  );
  const parent = value.slice(0, slash + 1),
    prefix = value.slice(slash + 1);
  const expanded = parent.startsWith("~/")
    ? resolve(homedir(), parent.slice(2))
    : parent;
  const folder = isAbsolute(expanded)
    ? expanded
    : resolve(directory, expanded || ".");
  try {
    const entries = (await readdir(folder, { withFileTypes: true }))
      .filter((entry) => entry.name.startsWith(prefix))
      .sort((a, b) => a.name.localeCompare(b.name));
    const items: ArgumentSuggestion[] = [];
    for (const entry of entries) {
      let isDirectory = entry.isDirectory(),
        isFile = entry.isFile();
      if (entry.isSymbolicLink()) {
        try {
          const info = await stat(resolve(folder, entry.name));
          isDirectory = info.isDirectory();
          isFile = info.isFile();
        } catch {
          continue;
        }
      }
      if (!isDirectory && (foldersOnly || !isFile)) continue;
      const text = parent + entry.name + (isDirectory ? "/" : "");
      items.push({
        label: entry.name + (isDirectory ? "/" : ""),
        text,
        kind: isDirectory ? "folder" : "file",
        detail: isDirectory ? "Folder" : "File",
      });
      if (items.length === 100) break;
    }
    return items;
  } catch {
    return [];
  }
}

export class ActionArgumentCompletion {
  private readonly classes: ClassNameService;
  private readonly console: ConsoleService;
  private readonly roles = new Map<
    string,
    {
      expires: number;
      value: Promise<Record<string, "path" | "class">>;
    }
  >();
  constructor(
    worker: string,
    script: string,
    python: string,
    log: (text: string) => void,
  ) {
    this.classes = new ClassNameService(worker);
    this.console = new ConsoleService(script, python, log);
  }
  async complete(
    action: NodeAction,
    name: string,
    value: string,
    cursor: number,
    context: ArgumentCompletionContext,
  ): Promise<ArgumentSuggestion[]> {
    const argument = action.arguments.find((item) => item.name === name);
    if (argument?.type !== "string") return [];
    const prefix = value.slice(0, cursor);
    let kind = argument.completion;
    if (!kind) {
      const key = JSON.stringify([
        action.revision,
        context.directory,
        context.libraryDirectory,
      ]);
      let cached = this.roles.get(key);
      if (!cached || cached.expires <= Date.now()) {
        if (this.roles.size >= 16)
          this.roles.delete(this.roles.keys().next().value ?? "");
        cached = {
          expires: Date.now() + 30000,
          value: this.console
            .request(
              action.generated,
              [...action.generated].length,
              context.directory,
              context.libraryDirectory ?? "",
              dirname(action.path),
              context.file,
              action.callable,
            )
            .then((response) => response.parameterRoles ?? {}),
        };
        this.roles.set(key, cached);
      }
      try {
        kind = (await cached.value)[name];
      } catch (error) {
        this.roles.delete(key);
        throw error;
      }
    }
    if (kind === "path" || kind === "file" || kind === "folder")
      return pathArgumentSuggestions(
        prefix,
        context.directory,
        kind === "folder",
      );
    if (kind !== "class") return [];
    if (!context.file)
      throw new Error("Open a C++ file for class suggestions.");
    if (context.cppDirty)
      throw new Error("Save C++ edits for current class suggestions.");
    const report = await this.classes.complete(
      {
        ...context,
        action: {
          id: "class-completion",
          title: "Class names",
          description: "Classes for action arguments",
          kind: "symbols",
          parameters: [],
        },
        files: [context.file],
        values: {},
        kinds: ["classes"],
        maxResults: context.maximum,
      },
      prefix,
    );
    return report.results.slice(0, 100).map((result) => ({
      label: result.name,
      text: result.name,
      kind: "class",
      detail: `${relative(context.directory, result.file)}:${result.line}`,
    }));
  }
  invalidate(): void {
    this.roles.clear();
    this.classes.invalidate();
  }
  dispose(): void {
    this.console.dispose();
    this.classes.dispose();
    this.roles.clear();
  }
}
