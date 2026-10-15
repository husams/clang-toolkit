import * as vscode from "vscode";
import {
  type ConsoleResponse,
  ConsoleService,
  findPython,
  toCodePointOffset,
  toUtf16Offset,
} from "./console-service.js";

export async function registerLanguage(
  context: vscode.ExtensionContext,
): Promise<void> {
  const output = vscode.window.createOutputChannel("CTK Completion");
  context.subscriptions.push(output);
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
      context.extensionPath;
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
      const source = document.getText();
      return await (await starting).request(
        source,
        toCodePointOffset(source, document.offsetAt(position)),
        directory,
        config.get<string>("libraryDirectory", ""),
      );
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
      if (event.affectsConfiguration("ctk.pythonPath")) {
        service?.dispose();
        service = undefined;
        starting = undefined;
        warned = false;
      }
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
          return (data.items ?? []).map((entry) => {
            const kind = entry.detail.startsWith("method")
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
