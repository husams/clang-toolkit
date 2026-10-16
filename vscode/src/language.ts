import { dirname } from "node:path";
import * as vscode from "vscode";
import { actionCompletionSource } from "./actions.js";
import { AutomaticClassSuggestions } from "./automatic-class-suggestions.js";
import { ClassNameService } from "./class-name-service.js";
import {
  type ConsoleResponse,
  ConsoleService,
  findPython,
  toCodePointOffset,
  toUtf16Offset,
} from "./console-service.js";
import type { RunRequest } from "./model.js";

export async function registerLanguage(
  context: vscode.ExtensionContext,
  targetFile: () => string | undefined,
): Promise<void> {
  const output = vscode.window.createOutputChannel("CTK Completion");
  context.subscriptions.push(output);
  const classes = new ClassNameService(
    vscode.Uri.joinPath(context.extensionUri, "dist/worker.js").fsPath,
  );
  const watcher = vscode.workspace.createFileSystemWatcher(
    "**/*.{c,cc,cpp,cxx,h,hh,hpp,hxx,json,yaml,yml}",
  );
  const invalidate = () => classes.invalidate();
  context.subscriptions.push(
    classes,
    watcher,
    watcher.onDidChange(invalidate),
    watcher.onDidCreate(invalidate),
    watcher.onDidDelete(invalidate),
    vscode.workspace.onDidChangeTextDocument(({ document }) => {
      if (["c", "cpp"].includes(document.languageId)) invalidate();
    }),
  );
  let service: ConsoleService | undefined;
  let starting: Promise<ConsoleService> | undefined;
  let warned = false;
  const response = async (
    document: vscode.TextDocument,
    position: vscode.Position,
  ): Promise<ConsoleResponse> => {
    if (!vscode.workspace.isTrusted) return { id: 0, items: [], functions: {} };
    const config = vscode.workspace.getConfiguration("ctk", document.uri);
    const directory =
      vscode.workspace.getWorkspaceFolder(document.uri)?.uri.fsPath ??
      vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ??
      (document.uri.scheme === "file"
        ? dirname(document.uri.fsPath)
        : process.cwd());
    if (!starting)
      starting = findPython(
        config.get<string>("pythonPath", ""),
        directory,
      ).then((python) => {
        output.appendLine(`Console autocomplete interpreter: ${python}`);
        service = new ConsoleService(
          vscode.Uri.joinPath(context.extensionUri, "console/editor_service.py")
            .fsPath,
          python,
          (message) => output.appendLine(message),
        );
        return service;
      });
    try {
      const original = document.getText();
      const cursor = toCodePointOffset(original, document.offsetAt(position));
      const action = document.uri.fsPath.endsWith(".ctk-action")
        ? actionCompletionSource(document.uri.fsPath, original, cursor)
        : undefined;
      if (document.uri.fsPath.endsWith(".ctk-action") && !action)
        return { id: 0, items: [], functions: {} };
      const data = await (await starting).request(
        action?.source ?? original,
        action?.cursor ?? cursor,
        directory,
        config.get<string>("libraryDirectory", ""),
        document.uri.scheme === "file"
          ? dirname(document.uri.fsPath)
          : directory,
        targetFile(),
      );
      if (action) {
        data.items = data.items
          ?.filter((item) => item.start + action.delta >= 0)
          .map((item) => ({ ...item, start: item.start + action.delta }));
        if (data.symbols)
          data.symbols = {
            ...data.symbols,
            start: data.symbols.start + action.delta,
          };
      }
      return data;
    } catch (error) {
      output.appendLine(String(error));
      if (!warned) {
        warned = true;
        void vscode.window.showErrorMessage(
          "CTK autocomplete needs the console's Python 3.14 environment; set ctk.pythonPath. See CTK Completion output.",
        );
      }
      return { id: 0, items: [], functions: {} };
    }
  };
  context.subscriptions.push(
    { dispose: () => service?.dispose() },
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("ctk")) invalidate();
      if (event.affectsConfiguration("ctk.pythonPath")) {
        service?.dispose();
        service = undefined;
        starting = undefined;
        warned = false;
      }
    }),
  );
  const automatic = new AutomaticClassSuggestions(
    () => {
      const editor = vscode.window.activeTextEditor;
      if (
        editor?.document.languageId !== "ctk" ||
        !vscode.window.state.focused ||
        !vscode.workspace.isTrusted ||
        !editor.selection.isEmpty ||
        !vscode.workspace
          .getConfiguration("ctk", editor.document.uri)
          .get<boolean>("automaticClassSuggestions", true)
      )
        return undefined;
      return {
        key: `${editor.document.uri.toString()}:${editor.document.version}:${editor.document.offsetAt(editor.selection.active)}`,
        value: { document: editor.document, position: editor.selection.active },
      };
    },
    async ({ document, position }) =>
      Boolean((await response(document, position)).symbols),
    () => vscode.commands.executeCommand("editor.action.triggerSuggest"),
    (error) =>
      output.appendLine(`Automatic class-name suggestions: ${String(error)}`),
  );
  context.subscriptions.push(
    automatic,
    vscode.window.onDidChangeActiveTextEditor(() => automatic.cancel()),
    vscode.workspace.onDidChangeTextDocument((event) => {
      if (
        event.document !== vscode.window.activeTextEditor?.document ||
        event.document.languageId !== "ctk"
      )
        return;
      automatic.cancel();
      if (
        event.reason ||
        !event.contentChanges.some(
          (change) =>
            change.rangeLength <= 1 &&
            change.text.length <= 128 &&
            (/^(?:[\p{L}\p{N}_:]+|["'])$/u.test(change.text) ||
              (change.text === "" && change.rangeLength === 1)),
        )
      )
        return;
      automatic.changed();
    }),
  );
  context.subscriptions.push(
    vscode.languages.registerCompletionItemProvider(
      "ctk",
      {
        async provideCompletionItems(document, position, token) {
          const source = document.getText(),
            version = document.version;
          const data = await response(document, position);
          if (token.isCancellationRequested || document.version !== version)
            return [];
          if (data.symbols) {
            const symbol = data.symbols;
            if (
              vscode.workspace.textDocuments.some(
                (doc) => doc.isDirty && ["c", "cpp"].includes(doc.languageId),
              )
            ) {
              output.appendLine(
                "Save edited C++ files before requesting class-name suggestions.",
              );
              return [];
            }
            const config = vscode.workspace.getConfiguration(
              "ctk",
              document.uri,
            );
            const directory =
              vscode.workspace.getWorkspaceFolder(document.uri)?.uri.fsPath ??
              vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ??
              dirname(symbol.file);
            const request: RunRequest = {
              action: {
                id: "class-completion",
                title: "Class names",
                description: "Classes available to classByName",
                kind: "symbols",
                parameters: [],
              },
              values: {},
              kinds: ["classes"],
              files: [symbol.file],
              directory,
              endpoint: config.get<string>("server", ""),
              configPath: config.get<string>("configPath", ""),
              compilationDatabase: config.get<string>(
                "compilationDatabase",
                "",
              ),
              compileArguments: config.get<string[]>("compileArguments", []),
              timeoutMs: config.get<number>("rpcTimeoutMs", 30000),
              maxResults: config.get<number>("maxResults", 2000),
            };
            try {
              const report = await classes.complete(request, symbol.prefix);
              if (token.isCancellationRequested || document.version !== version)
                return [];
              return new vscode.CompletionList(
                report.results.map((result) => {
                  const item = new vscode.CompletionItem(
                    result.name,
                    vscode.CompletionItemKind.Class,
                  );
                  item.range = new vscode.Range(
                    document.positionAt(toUtf16Offset(source, symbol.start)),
                    position,
                  );
                  item.insertText =
                    symbol.quote +
                    result.name
                      .replaceAll("\\", "\\\\")
                      .replaceAll(symbol.quote, `\\${symbol.quote}`) +
                    (symbol.close ? symbol.quote : "");
                  item.filterText = symbol.quote + result.name;
                  item.detail = `${vscode.workspace.asRelativePath(result.file)}:${result.line}`;
                  item.documentation =
                    new vscode.MarkdownString().appendCodeblock(
                      result.excerpt,
                      "cpp",
                    );
                  return item;
                }),
                report.truncated,
              );
            } catch (error) {
              output.appendLine(`Class-name completion: ${String(error)}`);
              return [];
            }
          }
          return (data.items ?? []).map((entry) => {
            const kind =
              entry.detail === "directory"
                ? vscode.CompletionItemKind.Folder
                : entry.detail === "file"
                  ? vscode.CompletionItemKind.File
                  : entry.detail.startsWith("method")
                    ? vscode.CompletionItemKind.Method
                    : entry.detail.includes("matcher") ||
                        entry.detail.startsWith("user defined")
                      ? vscode.CompletionItemKind.Function
                      : entry.detail.includes("keyword")
                        ? vscode.CompletionItemKind.Keyword
                        : vscode.CompletionItemKind.Property;
            const item = new vscode.CompletionItem(entry.label, kind);
            item.range = new vscode.Range(
              document.positionAt(toUtf16Offset(source, entry.start)),
              position,
            );
            item.insertText = entry.text;
            item.filterText = entry.text;
            if (entry.detail === "directory")
              item.command = {
                command: "editor.action.triggerSuggest",
                title: "Continue path completion",
              };
            item.detail = entry.detail;
            item.documentation = new vscode.MarkdownString(
              entry.documentation || entry.detail,
            );
            return item;
          });
        },
      },
      ".",
      "$",
      "(",
      ",",
      " ",
      "/",
      "\\",
      '"',
      "'",
    ),
  );
  context.subscriptions.push(
    vscode.languages.registerHoverProvider("ctk", {
      async provideHover(document, position) {
        const word = document.getWordRangeAtPosition(position);
        if (!word) return undefined;
        const data = await response(document, word.end);
        const help = data.functions?.[document.getText(word)];
        if (help)
          return new vscode.Hover(
            new vscode.MarkdownString(help.documentation),
            word,
          );
        const entry = data.items?.find(
          (item) => item.label.replace(/\($/, "") === document.getText(word),
        );
        return entry
          ? new vscode.Hover(
              new vscode.MarkdownString(
                `${entry.detail}\n\n${entry.documentation}`,
              ),
              word,
            )
          : undefined;
      },
    }),
  );
  context.subscriptions.push(
    vscode.languages.registerSignatureHelpProvider(
      "ctk",
      {
        async provideSignatureHelp(document, position, token) {
          const data = await response(document, position);
          if (token.isCancellationRequested || !data.call) return undefined;
          const help = data.functions?.[data.call.name];
          if (!help) return undefined;
          const result = new vscode.SignatureHelp();
          result.signatures = (
            help.signatures?.length ? help.signatures : [help.signature]
          ).map((label) => {
            const signature = new vscode.SignatureInformation(
              label,
              new vscode.MarkdownString(help.documentation),
            );
            signature.parameters = parametersOf(label).map(
              (parameter) => new vscode.ParameterInformation(parameter),
            );
            return signature;
          });
          result.activeSignature = 0;
          result.activeParameter = Math.min(
            data.call.parameter,
            Math.max(0, (result.signatures[0]?.parameters.length ?? 0) - 1),
          );
          return result;
        },
      },
      "(",
      ",",
    ),
  );
}
export function parametersOf(signature: string): string[] {
  const content = signature.slice(
    signature.indexOf("(") + 1,
    signature.lastIndexOf(")"),
  );
  const parts: string[] = [];
  let depth = 0,
    start = 0,
    quote = "";
  for (let index = 0; index < content.length; index++) {
    const character = content[index] ?? "";
    if (quote) {
      if (character === "\\") index++;
      else if (character === quote) quote = "";
      continue;
    }
    if (character === '"' || character === "'") quote = character;
    else if ("([<{".includes(character)) depth++;
    else if (")]>}".includes(character)) depth--;
    else if (character === "," && depth === 0) {
      parts.push(content.slice(start, index).trim());
      start = index + 1;
    }
  }
  if (content.slice(start).trim()) parts.push(content.slice(start).trim());
  return parts;
}
