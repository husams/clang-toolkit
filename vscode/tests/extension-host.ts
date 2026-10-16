import assert from "node:assert/strict";
import { realpath } from "node:fs/promises";
import * as vscode from "vscode";
import type { ActionNode } from "../src/actions.js";
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
  const helperSource =
    'let scale(x) = x * 2\nlet node = classByName("dem", "demo::Order")\nclassFields(node)';
  const helperPath = await complete(
    helperSource,
    helperSource.indexOf('"dem') + 4,
  );
  const helperFile = helperPath.items.find((item) => item.label === "demo.cpp");
  assert.equal(helperFile?.kind, vscode.CompletionItemKind.File);
  assert.ok(helperFile?.range instanceof vscode.Range);
  const helperEdit = new vscode.WorkspaceEdit();
  helperEdit.replace(
    helperPath.draft.uri,
    helperFile.range,
    String(helperFile.insertText),
  );
  await vscode.workspace.applyEdit(helperEdit);
  assert.equal(
    helperPath.draft.getText(),
    helperSource.replace('"dem"', '"demo.cpp"'),
  );
  await vscode.window.showTextDocument(helperPath.draft);
  await vscode.commands.executeCommand("ctk.runCurrentScript");
  const helperExecution = api.snapshot() as {
    errors: string[];
    results: { name: string }[];
  };
  assert.deepEqual(helperExecution.errors, []);
  assert.ok(
    helperExecution.results.some(
      (item) => item.name === "demo::Order::quantity",
    ),
  );
  const classArgument = await complete('classByName("demo.cpp", "dem');
  assert.ok(
    classArgument.items.some(
      (item) =>
        item.label === "demo::Order" &&
        item.kind === vscode.CompletionItemKind.Class,
    ),
  );
  assert.ok(
    !classArgument.items.some(
      (item) => item.kind === vscode.CompletionItemKind.File,
    ),
  );
  const classSource =
    'let node = classByName("demo.cpp", "demo::Or")\nclassFields(node)';
  const classDraft = await complete(
    classSource,
    classSource.indexOf("demo::Or") + "demo::Or".length,
  );
  const classItem = classDraft.items.find(
    (item) => item.label === "demo::Order",
  );
  assert.ok(classItem?.range instanceof vscode.Range);
  const classEdit = new vscode.WorkspaceEdit();
  classEdit.replace(
    classDraft.draft.uri,
    classItem.range,
    String(classItem.insertText),
  );
  await vscode.workspace.applyEdit(classEdit);
  assert.equal(
    classDraft.draft.getText(),
    classSource.replace('demo::Or"', 'demo::Order"'),
  );
  await vscode.window.showTextDocument(classDraft.draft);
  await vscode.commands.executeCommand("ctk.runCurrentScript");
  assert.deepEqual((api.snapshot() as { errors: string[] }).errors, []);
  assert.ok(
    (api.snapshot() as { results: { name: string }[] }).results.some(
      (r) => r.name === "demo::Order::quantity",
    ),
  );
  const selectedClass = await complete('classByName(arg.FILE, "dem');
  assert.ok(selectedClass.items.some((item) => item.label === "demo::Order"));
  const helperFolders = await complete('classByName("source');
  assert.ok(
    helperFolders.items.some(
      (item) =>
        item.label === "source dir/" &&
        item.kind === vscode.CompletionItemKind.Folder,
    ),
  );
  const userPath = await complete('let load(input) = parse input\nload("dem');
  assert.ok(userPath.items.some((item) => item.label === "demo.cpp"));
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
  const actionTarget = vscode.Uri.joinPath(folder.uri, "node-actions.cpp");
  await vscode.workspace.fs.writeFile(
    actionTarget,
    Buffer.from(
      "int adjust(int value) { return value + 1; }\nint processOrder(int quantity) { return adjust(quantity); }\nint unrelated() { return 0; }\n",
    ),
  );
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(actionTarget),
  );
  const catalog = await api.actions.catalog();
  const functions = catalog.find((a) => a.id === "find-function"),
    calls = catalog.find((a) => a.id === "find-calls");
  assert.ok(functions);
  assert.ok(calls);
  await api.actions.setAction(functions);
  const actionRun = api.actions.run(
    undefined,
    { name: "processOrder" },
    actionTarget,
  );
  await assert.rejects(api.actions.run(), /already running/);
  await actionRun;
  type ActionSnapshot = {
    results: ActionNode[];
    matches: number;
    parseCount: number;
    error: string;
    input: { id: string };
    stale: boolean;
    rendered?: { view: string; nodes: number; groups: number };
  };
  const actionState = () => api.actions.snapshot() as ActionSnapshot;
  assert.equal(actionState().matches, 1, JSON.stringify(actionState()));
  assert.equal(actionState().parseCount, 1);
  const binding = actionState().results.find((r) => r.binding === "function");
  assert.ok(binding);
  async function renderedActions(view: string) {
    const end = Date.now() + 10000;
    while (Date.now() < end) {
      const s = actionState();
      if (
        s.rendered?.view === view &&
        s.rendered.nodes === s.results.length &&
        s.rendered.groups > 0
      )
        return;
      await new Promise((done) => setTimeout(done, 50));
    }
    assert.fail(
      `Action webview did not render ${view}: ${JSON.stringify(actionState())}`,
    );
  }
  await renderedActions("bindings");
  await api.actions.receive({ type: "nodeView", view: "files" });
  await renderedActions("files");
  await api.actions.select(binding.nodeId);
  assert.equal(actionState().stale, false, JSON.stringify(actionState()));
  assert.equal(
    vscode.window.activeTextEditor?.document.uri.fsPath,
    await realpath(actionTarget.fsPath),
  );
  await api.actions.setAction(calls, true);
  assert.equal(
    actionState().input.id,
    binding.nodeId,
    "follow-up must use the selected binding handle",
  );
  await api.actions.run();
  assert.equal(actionState().matches, 1, JSON.stringify(actionState()));
  assert.equal(
    actionState().parseCount,
    1,
    "follow-up must reuse the parsed translation unit",
  );
  assert.ok(
    actionState().results.some(
      (r) => r.binding === "call" && r.excerpt.includes("adjust(quantity)"),
    ),
  );
  await renderedActions("files");
  await api.actions.receive({ type: "nodeBack" });
  assert.equal(
    actionState().results.find((r) => r.binding === "function")?.nodeId,
    binding.nodeId,
  );
  const actionFolder = vscode.Uri.joinPath(folder.uri, ".ctk", "actions");
  await vscode.workspace.fs.createDirectory(actionFolder);
  const actionUri = vscode.Uri.joinPath(
    actionFolder,
    "workspace-function.ctk-action",
  );
  const actionSource =
    '---\nname: workspace-function\ndescription: Find a named function\narguments:\n  - name: name\n    description: Function name\n    default: processOrder\n---\nmatch functionDecl(hasName(name)).bind("function") in node\n';
  await vscode.workspace.fs.writeFile(actionUri, Buffer.from(actionSource));
  const actionDoc = await vscode.workspace.openTextDocument(actionUri);
  assert.equal(actionDoc.languageId, "ctk");
  assert.ok(
    (await api.actions.catalog()).some(
      (a) => a.id === "workspace-function" && a.origin === "Workspace",
    ),
  );
  const draft = actionSource.replace(
    "functionDecl(hasName(name))",
    "functionDecl(isDef())",
  );
  const editAction = new vscode.WorkspaceEdit();
  editAction.replace(
    actionUri,
    new vscode.Range(
      actionDoc.positionAt(0),
      actionDoc.positionAt(actionDoc.getText().length),
    ),
    draft,
  );
  await vscode.workspace.applyEdit(editAction);
  const actionCompletions =
    await vscode.commands.executeCommand<vscode.CompletionList>(
      "vscode.executeCompletionItemProvider",
      actionUri,
      actionDoc.positionAt(draft.indexOf("isDef") + 5),
    );
  const actionItem = actionCompletions?.items.find(
    (item) => item.label === "isDefinition",
  );
  assert.ok(actionItem?.range instanceof vscode.Range);
  const insertAction = new vscode.WorkspaceEdit();
  insertAction.replace(
    actionUri,
    actionItem.range,
    String(actionItem.insertText),
  );
  await vscode.workspace.applyEdit(insertAction);
  assert.equal(
    actionDoc.getText(),
    draft.replace("isDef", "isDefinition"),
    "YAML action completion must preserve front matter and later CTK",
  );
  await vscode.window.showTextDocument(actionDoc);
  await vscode.commands.executeCommand("ctk.runCurrentScript");
  assert.equal(actionState().error, "");
  assert.equal(actionState().matches, 3);
  const currentFunction = actionState().results.find(
    (result) => result.binding === "function" && result.name === "processOrder",
  );
  assert.ok(currentFunction);
  await api.actions.select(currentFunction.nodeId);
  await api.actions.create(true);
  const created = vscode.window.activeTextEditor?.document;
  assert.ok(created?.uri.fsPath.endsWith("/my-action.ctk-action"));
  assert.equal(created.isDirty, false);
  assert.ok(created.getText().includes("name: my-action"));
  assert.equal(actionState().input.id, currentFunction.nodeId);
  assert.ok(
    (await api.actions.catalog()).some((action) => action.id === "my-action"),
  );
  await api.actions.run();
  assert.equal(
    actionState().matches,
    1,
    "new action must run on the selected node",
  );
  assert.equal(actionState().parseCount, 1);
  await api.actions.create();
  assert.ok(
    vscode.window.activeTextEditor?.document.uri.fsPath.endsWith(
      "/my-action-2.ctk-action",
    ),
  );
  assert.equal(created.getText().includes("name: my-action\n"), true);
  await api.actions.refresh();
  await api.actions.run();
  assert.equal(
    actionState().matches,
    3,
    "refresh must preserve the C++ target while editing the new action",
  );
  const cppDoc = await vscode.workspace.openTextDocument(actionTarget);
  const dirty = new vscode.WorkspaceEdit();
  dirty.insert(
    actionTarget,
    cppDoc.positionAt(cppDoc.getText().length),
    "// edited\n",
  );
  await vscode.workspace.applyEdit(dirty);
  assert.equal(
    actionState().stale,
    true,
    "editing C++ must invalidate retained results",
  );
  await assert.rejects(api.actions.run(), /stale/);
  await api.actions.close();
  await cppDoc.save();
  await vscode.window.showTextDocument(cppDoc);
  await vscode.window.showTextDocument(actionDoc);
  await vscode.commands.executeCommand("ctk.runCurrentScript");
  assert.equal(
    actionState().matches,
    3,
    "editor action must use the last selected C++ file without a second file picker",
  );
  assert.equal(actionState().parseCount, 1);
  await api.actions.close();
  console.log(
    "CTK_EXTENSION_HOST_PASS: symbols, console, YAML actions, both result views, retained-node follow-up, history, stale edits and completion",
  );
}
