import assert from "node:assert/strict";
import * as vscode from "vscode";
import type { Prototype } from "../src/extension.js";
import { predefined, scriptAction } from "../src/model.js";
export async function run(): Promise<void> {
  const extension = vscode.extensions.getExtension<Prototype>(
    "clang-toolkit.clang-toolkit-prototype",
  );
  assert.ok(extension);
  const api = await extension.activate();
  const folder = vscode.workspace.workspaceFolders?.[0];
  assert.ok(folder);
  const target = vscode.Uri.joinPath(folder.uri, "demo.cpp");
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(target),
  );
  await vscode.commands.executeCommand("ctk.openAnalysis");
  const running = api.execute({
    action: predefined[0]!,
    values: { NAME: "Order" },
    scope: "file",
    target,
  });
  await assert.rejects(
    api.execute({ action: predefined[0]!, target }),
    /already running/,
  );
  await running;
  const snapshot = api.snapshot() as {
    results: { id: string; name: string }[];
    errors: string[];
  };
  assert.deepEqual(snapshot.errors, []);
  assert.ok(
    snapshot.results.some((r) => r.name === "demo::Order"),
    JSON.stringify(snapshot),
  );
  const deadline = Date.now() + 10000;
  while (Date.now() < deadline) {
    const rendered = (
      api.snapshot() as {
        rendered?: { action: string; matches: number; groups: number };
      }
    ).rendered;
    if (
      rendered?.action === "symbols" &&
      rendered.matches === snapshot.results.length &&
      rendered.groups === 1
    )
      break;
    await new Promise((done) => setTimeout(done, 50));
  }
  const rendered = (
    api.snapshot() as { rendered?: { matches: number; groups: number } }
  ).rendered;
  assert.equal(
    rendered?.matches,
    snapshot.results.length,
    "webview must display every native match",
  );
  assert.equal(rendered?.groups, 1, "webview must group results by file");
  await api.openResult(snapshot.results[0]!.id);
  const document = await vscode.workspace.openTextDocument({
    language: "ctk",
    content: 'emit match functionDecl(isDef).bind("symbol");',
  });
  await vscode.window.showTextDocument(document);
  const completions =
    await vscode.commands.executeCommand<vscode.CompletionList>(
      "vscode.executeCompletionItemProvider",
      document.uri,
      new vscode.Position(0, 29),
    );
  assert.ok(completions?.items.some((item) => item.label === "isDefinition"));
  const complete = async (source: string, cursor = source.length) => {
    const draft = await vscode.workspace.openTextDocument({
      language: "ctk",
      content: source,
    });
    const items = await vscode.commands.executeCommand<vscode.CompletionList>(
      "vscode.executeCompletionItemProvider",
      draft.uri,
      draft.positionAt(cursor),
    );
    return { draft, items: items?.items ?? [] };
  };
  const members = await complete(
    'let x = match functionDecl().bind("symbol");\nx.',
  );
  assert.ok(
    members.items.some(
      (item) => item.label === "one" && item.insertText === "one(",
    ),
  );
  assert.ok(members.items.some((item) => item.label === "symbol"));
  const pathSource =
    'let scale(x) = x * 2\nlet tree = parse "dem"\nprint scale(21)';
  const path = await complete(pathSource, pathSource.indexOf("dem") + 3);
  const file = path.items.find((item) => item.label === "demo.cpp");
  assert.equal(file?.kind, vscode.CompletionItemKind.File);
  assert.ok(file?.range instanceof vscode.Range);
  const pathEdit = new vscode.WorkspaceEdit();
  pathEdit.replace(path.draft.uri, file.range, String(file.insertText));
  await vscode.workspace.applyEdit(pathEdit);
  assert.equal(path.draft.getText(), pathSource.replace('"dem"', '"demo.cpp"'));
  const nested = vscode.Uri.joinPath(folder.uri, "source dir");
  await vscode.workspace.fs.createDirectory(nested);
  await vscode.workspace.fs.writeFile(
    vscode.Uri.joinPath(nested, "nested file.cpp"),
    Buffer.from("int nested;"),
  );
  const folders = await complete('parse "source');
  const directory = folders.items.find((item) => item.label === "source dir/");
  assert.equal(directory?.kind, vscode.CompletionItemKind.Folder);
  assert.equal(directory?.command?.command, "editor.action.triggerSuggest");
  const children = await complete('parse "source dir/"');
  assert.ok(children.items.some((item) => item.label === "nested file.cpp"));
  await vscode.workspace.fs.writeFile(
    vscode.Uri.joinPath(nested, "helper.ctk"),
    Buffer.from("let helper() = 1"),
  );
  const importUri = vscode.Uri.joinPath(nested, "run.ctk");
  await vscode.workspace.fs.writeFile(importUri, Buffer.from('import "hel"'));
  const imported = await vscode.workspace.openTextDocument(importUri);
  const importItems =
    await vscode.commands.executeCommand<vscode.CompletionList>(
      "vscode.executeCompletionItemProvider",
      importUri,
      imported.positionAt(imported.getText().indexOf("hel") + 3),
    );
  assert.ok(importItems?.items.some((item) => item.label === "helper.ctk"));
  assert.equal(
    vscode.workspace
      .getConfiguration("editor", { languageId: "ctk" })
      .get<{ strings: string }>("quickSuggestions")?.strings,
    "on",
  );
  const source = 'emit match functionDecl(\n  isDef()\n).bind("symbol");';
  const earlier = await complete(source, source.indexOf("isDef") + 5);
  const definition = earlier.items.find(
    (item) => item.label === "isDefinition",
  );
  assert.ok(definition?.range instanceof vscode.Range);
  const edit = new vscode.WorkspaceEdit();
  edit.replace(
    earlier.draft.uri,
    definition.range,
    String(definition.insertText),
  );
  await vscode.workspace.applyEdit(edit);
  assert.equal(
    earlier.draft.getText(),
    source.replace("isDef", "isDefinition"),
  );
  const user = await complete(
    "let scale(value, factor = 2) = { value * factor }\nsca",
  );
  assert.ok(
    user.items.some(
      (item) => item.label === "scale" && item.detail?.includes("factor = 2"),
    ),
  );
  const helper = await complete("classByN");
  assert.ok(helper.items.some((item) => item.label === "classByName"));
  const signatureDoc = await vscode.workspace.openTextDocument({
    language: "ctk",
    content:
      'let scale(value, factor = 2) = { value * factor }\nscale(other("a,b"), ',
  });
  const signatures = await vscode.commands.executeCommand<vscode.SignatureHelp>(
    "vscode.executeSignatureHelpProvider",
    signatureDoc.uri,
    signatureDoc.positionAt(signatureDoc.getText().length),
  );
  assert.equal(signatures?.signatures[0]?.label, "scale(value, factor = 2)");
  assert.equal(signatures.activeParameter, 1);
  assert.equal(
    vscode.workspace
      .getConfiguration("editor", { languageId: "ctk" })
      .get<{ other: string }>("quickSuggestions")?.other,
    "on",
  );
  assert.ok(
    (
      await vscode.commands.executeCommand<vscode.Hover[]>(
        "vscode.executeHoverProvider",
        document.uri,
        new vscode.Position(0, 12),
      )
    )?.length,
  );
  await api.execute({
    action: predefined.find((a) => a.id === "members")!,
    values: { CLASS_NAME: "demo::Order", MEMBER_KIND: "Fields" },
    target,
  });
  assert.equal((api.snapshot() as { results: unknown[] }).results.length, 1);
  await api.execute({
    action: {
      ...scriptAction(
        "custom.ctk",
        'match cxxRecordDecl(isExpansionInMainFile(), isDefinition(), unless(isImplicit())).bind("symbol");',
      ),
      script: undefined,
    },
    target,
  });
  assert.ok(
    (api.snapshot() as { results: { name: string }[] }).results.some(
      (r) => r.name === "demo::Order",
    ),
  );
  const unsaved = await vscode.workspace.openTextDocument({
    language: "ctk",
    content:
      'let scale(value, factor = 2) = { value * factor }\nprint scale(21)\nlet node = classByName(arg.FILE, "demo::Order")\nclassFields(node)',
  });
  await vscode.window.showTextDocument(unsaved);
  await vscode.commands.executeCommand("ctk.runCurrentScript");
  assert.equal(
    unsaved.isUntitled,
    true,
    "unsaved scripts must run without a save dialog",
  );
  const executed = api.snapshot() as {
    errors: string[];
    output: string[];
    results: { name: string }[];
  };
  assert.deepEqual(executed.errors, []);
  assert.ok(executed.output.join("\n").includes("42"));
  assert.ok(
    executed.results.some((item) => item.name === "demo::Order::quantity"),
  );
  console.log(
    "CTK_EXTENSION_HOST_PASS: unified native analyses, scripts, completion, hover and source/details",
  );
}
