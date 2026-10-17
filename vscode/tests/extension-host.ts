import assert from "node:assert/strict";
import { readFile, realpath } from "node:fs/promises";
import * as vscode from "vscode";
import {
  type ActionNode,
  type NodeAction,
  parseNodeAction,
} from "../src/actions.js";
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
  const astState = () => api.details.snapshot();
  async function renderedAst(kind: string) {
    const end = Date.now() + 10000;
    while (Date.now() < end) {
      const state = astState();
      const rendered = state.rendered;
      if (
        !state.running &&
        rendered?.type === "rendered" &&
        rendered.kind === kind &&
        rendered.children.length === (state.children?.length ?? 0)
      )
        return rendered;
      await new Promise((done) => setTimeout(done, 50));
    }
    assert.fail(
      `AST inspector did not render ${kind}: ${JSON.stringify(astState())}`,
    );
  }
  assert.equal(astState().error, "", JSON.stringify(astState()));
  assert.equal(astState().node?.kind, "CXXRecordDecl");
  const classInspector = await renderedAst("CXXRecordDecl");
  assert.doesNotMatch(
    classInspector.text,
    /FIELD_STATE|BINDING_MATCH_SCOPE|supportedScopes|symbolIdentity|availability|Semantic fields/,
  );
  const symbolCatalog = await api.actions.catalog();
  const symbolFunctions = symbolCatalog.find(
    (action) => action.id === "find-function",
  );
  const symbolCalls = symbolCatalog.find(
    (action) => action.id === "find-calls",
  );
  assert.ok(symbolFunctions && symbolCalls);
  const method = astState().children?.find((child) =>
    child.name.includes("valid"),
  );
  assert.ok(method, JSON.stringify(astState()));
  await api.details.receive({ type: "child", id: method.id });
  const methodBody = astState().children?.find(
    (child) => child.kind === "CompoundStmt",
  );
  assert.ok(methodBody, JSON.stringify(astState()));
  await api.details.receive({ type: "child", id: methodBody.id });
  await renderedAst("CompoundStmt");
  const symbolTarget = await api.details.actionTarget();
  await api.actions.setAction(symbolFunctions, true, symbolTarget);
  const symbolState = () =>
    api.actions.snapshot() as {
      input: { id: string; label: string };
      matches: number;
      parseCount: number;
    };
  assert.equal(symbolState().input.id, methodBody.id);
  await api.actions.run();
  assert.equal(
    symbolState().input.label,
    "CompoundStmt",
    "the input label must remain specific after execution",
  );
  assert.equal(
    symbolState().parseCount,
    1,
    "search child action must retain its inspection context",
  );
  assert.equal(
    symbolState().matches,
    0,
    "a method body must not run the action on the whole file",
  );
  await api.actions.setAction(
    symbolCalls,
    true,
    await api.details.actionTarget(),
  );
  await api.actions.run();
  assert.equal(symbolState().input.id, methodBody.id);
  assert.equal(
    symbolState().parseCount,
    1,
    "repeated inspector actions must keep the same worker",
  );
  await api.actions.receive({ type: "nodeRoot" });
  await api.actions.setAction(symbolFunctions);
  await api.actions.run();
  assert.ok(
    symbolState().matches > 0,
    "File root must use the parsed-file root after search transfer",
  );
  await api.actions.close();
  await assert.rejects(symbolTarget.activate(), /expired|closed|unavailable/i);
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
    action: NodeAction;
    values: Record<string, string>;
    invalidAction: boolean;
    results: ActionNode[];
    matchFiles: {
      file: string;
      matches: { id: string; bindings: ActionNode[] }[];
    }[];
    matches: number;
    parseCount: number;
    error: string;
    input: { id: string; label: string };
    stale: boolean;
    rendered?: {
      nodes: number;
      groups: number;
      rows: {
        id: string;
        file: string;
        expanded: boolean;
        bindings: string[];
        nodeIds: string[];
      }[];
      action?: string;
      arguments?: string[];
      values?: Record<string, string>;
      canRun?: boolean;
    };
  };
  const actionState = () => api.actions.snapshot() as ActionSnapshot;
  assert.equal(actionState().matches, 1, JSON.stringify(actionState()));
  assert.equal(actionState().parseCount, 1);
  const binding = actionState().results.find((r) => r.binding === "function");
  assert.ok(binding);
  async function renderedActions() {
    const end = Date.now() + 10000;
    while (Date.now() < end) {
      const s = actionState();
      if (
        s.rendered &&
        s.rendered.nodes ===
          s.matchFiles.flatMap((file) =>
            file.matches.flatMap((row) => row.bindings),
          ).length &&
        s.rendered.groups > 0 &&
        s.rendered.rows.length === s.matches &&
        s.rendered.rows.every(
          (row) =>
            JSON.stringify(row.nodeIds) ===
            JSON.stringify(
              s.matchFiles
                .flatMap((file) => file.matches)
                .find((match) => match.id === row.id)
                ?.bindings.map((node) => node.nodeId),
            ),
        )
      )
        return s.rendered;
      await new Promise((done) => setTimeout(done, 50));
    }
    assert.fail(
      `Action webview did not preserve match rows: ${JSON.stringify(actionState())}`,
    );
  }
  await renderedActions();
  await api.actions.select(binding.nodeId);
  assert.equal(astState().error, "", JSON.stringify(astState()));
  const rootAst = await renderedAst("FunctionDecl");
  assert.ok(rootAst.properties.includes("Return type"));
  const rootAstId = astState().node?.id;
  const body = astState().children?.find(
    (child) => child.kind === "CompoundStmt",
  );
  assert.ok(body, JSON.stringify(astState()));
  await api.details.receive({ type: "child", id: body.id });
  await renderedAst("CompoundStmt");
  const returned = astState().children?.find(
    (child) => child.kind === "ReturnStmt",
  );
  assert.ok(returned);
  await api.details.receive({ type: "child", id: returned.id });
  await renderedAst("ReturnStmt");
  const callExpression = astState().children?.find(
    (child) => child.kind === "CallExpr",
  );
  assert.ok(callExpression);
  await api.details.receive({ type: "child", id: callExpression.id });
  const callInspector = await renderedAst("CallExpr");
  assert.ok(callInspector.properties.includes("Callee"));
  assert.ok(astState().canRunAction);
  assert.match(callInspector.text, /Run action on this node/);
  assert.doesNotMatch(
    callInspector.text,
    /FIELD_STATE|BINDING_MATCH_SCOPE|supportedScopes|symbolIdentity|availability|Semantic fields/,
  );
  await api.details.receive({ type: "source" });
  assert.equal(vscode.window.activeTextEditor?.selection.start.line, 1);
  await api.details.receive({ type: "back" });
  await renderedAst("ReturnStmt");
  await api.details.receive({ type: "root" });
  await renderedAst("FunctionDecl");
  assert.equal(
    astState().node?.id,
    rootAstId,
    "Back must restore the exact retained AST selection",
  );
  assert.equal(
    actionState().parseCount,
    1,
    "child inspection must not reparse the action file",
  );
  assert.equal(actionState().stale, false, JSON.stringify(actionState()));
  assert.equal(
    vscode.window.activeTextEditor?.document.uri.fsPath,
    await realpath(actionTarget.fsPath),
  );
  await api.details.receive({ type: "child", id: body.id });
  await api.details.receive({ type: "child", id: returned.id });
  await api.details.receive({ type: "child", id: callExpression.id });
  const inspectedTarget = await api.details.actionTarget();
  await api.actions.setAction(calls, true, inspectedTarget);
  assert.equal(
    actionState().input.id,
    callExpression.id,
    "inspector follow-up must use the displayed child, not its original binding",
  );
  await api.actions.run();
  assert.equal(actionState().matches, 1, JSON.stringify(actionState()));
  assert.equal(actionState().input.label, "CallExpr: adjust");
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
  await renderedActions();
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
  const liveActionDoc = vscode.window.activeTextEditor?.document;
  assert.ok(liveActionDoc?.uri.fsPath.endsWith("/my-action-2.ctk-action"));
  const editMetadata = async (source: string) => {
    const edit = new vscode.WorkspaceEdit();
    edit.replace(
      liveActionDoc.uri,
      new vscode.Range(
        liveActionDoc.positionAt(0),
        liveActionDoc.positionAt(liveActionDoc.getText().length),
      ),
      source,
    );
    assert.equal(await vscode.workspace.applyEdit(edit), true);
  };
  const liveSource = (argumentsYaml: string) =>
    `---\nname: live-functions\ndescription: Find a named function\narguments:\n${argumentsYaml}\n---\nmatch functionDecl(hasName(name)).bind("function") in node\n`;
  const namedArgument =
    "  - name: name\n    description: Function name\n    default: processOrder";
  await editMetadata(liveSource(namedArgument));
  assert.equal(liveActionDoc.isDirty, true);
  assert.equal(
    actionState().action.id,
    "live-functions",
    "unsaved metadata must update the picker",
  );
  assert.deepEqual(actionState().values, { name: "processOrder" });
  const renderedMetadata = async (
    names: string[],
    values: Record<string, string>,
    canRun = true,
  ) => {
    const end = Date.now() + 10000;
    while (Date.now() < end) {
      const rendered = actionState().rendered;
      if (
        rendered?.action?.startsWith("Live functions") &&
        JSON.stringify(rendered.arguments) === JSON.stringify(names) &&
        JSON.stringify(rendered.values) === JSON.stringify(values) &&
        rendered.canRun === canRun
      )
        return;
      await new Promise((done) => setTimeout(done, 50));
    }
    assert.fail(
      `Live action metadata was not rendered: ${JSON.stringify(actionState())}`,
    );
  };
  await renderedMetadata(["name"], { name: "processOrder" });
  await api.actions.receive({
    type: "nodeArguments",
    revision: actionState().action.revision,
    values: { name: "adjust" },
  });
  await editMetadata("---\nname: live-functions\narguments: [\n---\n0");
  assert.equal(actionState().invalidAction, true);
  await renderedMetadata(["name"], { name: "adjust" }, false);
  await editMetadata(
    liveSource(
      `${namedArgument.replace("processOrder", "unrelated")}\n  - name: limit\n    description: Result limit\n    type: number\n    default: 1`,
    ),
  );
  assert.equal(actionState().invalidAction, false);
  assert.deepEqual(actionState().values, { name: "adjust", limit: "1" });
  await renderedMetadata(["name", "limit"], { name: "adjust", limit: "1" });
  assert.ok(
    (await api.actions.catalog()).some(
      (action) => action.id === "live-functions",
    ),
  );
  assert.ok(
    !(await api.actions.catalog()).some(
      (action) => action.id === "my-action-2",
    ),
  );
  await api.actions.run();
  assert.equal(actionState().matches, 1);
  assert.equal(actionState().parseCount, 1);
  await editMetadata(
    liveSource(namedArgument.replace("processOrder", "unrelated")),
  );
  assert.deepEqual(
    actionState().action.arguments.map((argument) => argument.name),
    ["name"],
  );
  await renderedMetadata(["name"], { name: "adjust" });
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
  const completionTarget = vscode.Uri.joinPath(
    folder.uri,
    "argument-target.cpp",
  );
  await vscode.workspace.fs.writeFile(
    completionTarget,
    Buffer.from(
      "namespace demo { struct Order { int quantity; }; struct Other {}; }\n",
    ),
  );
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(completionTarget),
  );
  const completionAction = vscode.Uri.joinPath(
    actionFolder,
    "argument-completion.ctk-action",
  );
  const marker = vscode.Uri.joinPath(folder.uri, "completion-ran.json");
  await vscode.workspace.fs.writeFile(
    completionAction,
    Buffer.from(
      `---\nname: argument-completion\ndescription: Inspect class fields\narguments:\n  - name: className\n    description: Class name\n  - name: cppFile\n    description: C++ file\n    default: ""\n---\nlet tree = if cppFile == "" then node else { parse cppFile }\nlet target = classByName(tree, className)\nsave "executed" to ${JSON.stringify(marker.fsPath)}\nmatch fieldDecl().bind("field") in target\n`,
    ),
  );
  const completionDoc =
    await vscode.workspace.openTextDocument(completionAction);
  await vscode.window.showTextDocument(completionDoc);
  await api.actions.current(completionDoc);
  assert.equal(actionState().parseCount, 0);
  const classChoices = await api.actions.completeArgument(
    "className",
    "demo::Or",
  );
  assert.ok(
    classChoices.some(
      (item) => item.kind === "class" && item.text === "demo::Order",
    ),
    JSON.stringify(classChoices),
  );
  const pathChoices = await api.actions.completeArgument(
    "cppFile",
    "argument-",
  );
  assert.ok(
    pathChoices.some(
      (item) => item.kind === "file" && item.text === "argument-target.cpp",
    ),
  );
  const folderChoices = await api.actions.completeArgument(
    "cppFile",
    "source ",
  );
  assert.ok(
    folderChoices.some(
      (item) => item.kind === "folder" && item.text === "source dir/",
    ),
  );
  assert.equal(
    actionState().parseCount,
    0,
    "autocomplete must not execute the action or create its retained context",
  );
  await assert.rejects(Promise.resolve(vscode.workspace.fs.stat(marker)));
  await api.actions.run(undefined, { className: "demo::Order", cppFile: "" });
  assert.equal(actionState().matches, 1);
  assert.equal(actionState().parseCount, 1);
  await vscode.workspace.fs.stat(marker);
  await api.actions.close();

  // A callee declared in a header belongs to each caller's match, not a
  // separate header group or a merged list of all callees.
  const relatedHeader = vscode.Uri.joinPath(folder.uri, "related-target.hpp");
  const relatedSource = vscode.Uri.joinPath(folder.uri, "related-callers.cpp");
  await vscode.workspace.fs.writeFile(
    relatedHeader,
    Buffer.from("inline int sharedTarget(int value) { return value + 1; }\n"),
  );
  await vscode.workspace.fs.writeFile(
    relatedSource,
    Buffer.from(
      '#include "related-target.hpp"\nint firstCaller() { return sharedTarget(1); }\nint secondCaller() { return sharedTarget(2); }\n',
    ),
  );
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(relatedSource),
  );
  const relatedActionUri = vscode.Uri.joinPath(
    actionFolder,
    "related.ctk-action",
  );
  const relatedActionSource = await readFile(
    vscode.Uri.joinPath(
      extension.extensionUri,
      "examples",
      "caller-callee.ctk-action",
    ).fsPath,
    "utf8",
  );
  await vscode.workspace.fs.writeFile(
    relatedActionUri,
    Buffer.from(relatedActionSource),
  );
  const relatedAction = parseNodeAction(
    relatedActionUri.fsPath,
    relatedActionSource,
  );
  await api.actions.setAction(relatedAction);
  await api.actions.run(undefined, {}, relatedSource);
  assert.equal(actionState().matches, 2, JSON.stringify(actionState()));
  assert.equal(actionState().parseCount, 1);
  const relatedRows = await renderedActions();
  assert.equal(
    relatedRows.nodes,
    4,
    "two calls must display exactly one caller and one callee each",
  );
  assert.equal(
    actionState().results.filter((node) => node.binding === "root").length,
    2,
    "automatic root handles remain retained even when their aliases are hidden",
  );
  assert.equal(
    relatedRows.groups,
    1,
    "header callees must stay with the source-file matches",
  );
  const sourcePath = await realpath(relatedSource.fsPath);
  const headerPath = await realpath(relatedHeader.fsPath);
  for (const row of relatedRows.rows) {
    assert.equal(row.file, sourcePath);
    assert.equal(
      row.expanded,
      false,
      "each match must start collapsed rather than showing a long binding list",
    );
    assert.deepEqual([...row.bindings].sort(), ["callee", "caller"]);
  }
  assert.deepEqual(
    relatedRows.rows.map((row) => {
      const nodes = actionState().results.filter(
        (node) => node.matchId === row.id,
      );
      return [
        nodes.find((node) => node.binding === "caller")?.name,
        nodes.find((node) => node.binding === "callee")?.name,
      ];
    }),
    [
      ["firstCaller", "sharedTarget"],
      ["secondCaller", "sharedTarget"],
    ],
  );
  const relatedCallee = actionState().results.find(
    (node) => node.binding === "callee",
  );
  assert.ok(relatedCallee);
  assert.equal(relatedCallee.file, headerPath);
  await api.actions.select(relatedCallee.nodeId);
  assert.equal(
    vscode.window.activeTextEditor?.document.uri.fsPath,
    headerPath,
    "a cross-file binding must still open its own source",
  );
  await api.actions.setAction(functions, true);
  assert.equal(actionState().input.id, relatedCallee.nodeId);
  await api.actions.run(undefined, { name: "sharedTarget" });
  assert.equal(actionState().matches, 1, JSON.stringify(actionState()));
  assert.equal(
    actionState().parseCount,
    1,
    "cross-file follow-up must reuse the selected node",
  );
  await renderedActions();
  await api.actions.receive({ type: "nodeBack" });
  assert.deepEqual(
    (await renderedActions()).rows,
    relatedRows.rows,
    "Back must restore the complete related matches",
  );
  await api.actions.close();
  console.log(
    "CTK_EXTENSION_HOST_PASS: symbols, console, YAML actions, file/match/binding outline, cross-file related matches, retained-node follow-up, history, stale edits and completion",
  );
}
