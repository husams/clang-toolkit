import assert from "node:assert/strict";
import { readFile, realpath } from "node:fs/promises";
import * as vscode from "vscode";
import {
  type ActionNode,
  type NodeAction,
  type NodeActionTarget,
  parseNodeAction,
} from "../src/actions.js";
import type { Prototype } from "../src/extension.js";
import { predefined, scriptAction } from "../src/model.js";
export async function run(): Promise<void> {
  const extension = vscode.extensions.getExtension<Prototype>(
    "clang-toolkit.clang-toolkit-prototype",
  );
  assert.ok(extension);
  assert.equal(extension.packageJSON.contributes.views.explorer, undefined);
  assert.deepEqual(extension.packageJSON.contributes.views.ctkResults, [
    { type: "webview", id: "ctk.result", name: "AST Inspector" },
  ]);
  assert.deepEqual(extension.packageJSON.contributes.viewsContainers.panel, [
    { id: "ctkResults", title: "CTK Inspector", icon: "media/semantic.svg" },
  ]);
  const folder = vscode.workspace.workspaceFolders?.[0];
  assert.ok(folder);
  const target = vscode.Uri.joinPath(folder.uri, "demo.cpp");
  const initialEditor = await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(target),
  );
  const activationDeadline = Date.now() + 20000;
  while (!extension.isActive && Date.now() < activationDeadline)
    await new Promise((done) => setTimeout(done, 40));
  assert.ok(
    extension.isActive,
    "opening C++ must activate the extension without a CTK command",
  );
  const api = extension.exports;
  const astState = () => api.details.snapshot();
  async function automaticFile(file: string, child?: string, visible = true) {
    if (visible)
      await vscode.commands.executeCommand("ctk.result.focus", {
        preserveFocus: true,
      });
    // Allow the worker's 30-second RPC plus startup/error-reporting overhead.
    const end = Date.now() + 45000;
    while (Date.now() < end) {
      const state = astState();
      if (
        !state.running &&
        !state.error &&
        state.node?.kind === "TranslationUnitDecl" &&
        state.node.file.endsWith(file) &&
        state.children !== undefined &&
        (!child || state.children.some((node) => node.name === child)) &&
        (!visible ||
          (state.rendered?.type === "rendered" &&
            state.rendered.kind === "TranslationUnitDecl"))
      )
        return state;
      await new Promise((done) => setTimeout(done, 40));
    }
    assert.fail(
      `File AST did not load automatically: ${JSON.stringify(astState())}`,
    );
  }
  const automatic = await automaticFile("demo.cpp");
  async function inspectorTab(tab: "ast" | "properties") {
    await vscode.commands.executeCommand("ctk.result.focus", {
      preserveFocus: true,
    });
    await api.details.receive({ type: "tab", tab });
    const end = Date.now() + 10000;
    while (Date.now() < end) {
      const rendered = astState().rendered;
      if (
        rendered?.type === "rendered" &&
        rendered.nodeId === astState().node?.id &&
        rendered.children.length === (astState().children?.length ?? 0) &&
        rendered.tab === tab &&
        rendered.panels.ast === (tab === "ast") &&
        rendered.panels.properties === (tab === "properties")
      )
        return rendered;
      await new Promise((done) => setTimeout(done, 40));
    }
    assert.fail(`Inspector tab did not render: ${JSON.stringify(astState())}`);
  }
  assert.equal(astState().tab, "ast");
  const originalTree = astState().tree;
  await inspectorTab("properties");
  assert.equal(astState().node!.id, automatic.node!.id);
  assert.deepEqual(
    astState().tree,
    originalTree,
    "tabs must preserve expansion and selection without loading another AST",
  );
  await inspectorTab("ast");
  assert.equal(
    vscode.window.activeTextEditor,
    initialEditor,
    "automatic AST loading must keep editor focus",
  );
  assert.ok(
    initialEditor.selection.isEmpty,
    "automatic AST loading must not select source",
  );
  assert.deepEqual(
    (api.snapshot() as { results: unknown[] }).results,
    [],
    "opening a file must not require a search",
  );
  const namespace = automatic.children?.find(
    (node) => node.kind === "NamespaceDecl",
  );
  assert.ok(namespace);
  const menuRow =
    automatic.rendered?.type === "rendered"
      ? automatic.rendered.tree.find((row) => row.id === namespace.id)
      : undefined;
  assert.ok(menuRow && !menuRow.loaded && !menuRow.selected);
  const picker: { target?: NodeActionTarget } = {};
  const originalChoose = api.actions.choose;
  try {
    api.actions.choose = async (_file, followup, node) => {
      assert.equal(followup, true);
      assert.ok(node);
      picker.target = node;
    };
    await vscode.commands.executeCommand(
      "ctk.runInspectorNodeAction",
      menuRow.context,
    );
  } finally {
    api.actions.choose = originalChoose;
  }
  assert.ok(
    picker.target,
    "the context menu command must open the existing action picker",
  );
  const clickedTarget = picker.target;
  assert.equal(
    (await clickedTarget.activate()).id,
    namespace.id,
    "right-click actions must use the clicked unloaded node, not the selected root",
  );
  assert.equal(
    astState().node!.id,
    automatic.node!.id,
    "opening an action picker must preserve inspector selection",
  );
  await assert.rejects(
    api.details.runNodeAction({
      ...menuRow.context,
      ctkAstNodeId: "expired-node",
    }),
    /no longer current/,
  );
  const initialTreeRoot = astState().node!.id;
  await api.details.receive({
    type: "expand",
    id: namespace.id,
    expanded: true,
  });
  assert.equal(
    astState().node!.id,
    initialTreeRoot,
    "expanding a branch must preserve the inspected selection",
  );
  const expandedClass = astState().tree.find(
    (row) => row.kind === "CXXRecordDecl" && row.name.endsWith("Order"),
  );
  assert.ok(
    expandedClass && expandedClass.depth === 2 && !expandedClass.loaded,
    "unvisited descendants must remain unloaded",
  );
  await api.details.receive({
    type: "expand",
    id: namespace.id,
    expanded: false,
  });
  assert.ok(
    !astState().tree.some((row) => row.id === expandedClass.id),
    "collapsing a branch must hide its descendants",
  );
  await api.details.receive({
    type: "expand",
    id: namespace.id,
    expanded: true,
  });
  assert.ok(
    astState().tree.some((row) => row.id === expandedClass.id),
    "reopening a branch must preserve retained child IDs",
  );
  await api.details.receive({ type: "child", id: namespace.id });
  assert.equal(astState().node?.kind, "NamespaceDecl");
  const lazyClass = astState().children?.find(
    (node) => node.kind === "CXXRecordDecl" && node.name.endsWith("Order"),
  );
  assert.ok(lazyClass, JSON.stringify(astState()));
  const classSelection = api.details.receive({
    type: "child",
    id: lazyClass.id,
  });
  await api.details.receive({ type: "properties", id: lazyClass.id });
  await classSelection;
  assert.ok(
    astState().children?.some((node) => node.name.includes("valid")),
    "clicking an unloaded AST child must fetch its children",
  );
  const selectedClassTree = astState().tree;
  const classProperties = await inspectorTab("properties");
  assert.match(classProperties.text, /Public members/);
  assert.match(classProperties.text, /demo::Order::quantity/);
  assert.match(classProperties.text, /demo::Order::valid/);
  await inspectorTab("ast");
  assert.deepEqual(
    astState().tree,
    selectedClassTree,
    "opening Properties during the first click's load must preserve the AST tree and selection",
  );
  const otherFile = vscode.Uri.joinPath(folder.uri, "auto-file.cpp");
  await vscode.workspace.fs.writeFile(
    otherFile,
    Buffer.from("int automaticallyLoaded() { return 7; }\n"),
  );
  await inspectorTab("properties");
  await vscode.commands.executeCommand("workbench.action.closePanel");
  const hiddenDeadline = Date.now() + 10000;
  while (astState().visible && Date.now() < hiddenDeadline)
    await new Promise((done) => setTimeout(done, 40));
  assert.equal(astState().visible, false);
  const otherEditor = await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(otherFile),
  );
  const otherAst = await automaticFile("auto-file.cpp", undefined, false);
  assert.equal(
    otherAst.visible,
    false,
    "opening C++ must keep the result panel hidden",
  );
  const literal = otherEditor.document.getText().indexOf("7");
  const beforeLiteral = otherEditor.document.positionAt(literal - 1);
  otherEditor.selection = new vscode.Selection(beforeLiteral, beforeLiteral);
  await vscode.commands.executeCommand("cursorMove", {
    to: "right",
    by: "character",
    value: 1,
  });
  const cursorDeadline = Date.now() + 15000;
  while (
    (astState().running || astState().node?.kind !== "IntegerLiteral") &&
    Date.now() < cursorDeadline
  )
    await new Promise((done) => setTimeout(done, 40));
  const hiddenSelection = astState();
  assert.equal(hiddenSelection.node?.kind, "IntegerLiteral");
  assert.equal(
    hiddenSelection.visible,
    false,
    "cursor updates must keep the result panel hidden",
  );
  assert.equal(hiddenSelection.tab, "properties");
  assert.ok(otherEditor.selection.isEmpty);
  assert.equal(
    otherEditor.document.offsetAt(otherEditor.selection.active),
    literal,
  );
  await inspectorTab("properties");
  assert.deepEqual(astState().tree, hiddenSelection.tree);
  assert.equal(astState().node?.id, hiddenSelection.node?.id);
  await inspectorTab("ast");
  await assert.rejects(clickedTarget.activate(), /no longer current/);
  assert.ok(
    otherAst.children?.some((node) => node.name === "automaticallyLoaded"),
  );
  assert.equal(vscode.window.activeTextEditor, otherEditor);
  const reloadEdit = new vscode.WorkspaceEdit();
  reloadEdit.replace(
    otherFile,
    new vscode.Range(
      otherEditor.document.positionAt(0),
      otherEditor.document.positionAt(otherEditor.document.getText().length),
    ),
    "int refreshedAutomatically() { return 8; }\n",
  );
  await vscode.workspace.applyEdit(reloadEdit);
  await otherEditor.document.save();
  const reloaded = await waitForAst(
    (state) =>
      state.contextId !== hiddenSelection.contextId &&
      state.node?.kind === "IntegerLiteral" &&
      state.node.properties.some(
        (property) =>
          property.label === "Literal value" && property.value === "8",
      ) &&
      state.tree.some((row) => row.name === "refreshedAutomatically"),
  );
  assert.notEqual(
    reloaded.tree[0]?.id,
    otherAst.node?.id,
    "saving source must replace stale native handles automatically",
  );
  await vscode.window.showTextDocument(initialEditor.document);
  const restoreDeadline = Date.now() + 15000;
  while (astState().node?.id !== lazyClass.id && Date.now() < restoreDeadline)
    await new Promise((done) => setTimeout(done, 40));
  assert.equal(astState().node?.id, lazyClass.id);
  assert.deepEqual(
    astState().tree,
    selectedClassTree,
    "switching back must restore the selected class and expanded tree",
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
  const highlightedSource = () => {
    const editor = vscode.window.activeTextEditor;
    assert.ok(
      editor,
      "AST navigation must reveal its C++ editor automatically",
    );
    return editor.document.getText(editor.selection);
  };
  async function selectEditorCode(
    uri: vscode.Uri,
    code: string,
    kind: string,
    last = false,
  ) {
    const document = await vscode.workspace.openTextDocument(uri);
    const editor = await vscode.window.showTextDocument(document, {
      preserveFocus: false,
    });
    const text = document.getText();
    const start = last ? text.lastIndexOf(code) : text.indexOf(code);
    assert.ok(start >= 0, `Missing selection fixture: ${code}`);
    editor.selection = new vscode.Selection(
      document.positionAt(start),
      document.positionAt(start),
    );
    await vscode.commands.executeCommand("cursorMove", {
      to: "right",
      by: "character",
      value: code.length,
      select: true,
    });
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) {
      const state = astState();
      if (
        !state.running &&
        !state.error &&
        (kind === "unmatched"
          ? Boolean(state.notice) && !state.canRunAction
          : !state.notice && state.node?.kind === kind)
      ) {
        assert.equal(
          highlightedSource(),
          code,
          "reverse sync must preserve the user's exact selection",
        );
        if (kind !== "unmatched") await revealedTree(kind, state.node!.id);
        return state;
      }
      await new Promise((done) => setTimeout(done, 40));
    }
    assert.fail(
      `Editor selection did not resolve ${kind}: ${JSON.stringify(astState())}`,
    );
  }
  async function moveEditorCursor(
    uri: vscode.Uri,
    code: string,
    kind: string,
    offset = 0,
    last = false,
  ) {
    const document = await vscode.workspace.openTextDocument(uri);
    const editor = await vscode.window.showTextDocument(document, {
      preserveFocus: false,
    });
    const text = document.getText();
    const start = last ? text.lastIndexOf(code) : text.indexOf(code);
    assert.ok(start >= 0, `Missing cursor fixture: ${code}`);
    const position = document.positionAt(start + offset);
    const before = document.positionAt(
      start + offset + (start + offset ? -1 : 1),
    );
    const previousId = astState().node?.id;
    const treeRoot = astState().tree.find((row) => row.depth === 0);
    if (treeRoot) {
      await api.details.receive({
        type: "expand",
        id: treeRoot.id,
        expanded: false,
      });
      assert.equal(
        astState().tree.length,
        1,
        "cursor reveal must start with collapsed ancestors",
      );
    }
    editor.selection = new vscode.Selection(before, before);
    await vscode.commands.executeCommand("cursorMove", {
      to: start + offset ? "right" : "left",
      by: "character",
      value: 1,
      select: false,
    });
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) {
      const state = astState();
      if (
        !state.running &&
        !state.error &&
        (kind === "unmatched"
          ? Boolean(state.notice) && !state.canRunAction
          : !state.notice &&
            state.node?.kind === kind &&
            state.node.id !== previousId)
      ) {
        assert.equal(vscode.window.activeTextEditor, editor);
        assert.ok(
          editor.selection.isEmpty,
          "cursor lookup must not select code",
        );
        assert.ok(
          editor.selection.active.isEqual(position),
          "cursor lookup must preserve the caret",
        );
        if (kind !== "unmatched") await revealedTree(kind, state.node!.id);
        return state;
      }
      await new Promise((done) => setTimeout(done, 40));
    }
    assert.fail(
      `Editor cursor did not resolve ${kind}: ${JSON.stringify(astState())}`,
    );
  }
  async function renderedAst(kind: string) {
    await vscode.commands.executeCommand("ctk.result.focus", {
      preserveFocus: true,
    });
    const end = Date.now() + 10000;
    while (Date.now() < end) {
      const state = astState();
      const rendered = state.rendered;
      if (
        !state.running &&
        rendered?.type === "rendered" &&
        rendered.kind === kind &&
        rendered.tree.some(
          (row) => row.id === state.node?.id && row.selected,
        ) &&
        rendered.children.length === (state.children?.length ?? 0)
      )
        return rendered;
      await new Promise((done) => setTimeout(done, 50));
    }
    assert.fail(
      `AST inspector did not render ${kind}: ${JSON.stringify(astState())}`,
    );
  }
  async function revealedTree(kind: string, id: string) {
    const rendered = await renderedAst(kind);
    assert.ok(rendered.tree.some((row) => row.id === id && row.selected));
    const tree = astState().tree;
    let selected = tree.find((row) => row.selected);
    assert.ok(
      selected,
      "cursor lookup must select its corresponding visible tree row",
    );
    while (selected.parent) {
      selected = tree.find((row) => row.id === selected!.parent);
      assert.ok(selected?.expanded, "cursor lookup must expand every ancestor");
    }
    assert.equal(selected.kind, "TranslationUnitDecl");
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
  assert.equal(
    highlightedSource(),
    "{ return quantity > 0; }",
    "Symbol Search child navigation must select its complete body",
  );
  await selectEditorCode(target, "quantity > 0", "BinaryOperator");
  await api.details.receive({ type: "back" });
  await renderedAst("CompoundStmt");
  await moveEditorCursor(
    target,
    "quantity > 0",
    "IntegerLiteral",
    "quantity > ".length,
  );
  await api.details.receive({ type: "back" });
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
      "int adjust(int value) { return value + 1; }\nint processOrder(int quantity) { return adjust(quantity); }\nint unrelated() { return 0; }\n// outside AST\n",
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
    completed: boolean;
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
    await vscode.commands.executeCommand("ctk.analysis.focus", {
      preserveFocus: true,
    });
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
  const sourceLessChild = astState().children?.find(
    (child) => !child.locationValid && !child.range.length,
  );
  if (sourceLessChild) {
    await api.details.receive({ type: "child", id: sourceLessChild.id });
    await new Promise((done) => setTimeout(done, 350));
    assert.equal(astState().node?.id, sourceLessChild.id);
    assert.equal(
      highlightedSource(),
      "",
      "a source-less child must clear the previous AST selection",
    );
    await api.details.receive({ type: "root" });
    await renderedAst("FunctionDecl");
  }
  const body = astState().children?.find(
    (child) => child.kind === "CompoundStmt",
  );
  assert.ok(body, JSON.stringify(astState()));
  await api.details.receive({ type: "child", id: body.id });
  await renderedAst("CompoundStmt");
  assert.equal(highlightedSource(), "{ return adjust(quantity); }");
  const returned = astState().children?.find(
    (child) => child.kind === "ReturnStmt",
  );
  assert.ok(returned);
  await api.details.receive({ type: "child", id: returned.id });
  await renderedAst("ReturnStmt");
  assert.equal(highlightedSource(), "return adjust(quantity)");
  const callExpression = astState().children?.find(
    (child) => child.kind === "CallExpr",
  );
  assert.ok(callExpression);
  await api.details.receive({ type: "child", id: callExpression.id });
  const callInspector = await renderedAst("CallExpr");
  const callProperties = await inspectorTab("properties");
  assert.equal(
    highlightedSource(),
    "adjust(quantity)",
    "child selection must highlight the complete call without a source-link click",
  );
  assert.ok(callInspector.properties.includes("Callee"));
  assert.ok(astState().canRunAction);
  assert.match(callProperties.text, /Run Action/);
  assert.doesNotMatch(
    callProperties.text,
    /FIELD_STATE|BINDING_MATCH_SCOPE|supportedScopes|symbolIdentity|availability|Semantic fields/,
  );
  await inspectorTab("ast");
  await api.details.receive({ type: "source" });
  assert.equal(vscode.window.activeTextEditor?.selection.start.line, 1);
  await api.details.receive({ type: "back" });
  await renderedAst("ReturnStmt");
  assert.equal(
    highlightedSource(),
    "return adjust(quantity)",
    "Back must restore the parent highlight",
  );
  await api.details.receive({ type: "root" });
  await renderedAst("FunctionDecl");
  assert.equal(
    highlightedSource(),
    "int processOrder(int quantity) { return adjust(quantity); }",
    "Selected result must restore the full function highlight",
  );
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
  await inspectorTab("properties");
  await moveEditorCursor(
    actionTarget,
    "value + 1",
    "IntegerLiteral",
    "value + ".length,
  );
  assert.equal(
    astState().tab,
    "properties",
    "cursor updates must keep the user's inspector tab",
  );
  await inspectorTab("ast");
  const restoredAstPanel = astState().rendered;
  assert.ok(
    restoredAstPanel?.type === "rendered" && restoredAstPanel.panels.ast,
  );
  await moveEditorCursor(actionTarget, "quantity", "DeclRefExpr", 2, true);
  await moveEditorCursor(actionTarget, "adjust(quantity)", "DeclRefExpr", 2);
  await moveEditorCursor(
    actionTarget,
    "adjust(quantity)",
    "CallExpr",
    "adjust".length,
  );
  const cursorSelectedId = astState().node!.id;
  assert.equal(
    (await (await api.details.actionTarget()).activate()).id,
    cursorSelectedId,
  );
  assert.equal(actionState().parseCount, 1);
  await moveEditorCursor(actionTarget, "int adjust", "FunctionDecl");
  await moveEditorCursor(actionTarget, "\n", "unmatched", 1, true);
  await assert.rejects(api.details.actionTarget(), /Select a current AST node/);
  await api.details.receive({ type: "root" });
  await renderedAst("FunctionDecl");
  // Inspector-created selections and collapsed carets must not navigate back.
  await new Promise((done) => setTimeout(done, 350));
  assert.equal(astState().node?.id, rootAstId);
  await selectEditorCode(actionTarget, "adjust(quantity)", "CallExpr");
  const sourceSelectedId = astState().node!.id;
  assert.equal(
    (await (await api.details.actionTarget()).activate()).id,
    sourceSelectedId,
    "source-selected nodes must remain executable",
  );
  await selectEditorCode(actionTarget, "djust", "DeclRefExpr", true);
  await selectEditorCode(
    actionTarget,
    "return adjust(quantity);",
    "ReturnStmt",
  );
  await selectEditorCode(
    actionTarget,
    "int unrelated() { return 0; }",
    "FunctionDecl",
  );
  assert.equal(
    astState().node?.name,
    "unrelated",
    "editor lookup must cover the parsed file beyond the original match",
  );
  assert.equal(actionState().parseCount, 1);
  await selectEditorCode(actionTarget, "outside AST", "unmatched");
  await assert.rejects(api.details.actionTarget(), /Select a current AST node/);
  await selectEditorCode(actionTarget, "adjust(quantity)", "CallExpr");
  const currentId = astState().node!.id;
  const sourceText = (
    await vscode.workspace.openTextDocument(actionTarget)
  ).getText();
  const otherStart = sourceText.indexOf("int unrelated()");
  let selectionCurrent = true;
  const superseded = api.details.selectSource(
    {
      file: actionTarget.fsPath,
      start: otherStart,
      end: sourceText.indexOf("}", otherStart) + 1,
    },
    () => selectionCurrent,
  );
  selectionCurrent = false;
  await superseded;
  assert.equal(
    astState().node!.id,
    currentId,
    "an outdated in-flight selection must not replace the current inspector node",
  );
  await api.details.receive({ type: "root" });
  await renderedAst("FunctionDecl");
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
    highlightedSource(),
    "inline int sharedTarget(int value) { return value + 1; }",
  );
  assert.equal(
    vscode.window.activeTextEditor?.document.uri.fsPath,
    headerPath,
    "a cross-file binding must still open its own source",
  );
  const headerBody = astState().children?.find(
    (child) => child.kind === "CompoundStmt",
  );
  assert.ok(headerBody);
  await api.details.receive({ type: "child", id: headerBody.id });
  assert.equal(
    highlightedSource(),
    "{ return value + 1; }",
    "header child selection must automatically highlight its header range",
  );
  await selectEditorCode(relatedHeader, "value + 1", "BinaryOperator");
  await moveEditorCursor(
    relatedHeader,
    "value + 1",
    "IntegerLiteral",
    "value + ".length,
  );
  assert.equal(
    actionState().parseCount,
    1,
    "header selection must reuse the original translation unit",
  );
  assert.equal(
    await realpath(vscode.window.activeTextEditor!.document.uri.fsPath),
    headerPath,
  );
  await api.details.receive({ type: "root" });
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
  const semanticUri = vscode.Uri.joinPath(folder.uri, "semantic-inspector.cpp");
  await vscode.workspace.fs.writeFile(
    semanticUri,
    await vscode.workspace.fs.readFile(
      vscode.Uri.joinPath(
        extension.extensionUri,
        "examples",
        "semantic-inspector.cpp",
      ),
    ),
  );
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(semanticUri),
  );
  const semanticRoot = await automaticFile("semantic-inspector.cpp");
  const widget = semanticRoot.children?.find((node) => node.name === "Widget");
  assert.ok(widget);
  await api.details.receive({ type: "properties", id: widget.id });
  const widgetProperties = await inspectorTab("properties");
  for (const text of [
    "Inheritance",
    "MidAlias",
    "Root · public virtual",
    "Hidden · protected",
    "Public members",
    "Protected members",
    "Private members",
    "Widget::secret",
    "Widget::check",
    "Widget::ratio",
  ])
    assert.ok(
      widgetProperties.text.includes(text),
      `${text}: ${widgetProperties.text}`,
    );
  assert.doesNotMatch(
    widgetProperties.text,
    /FIELD_STATE|ACCESS_SPECIFIER|symbolIdentity|availability/,
  );
  const widgetTree = astState().tree;
  await inspectorTab("ast");
  assert.deepEqual(astState().tree, widgetTree);
  const widgetBase = astState().children?.find(
    (child) => child.kind === "CXXBaseSpecifier" && child.name === "MidAlias",
  );
  assert.ok(
    widgetBase,
    "the AST must label a base specifier with its type name",
  );
  await api.details.receive({ type: "child", id: widgetBase.id });
  const middleReference = astState().semantics?.referencedDeclaration;
  assert.equal(middleReference?.name, "Middle");
  assert.ok(middleReference?.nodeId);
  assert.match((await inspectorTab("ast")).text, /Base declaration/);
  const baseTypeLoc = astState().children?.find((child) =>
    child.kind.endsWith("TypeLoc"),
  );
  assert.ok(baseTypeLoc);
  await api.details.receive({ type: "child", id: baseTypeLoc.id });
  assert.deepEqual(
    astState().semantics?.referencedDeclaration,
    middleReference,
  );
  assert.match((await inspectorTab("properties")).text, /Base declaration/);
  await api.details.receive({ type: "related", id: middleReference.nodeId });
  assert.equal(astState().node?.name, "Middle");
  assert.match(highlightedSource(), /^struct Middle : virtual public Root/);
  assert.ok(astState().canRunAction);
  await api.details.receive({ type: "child", id: widget.id });
  await inspectorTab("ast");
  for (const title of [
    "Source",
    "Inheritance",
    "Public members",
    "Protected members",
    "Private members",
    "Properties",
    "Source range",
  ])
    assert.ok(
      widgetProperties.sections.some((section) => section.title === title),
      title,
    );
  const rootBaseId = astState().semantics?.inheritance?.find(
    (base) => base.name === "Root",
  )?.nodeId;
  assert.ok(rootBaseId);
  await api.details.receive({ type: "related", id: rootBaseId });
  assert.equal(astState().node?.id, rootBaseId);
  assert.equal(astState().node?.name, "Root");
  assert.match(highlightedSource(), /^struct Root \{/);
  assert.ok(astState().canRunAction);
  assert.ok(
    astState().tree.some((row) => row.id === rootBaseId && row.selected),
  );
  assert.ok(
    astState().tree.some((row) => row.id === widget.id && row.expanded),
    "base navigation must keep the derived branch open",
  );
  await api.details.receive({ type: "back" });
  assert.equal(astState().node?.id, widget.id);
  assert.ok(
    astState().tree.some((row) => row.id === rootBaseId && row.expanded),
    "Back must keep the visited base branch",
  );
  const check = astState().children?.find(
    (node) => node.name === "Widget::check",
  );
  assert.ok(check);
  await api.details.receive({ type: "properties", id: check.id });
  const functionProperties = await inspectorTab("properties");
  for (const text of ["Parameters", "limit", "label", "const char *", "Const"])
    assert.ok(functionProperties.text.includes(text), functionProperties.text);
  const functionTree = astState().tree;
  await inspectorTab("ast");
  assert.deepEqual(astState().tree, functionTree);
  await api.details.receive({ type: "back" });
  await assert.rejects(
    api.details.receive({ type: "related", id: check.id }),
    /base class is no longer available/,
  );
  await api.details.receive({ type: "related", id: rootBaseId });
  const baseActionUri = vscode.Uri.joinPath(
    actionFolder,
    "inspect-base-fields.ctk-action",
  );
  const baseActionSource =
    '---\nname: inspect-base-fields\ndescription: Inspect the selected base class\narguments: []\n---\nmatch fieldDecl().bind("field") in node';
  await vscode.workspace.fs.writeFile(
    baseActionUri,
    Buffer.from(baseActionSource),
  );
  await api.actions.setAction(
    parseNodeAction(baseActionUri.fsPath, baseActionSource),
    true,
    await api.details.actionTarget(),
  );
  assert.equal(actionState().input.id, rootBaseId);
  await api.actions.run();
  assert.equal(
    actionState().parseCount,
    1,
    "an inheritance action must reuse its retained TU",
  );
  assert.equal(actionState().matches, 1);
  assert.deepEqual(
    actionState()
      .results.filter((node) => node.binding === "field")
      .map((node) => node.name),
    ["Root::id"],
  );
  await api.actions.close();
  await api.details.show(
    {
      id: "expired-node",
      name: "Root::Root",
      kind: "CXXRecordDecl",
      file: vscode.Uri.joinPath(folder.uri, "semantic-inspector.cpp").fsPath,
      line: 1,
      column: 1,
      excerpt: "",
      raw: {},
    },
    async () => {
      throw new Error("cursor unavailable");
    },
    async () => {
      throw new Error("Expired nodes cannot run actions");
    },
  );
  const expiredState = astState();
  assert.equal(expiredState.error, "cursor unavailable");
  assert.equal(expiredState.canRunAction, false);
  assert.equal(expiredState.inspectionStatus.command, "ctk.reloadFileAst");
  assert.match(
    String(expiredState.inspectionStatus.tooltip),
    /analysis session expired/,
  );
  assert.doesNotMatch(
    String(expiredState.inspectionStatus.tooltip),
    /cursor unavailable/,
  );
  const expiredProperties = await inspectorTab("properties");
  assert.doesNotMatch(
    expiredProperties.text,
    /AST Inspector|← Back|File AST|cursor unavailable|Retry loading children/,
  );
  await assert.rejects(api.details.actionTarget(), /Select a current AST node/);
  await vscode.commands.executeCommand("ctk.reloadFileAst");
  const refreshedAst = await automaticFile("semantic-inspector.cpp");
  const refreshedClass = refreshedAst.children?.find(
    (node) => node.name === "Root",
  );
  assert.ok(refreshedClass);
  await api.details.receive({ type: "child", id: refreshedClass.id });
  const injected = astState().children?.find(
    (node) => node.name === "Root::Root",
  );
  assert.ok(injected);
  await api.details.receive({ type: "child", id: injected.id });
  assert.equal(astState().error, "");
  assert.equal(astState().node?.name, "Root::Root");
  assert.equal(astState().canRunAction, true);
  const owningContext = astState().contextId;
  const owningNode = astState().node!.id;
  const closingTarget = await api.details.actionTarget();
  await api.actions.setAction(
    parseNodeAction(baseActionUri.fsPath, baseActionSource),
    true,
    closingTarget,
  );
  await api.actions.run();
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(semanticUri),
    { viewColumn: vscode.ViewColumn.Two },
  );
  const duplicateTab = vscode.window.tabGroups.activeTabGroup.activeTab;
  assert.ok(duplicateTab);
  await vscode.window.tabGroups.close(duplicateTab);
  await new Promise((done) => setTimeout(done, 350));
  assert.equal(
    astState().contextId,
    owningContext,
    "closing one split must keep the other tab's session",
  );
  assert.equal(astState().node?.id, owningNode);
  assert.equal(actionState().completed, true);
  const cxxTabs = vscode.window.tabGroups.all.flatMap((group) =>
    group.tabs.filter(
      (tab) =>
        tab.input instanceof vscode.TabInputText &&
        /\.(?:c|cc|cpp|cxx|h|hh|hpp|hxx)$/i.test(tab.input.uri.fsPath),
    ),
  );
  await vscode.window.tabGroups.close(cxxTabs);
  const closedDeadline = Date.now() + 15000;
  while (
    (astState().node || actionState().completed) &&
    Date.now() < closedDeadline
  )
    await new Promise((done) => setTimeout(done, 40));
  assert.equal(
    astState().node,
    undefined,
    "closing the owning source tab must clear its inspector",
  );
  assert.equal(
    actionState().completed,
    false,
    "closing the owning tab must release transferred action resources",
  );
  await assert.rejects(
    closingTarget.activate(),
    /Source or settings changed|no longer current|closed/,
  );
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(semanticUri),
  );
  const reopened = await automaticFile("semantic-inspector.cpp", "Root");
  assert.notEqual(
    reopened.contextId,
    owningContext,
    "reopening the same path must create a fresh live session",
  );
  assert.equal(reopened.canRunAction, true);
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(semanticUri),
    { preview: false },
  );
  const rootClass = reopened.children!.find((node) => node.name === "Root")!;
  const middleClass = reopened.children!.find(
    (node) => node.name === "Middle",
  )!;
  await api.details.receive({
    type: "expand",
    id: rootClass.id,
    expanded: true,
  });
  await api.details.receive({
    type: "expand",
    id: middleClass.id,
    expanded: true,
  });
  await api.details.receive({ type: "child", id: rootClass.id });
  await api.details.receive({
    type: "expand",
    id: rootClass.id,
    expanded: false,
  });
  await inspectorTab("properties");
  const savedFirst = astState();
  const firstTarget = await api.details.actionTarget();
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(otherFile),
    { preview: false },
  );
  const secondRoot = await automaticFile(
    "auto-file.cpp",
    "refreshedAutomatically",
  );
  const secondFunction = secondRoot.children!.find(
    (node) => node.name === "refreshedAutomatically",
  )!;
  await api.details.receive({ type: "child", id: secondFunction.id });
  await inspectorTab("ast");
  const savedSecond = astState();
  const secondTarget = await api.details.actionTarget();
  async function restoredFile(
    uri: vscode.Uri,
    saved: ReturnType<typeof astState>,
  ) {
    await vscode.window.showTextDocument(
      await vscode.workspace.openTextDocument(uri),
      { preview: false },
    );
    const end = Date.now() + 15000;
    while (
      (astState().contextId !== saved.contextId || astState().running) &&
      Date.now() < end
    )
      await new Promise((done) => setTimeout(done, 40));
    const restored = astState();
    assert.equal(
      restored.contextId,
      saved.contextId,
      "switching tabs must reuse its native context",
    );
    assert.equal(
      restored.node?.id,
      saved.node?.id,
      "the selected native node must survive tab switching",
    );
    assert.deepEqual(
      restored.tree,
      saved.tree,
      "loaded branches and expansion must survive tab switching",
    );
    assert.equal(
      restored.tab,
      saved.tab,
      "each file must restore its own AST/Properties tab",
    );
  }
  await restoredFile(semanticUri, savedFirst);
  await api.actions.setAction(
    parseNodeAction(baseActionUri.fsPath, baseActionSource),
    true,
    firstTarget,
  );
  await api.actions.run();
  assert.equal(
    actionState().parseCount,
    1,
    "returning to the first file must not reparse it",
  );
  await api.actions.refresh();
  await restoredFile(otherFile, savedSecond);
  await api.actions.setAction(
    parseNodeAction(baseActionUri.fsPath, baseActionSource),
    true,
    secondTarget,
  );
  await api.actions.run();
  assert.equal(
    actionState().parseCount,
    1,
    "the second file must retain its independent parse",
  );
  await api.actions.refresh();
  await restoredFile(semanticUri, savedFirst);
  async function tabsFor(uri: vscode.Uri) {
    const file = await realpath(uri.fsPath);
    const tabs: vscode.Tab[] = [];
    for (const group of vscode.window.tabGroups.all)
      for (const tab of group.tabs)
        if (
          tab.input instanceof vscode.TabInputText &&
          (await realpath(tab.input.uri.fsPath).catch(() => "")) === file
        )
          tabs.push(tab);
    assert.ok(tabs.length, `No open tabs for ${file}`);
    return tabs;
  }
  const lastFirstTabs = await tabsFor(semanticUri);
  await vscode.window.tabGroups.close(lastFirstTabs);
  await restoredFile(otherFile, savedSecond);
  await assert.rejects(
    firstTarget.activate(),
    /Source or settings changed|closed/,
  );
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(semanticUri),
    { preview: false },
  );
  const freshFirst = await automaticFile("semantic-inspector.cpp", "Root");
  assert.notEqual(freshFirst.contextId, savedFirst.contextId);
  assert.notEqual(freshFirst.node?.id, reopened.node?.id);
  const lastSecondTabs = await tabsFor(otherFile);
  await vscode.window.tabGroups.close(lastSecondTabs);
  await new Promise((done) => setTimeout(done, 350));
  assert.equal(
    astState().contextId,
    freshFirst.contextId,
    "closing an inactive file must not release the active file's context",
  );
  await assert.rejects(
    secondTarget.activate(),
    /Source or settings changed|closed/,
  );
  const savedUri = vscode.Uri.joinPath(folder.uri, "save-state.cpp");
  const savedSource = `// λ\nnamespace sample {\nstruct Keep {\n  int run(int value) { return value + 7; }\n  int run(double value) { return (int)value; }\n};\nstruct Other { int flag; };\n}\n`;
  await vscode.workspace.fs.writeFile(savedUri, Buffer.from(savedSource));
  const savedEditor = await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(savedUri),
    { preview: false },
  );
  await automaticFile("save-state.cpp", "sample");
  const numberOffset = savedSource.indexOf("7;");
  const beforeNumber = savedEditor.document.positionAt(numberOffset - 1);
  savedEditor.selection = new vscode.Selection(beforeNumber, beforeNumber);
  await vscode.commands.executeCommand("cursorMove", {
    to: "right",
    by: "character",
    value: 1,
  });
  async function waitForAst(
    predicate: (state: ReturnType<typeof astState>) => boolean,
  ) {
    const end = Date.now() + 45000;
    while (Date.now() < end) {
      const state = astState();
      if (!state.running && !state.error && predicate(state)) return state;
      await new Promise((done) => setTimeout(done, 40));
    }
    assert.fail(
      `AST restoration did not finish: ${JSON.stringify(astState())}`,
    );
  }
  await waitForAst((state) => state.node?.kind === "IntegerLiteral");
  const otherClass = astState().tree.find(
    (row) => row.name === "sample::Other",
  );
  assert.ok(otherClass);
  await api.details.receive({
    type: "expand",
    id: otherClass.id,
    expanded: true,
  });
  await inspectorTab("properties");
  const beforeSave = astState(),
    staleSavedTarget = await api.details.actionTarget();
  const editSaved = new vscode.WorkspaceEdit();
  editSaved.insert(
    savedUri,
    new vscode.Position(0, 0),
    "// inserted above the AST\n",
  );
  editSaved.replace(
    savedUri,
    new vscode.Range(
      savedEditor.document.positionAt(numberOffset),
      savedEditor.document.positionAt(numberOffset + 1),
    ),
    "99",
  );
  await vscode.workspace.applyEdit(editSaved);
  await savedEditor.document.save();
  const afterSave = await waitForAst(
    (state) =>
      state.contextId !== beforeSave.contextId &&
      state.node?.kind === "IntegerLiteral" &&
      state.node.properties.some(
        (property) =>
          property.label === "Literal value" && property.value === "99",
      ),
  );
  assert.notEqual(
    afterSave.node?.id,
    beforeSave.node?.id,
    "saving must replace native handles",
  );
  assert.equal(afterSave.tab, "properties");
  for (const expanded of ["sample", "sample::Keep", "sample::Other"])
    assert.ok(
      afterSave.tree.some((row) => row.name === expanded && row.expanded),
      `save must preserve expanded ${expanded}`,
    );
  assert.equal(
    afterSave.tree.filter(
      (row) => row.name === "sample::Keep::run" && row.expanded,
    ).length,
    1,
    "restore must preserve the exact overload",
  );
  await assert.rejects(
    staleSavedTarget.activate(),
    /Source or settings changed|closed/,
  );
  const savedActionTarget = await api.details.actionTarget();
  await api.actions.setAction(
    parseNodeAction(baseActionUri.fsPath, baseActionSource),
    true,
    savedActionTarget,
  );
  await api.actions.run();
  assert.equal(
    actionState().parseCount,
    1,
    "rebinding branches must reuse the new parse",
  );
  await api.actions.refresh();
  const returnText = "return value + 99;",
    returnStart = savedEditor.document.getText().indexOf(returnText);
  const removeReturn = new vscode.WorkspaceEdit();
  removeReturn.delete(
    savedUri,
    new vscode.Range(
      savedEditor.document.positionAt(returnStart),
      savedEditor.document.positionAt(returnStart + returnText.length),
    ),
  );
  await vscode.workspace.applyEdit(removeReturn);
  await savedEditor.document.save();
  const removedSelection = await waitForAst(
    (state) =>
      state.contextId !== afterSave.contextId &&
      state.node?.kind === "CompoundStmt",
  );
  assert.ok(
    removedSelection.tree.some(
      (row) => row.name === "sample::Other" && row.expanded,
    ),
  );
  const bodyRow = removedSelection.tree.find((row) => row.selected);
  assert.ok(bodyRow?.parent);
  await api.details.receive({ type: "child", id: bodyRow.parent });
  const selectedMethod = astState();
  assert.equal(selectedMethod.node?.kind, "CXXMethodDecl");
  assert.deepEqual(selectedMethod.semantics?.parameters, [
    { name: "value", type: "int" },
  ]);
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(semanticUri),
    { preview: false },
  );
  const foreground = await automaticFile("semantic-inspector.cpp", "Root");
  const inactiveEdit = new vscode.WorkspaceEdit();
  inactiveEdit.insert(
    savedUri,
    new vscode.Position(0, 0),
    "// saved while another tab is active\n",
  );
  await vscode.workspace.applyEdit(inactiveEdit);
  await savedEditor.document.save();
  type RetainedFile = {
    file: string;
    stale: boolean;
    error?: string;
    contextId?: string;
    node?: { id: string; name: string; kind: string };
  };
  const inactiveDeadline = Date.now() + 45000;
  let refreshedInactive: RetainedFile | undefined;
  while (Date.now() < inactiveDeadline) {
    refreshedInactive = (
      api.snapshot() as { inspectorFiles: RetainedFile[] }
    ).inspectorFiles.find((file) => file.file.endsWith("/save-state.cpp"));
    if (
      !refreshedInactive?.stale &&
      refreshedInactive?.contextId !== selectedMethod.contextId &&
      refreshedInactive?.node?.id !== selectedMethod.node?.id
    )
      break;
    await new Promise((done) => setTimeout(done, 40));
  }
  assert.ok(
    refreshedInactive &&
      !refreshedInactive.stale &&
      refreshedInactive.node?.id !== selectedMethod.node?.id,
    "an inactive saved file must refresh before it is revisited",
  );
  assert.equal(
    astState().contextId,
    foreground.contextId,
    "background save must not replace the active inspector",
  );
  await vscode.window.showTextDocument(savedEditor.document, {
    preview: false,
  });
  const restoredSaved = await waitForAst(
    (state) => state.contextId === refreshedInactive?.contextId,
  );
  assert.equal(restoredSaved.node?.id, refreshedInactive.node?.id);
  assert.equal(restoredSaved.node?.name, "sample::Keep::run");
  assert.deepEqual(restoredSaved.semantics?.parameters, [
    { name: "value", type: "int" },
  ]);
  assert.equal(restoredSaved.tab, "properties");
  assert.ok(
    restoredSaved.tree.some(
      (row) => row.name === "sample::Other" && row.expanded,
    ),
  );
  const parseFailure = "#error deliberate saved-file parse failure\n";
  const parseErrors = () =>
    vscode.languages
      .getDiagnostics()
      .flatMap(([uri, diagnostics]) =>
        diagnostics
          .filter((diagnostic) => diagnostic.source === "CTK")
          .map((diagnostic) => ({ uri, diagnostic })),
      );
  const retainedSavedFile = () =>
    (api.snapshot() as { inspectorFiles: RetainedFile[] }).inspectorFiles.find(
      (file) => file.file.endsWith("/save-state.cpp"),
    );
  async function saveParseFailure() {
    const edit = new vscode.WorkspaceEdit();
    edit.insert(savedUri, new vscode.Position(0, 0), parseFailure);
    assert.equal(await vscode.workspace.applyEdit(edit), true);
    assert.equal(await savedEditor.document.save(), true);
    const end = Date.now() + 45000;
    while (Date.now() < end) {
      if (
        retainedSavedFile()?.error &&
        parseErrors().some(({ diagnostic }) =>
          diagnostic.message.includes("deliberate saved-file parse failure"),
        )
      )
        return;
      await new Promise((done) => setTimeout(done, 40));
    }
    assert.fail(
      `A real Clang parse error was not reported: ${JSON.stringify(api.snapshot())}`,
    );
  }
  async function repairParseFailure() {
    const edit = new vscode.WorkspaceEdit();
    edit.delete(
      savedUri,
      new vscode.Range(new vscode.Position(0, 0), new vscode.Position(1, 0)),
    );
    assert.equal(await vscode.workspace.applyEdit(edit), true);
    assert.equal(await savedEditor.document.save(), true);
  }
  const beforeFailure = astState(),
    expiredAfterFailure = await api.details.actionTarget();
  await saveParseFailure();
  const failedSave = astState();
  const locatedErrors = parseErrors();
  assert.equal(
    locatedErrors.length,
    1,
    "native parse errors must appear once in Problems",
  );
  assert.equal(
    await realpath(locatedErrors[0]!.uri.fsPath),
    await realpath(savedUri.fsPath),
  );
  assert.equal(
    locatedErrors[0]!.diagnostic.severity,
    vscode.DiagnosticSeverity.Error,
  );
  assert.equal(locatedErrors[0]!.diagnostic.range.start.line, 0);
  assert.equal(
    locatedErrors[0]!.diagnostic.range.start.character,
    1,
    "Problems must retain Clang's exact #error location",
  );
  assert.equal(
    locatedErrors[0]!.diagnostic.message,
    "deliberate saved-file parse failure",
  );
  const clangProblems =
    vscode.languages.createDiagnosticCollection("ctk-test-clang");
  async function waitForProblemCount(count: number) {
    const end = Date.now() + 10000;
    while (Date.now() < end && parseErrors().length !== count)
      await new Promise((done) => setTimeout(done, 40));
    assert.equal(
      parseErrors().length,
      count,
      "CTK must respond to another provider's diagnostic changes",
    );
  }
  try {
    const duplicate = new vscode.Diagnostic(
      new vscode.Range(0, 1, 0, 6),
      "Deliberate saved-file parse failure",
      vscode.DiagnosticSeverity.Error,
    );
    duplicate.source = "clang";
    duplicate.code = "pp_hash_error";
    clangProblems.set(locatedErrors[0]!.uri, [duplicate]);
    await waitForProblemCount(0);
    const sharedErrors = vscode.languages
      .getDiagnostics(locatedErrors[0]!.uri)
      .filter(
        (diagnostic) =>
          diagnostic.message.toLowerCase() ===
          "deliberate saved-file parse failure",
      );
    assert.equal(
      sharedErrors.length,
      1,
      "Problems must keep only the matching clang entry",
    );
    assert.equal(sharedErrors[0]!.source, "clang");
    assert.equal(
      astState().contextId,
      failedSave.contextId,
      "deduplication must not replace the cached AST",
    );
    clangProblems.delete(locatedErrors[0]!.uri);
    await waitForProblemCount(1);
    assert.equal(
      parseErrors()[0]!.diagnostic.source,
      "CTK",
      "CTK must remain available when clang stops reporting the error",
    );
    clangProblems.set(locatedErrors[0]!.uri, [duplicate]);
    await waitForProblemCount(0);
    const changedError = new vscode.WorkspaceEdit();
    changedError.replace(
      savedUri,
      savedEditor.document.lineAt(0).range,
      "#error edited saved-file parse failure",
    );
    assert.equal(await vscode.workspace.applyEdit(changedError), true);
    assert.equal(savedEditor.document.isDirty, true);
    assert.equal(
      parseErrors().length,
      0,
      "editing must invalidate hidden CTK fallbacks immediately",
    );
    assert.equal(
      astState().inspectionStatus.text,
      "",
      "editing must immediately clear the stale parsing status as well",
    );
    assert.equal(astState().error, "");
    assert.equal(astState().canRunAction, false);
    await new Promise<void>((resolve, reject) => {
      const listener = vscode.languages.onDidChangeDiagnostics((event) => {
        if (
          !event.uris.some(
            (uri) => uri.toString() === locatedErrors[0]!.uri.toString(),
          )
        )
          return;
        clearTimeout(timer);
        listener.dispose();
        resolve();
      });
      const timer = setTimeout(() => {
        listener.dispose();
        reject(new Error("clang diagnostic removal was not observed"));
      }, 10000);
      clangProblems.delete(locatedErrors[0]!.uri);
    });
    assert.equal(
      parseErrors().length,
      0,
      "clang removing a stale error must not resurrect CTK's previous saved-file error",
    );
    assert.equal(await savedEditor.document.save(), true);
    const editedDeadline = Date.now() + 45000;
    while (
      Date.now() < editedDeadline &&
      !parseErrors().some(
        ({ diagnostic }) =>
          diagnostic.message === "edited saved-file parse failure",
      )
    )
      await new Promise((done) => setTimeout(done, 40));
    assert.deepEqual(
      parseErrors().map(({ diagnostic }) => diagnostic.message),
      ["edited saved-file parse failure"],
      "the next save must publish only the new parser result",
    );
    assert.equal(
      astState().contextId,
      beforeFailure.contextId,
      "editing and refreshing Problems must keep the last valid AST",
    );
    assert.match(astState().inspectionStatus.text, /AST refresh failed/);
    assert.match(
      String(astState().inspectionStatus.tooltip),
      /edited saved-file parse failure/,
    );
  } finally {
    clangProblems.dispose();
  }
  assert.match(failedSave.error, /Clang reported errors|parsing|parse/i);
  assert.equal(failedSave.node?.id, beforeFailure.node?.id);
  assert.equal(failedSave.contextId, beforeFailure.contextId);
  assert.deepEqual(
    failedSave.tree,
    beforeFailure.tree,
    "a failed parse must leave every old branch and selection visible",
  );
  assert.deepEqual(failedSave.node, beforeFailure.node);
  assert.deepEqual(failedSave.semantics, beforeFailure.semantics);
  assert.equal(failedSave.tab, "properties");
  assert.equal(failedSave.canRunAction, false);
  assert.match(failedSave.inspectionStatus.text, /AST refresh failed/);
  assert.match(String(failedSave.inspectionStatus.tooltip), /save-state\.cpp/);
  assert.match(
    String(failedSave.inspectionStatus.tooltip),
    /last valid AST.*Save this file again to retry/s,
  );
  await assert.rejects(api.details.actionTarget(), /current AST node/);
  await assert.rejects(
    expiredAfterFailure.activate(),
    /Source or settings changed|closed/,
  );
  await api.details.selectSource({ file: savedUri.fsPath, start: 0, end: 0 });
  await inspectorTab("ast");
  await api.details.receive({
    type: "expand",
    id: failedSave.tree[0]!.id,
    expanded: false,
  });
  assert.deepEqual(
    astState().tree,
    beforeFailure.tree,
    "failed snapshots must not navigate invalid native handles",
  );
  await inspectorTab("properties");
  const failedRendered = astState().rendered;
  assert.ok(
    failedRendered?.type === "rendered" &&
      !failedRendered.text.includes("Clang reported errors"),
    "parse errors belong only in the status bar",
  );
  await new Promise((done) => setTimeout(done, 800));
  assert.equal(
    astState().running,
    false,
    "failed parsing must not start a retry loop",
  );
  assert.equal(astState().contextId, beforeFailure.contextId);
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(semanticUri),
    { preview: false },
  );
  const unaffected = await automaticFile("semantic-inspector.cpp", "Root");
  assert.equal(unaffected.canRunAction, true);
  assert.match(
    unaffected.inspectionStatus.text,
    /AST refresh failed/,
    "an inactive file's error remains available in the status bar",
  );
  await vscode.window.showTextDocument(savedEditor.document, {
    preview: false,
  });
  const failureRestoreEnd = Date.now() + 10000;
  while (
    Date.now() < failureRestoreEnd &&
    (astState().contextId !== beforeFailure.contextId || !astState().error)
  )
    await new Promise((done) => setTimeout(done, 40));
  assert.equal(
    astState().contextId,
    beforeFailure.contextId,
    "revisiting a failed saved file must restore its last valid AST without reparsing",
  );
  assert.ok(astState().error);
  assert.deepEqual(astState().tree, beforeFailure.tree);
  await repairParseFailure();
  const recovered = await waitForAst(
    (state) =>
      state.contextId !== beforeFailure.contextId &&
      state.node?.name === "sample::Keep::run",
  );
  assert.equal(retainedSavedFile()?.error, undefined);
  assert.equal(
    parseErrors().length,
    0,
    "a successful saved parse must clear the file's Problems",
  );
  assert.equal(recovered.canRunAction, true);
  assert.equal(recovered.tab, "properties");
  assert.ok(
    recovered.tree.some((row) => row.name === "sample::Other" && row.expanded),
  );
  assert.deepEqual(recovered.semantics?.parameters, [
    { name: "value", type: "int" },
  ]);
  assert.doesNotMatch(recovered.inspectionStatus.text, /refresh failed/);
  await api.actions.setAction(
    parseNodeAction(baseActionUri.fsPath, baseActionSource),
    true,
    await api.details.actionTarget(),
  );
  await api.actions.run();
  assert.equal(
    actionState().parseCount,
    1,
    "a recovered action must use the successful replacement parse",
  );
  await api.actions.refresh();
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(semanticUri),
    { preview: false },
  );
  const backgroundForeground = await automaticFile(
    "semantic-inspector.cpp",
    "Root",
  );
  await saveParseFailure();
  assert.equal(astState().contextId, backgroundForeground.contextId);
  assert.equal(
    astState().canRunAction,
    true,
    "an unrelated failed save must not disable the active AST",
  );
  assert.match(astState().inspectionStatus.text, /AST refresh failed/);
  assert.equal(
    parseErrors().length,
    1,
    "failed background saves must publish their own Problems",
  );
  assert.equal(retainedSavedFile()?.contextId, recovered.contextId);
  await repairParseFailure();
  const backgroundRecoveryEnd = Date.now() + 45000;
  while (Date.now() < backgroundRecoveryEnd) {
    const retained = retainedSavedFile();
    if (
      retained &&
      !retained.stale &&
      !retained.error &&
      retained.contextId !== recovered.contextId
    )
      break;
    await new Promise((done) => setTimeout(done, 40));
  }
  assert.equal(
    retainedSavedFile()?.stale,
    false,
    `the next inactive save must retry the failed parse: ${JSON.stringify(retainedSavedFile())}`,
  );
  assert.equal(retainedSavedFile()?.error, undefined);
  assert.equal(
    parseErrors().length,
    0,
    "background recovery must clear its Problems",
  );
  assert.notEqual(retainedSavedFile()?.contextId, recovered.contextId);
  assert.equal(astState().contextId, backgroundForeground.contextId);
  assert.doesNotMatch(astState().inspectionStatus.text, /refresh failed/);
  await vscode.window.showTextDocument(savedEditor.document, {
    preview: false,
  });
  const recoveredBackground = await waitForAst(
    (state) => state.contextId === retainedSavedFile()?.contextId,
  );
  assert.equal(recoveredBackground.node?.name, "sample::Keep::run");
  assert.equal(recoveredBackground.canRunAction, true);
  assert.ok(
    recoveredBackground.tree.some(
      (row) => row.name === "sample::Other" && row.expanded,
    ),
  );
  await saveParseFailure();
  await vscode.window.showTextDocument(
    await vscode.workspace.openTextDocument(semanticUri),
    { preview: false },
  );
  const beforeFailedClose = await automaticFile(
    "semantic-inspector.cpp",
    "Root",
  );
  await vscode.window.tabGroups.close(await tabsFor(savedUri));
  const failedCloseEnd = Date.now() + 10000;
  while (Date.now() < failedCloseEnd && retainedSavedFile())
    await new Promise((done) => setTimeout(done, 40));
  assert.equal(
    retainedSavedFile(),
    undefined,
    "closing the failed file's last tab must release its snapshot and session",
  );
  assert.equal(
    parseErrors().length,
    0,
    "closing a failed file's last tab must clear its Problems",
  );
  assert.equal(astState().contextId, beforeFailedClose.contextId);
  assert.doesNotMatch(
    astState().inspectionStatus.text,
    /refresh failed/,
    "closing a failed file must clear its status-bar error",
  );
  const draftUri = vscode.Uri.joinPath(folder.uri, "draft-navigation.cpp"),
    draftHeaderUri = vscode.Uri.joinPath(folder.uri, "draft-navigation.hpp"),
    savedDraft =
      '#include "draft-navigation.hpp"\nstruct DraftDerived : draft::Base {};\n',
    savedHeader = "namespace draft { struct Base { int savedField; }; }\n";
  await vscode.workspace.fs.writeFile(draftUri, Buffer.from(savedDraft));
  await vscode.workspace.fs.writeFile(draftHeaderUri, Buffer.from(savedHeader));
  const draftDocument = await vscode.workspace.openTextDocument(draftUri),
    draftHeaderDocument =
      await vscode.workspace.openTextDocument(draftHeaderUri);
  await vscode.window.showTextDocument(draftHeaderDocument, { preview: false });
  await vscode.window.showTextDocument(draftDocument, { preview: false });
  const draftRoot = await automaticFile("draft-navigation.cpp", "DraftDerived"),
    draftDerived = draftRoot.children!.find(
      (node) => node.name === "DraftDerived",
    )!;
  await api.details.receive({ type: "properties", id: draftDerived.id });
  const oldBase = astState().semantics?.inheritance?.[0]?.nodeId;
  assert.ok(oldBase);
  const draftText = `// λ😀 unsaved source\n\n${savedDraft}`,
    draftHeaderText =
      "// λ😀 unsaved header\n\nnamespace draft { struct Base { int bufferField; }; }\n",
    draftEdit = new vscode.WorkspaceEdit();
  draftEdit.replace(
    draftUri,
    new vscode.Range(
      draftDocument.positionAt(0),
      draftDocument.positionAt(draftDocument.getText().length),
    ),
    draftText,
  );
  draftEdit.replace(
    draftHeaderUri,
    new vscode.Range(
      draftHeaderDocument.positionAt(0),
      draftHeaderDocument.positionAt(draftHeaderDocument.getText().length),
    ),
    draftHeaderText,
  );
  assert.equal(await vscode.workspace.applyEdit(draftEdit), true);
  assert.equal(draftDocument.isDirty, true);
  assert.equal(draftHeaderDocument.isDirty, true);
  const draftReady = Date.now() + 10000;
  while (astState().running && Date.now() < draftReady)
    await new Promise((done) => setTimeout(done, 40));
  assert.equal(
    astState().running,
    false,
    "wait until the Properties base link is enabled before activating it",
  );
  await api.details.receive({ type: "related", id: oldBase });
  assert.equal(astState().error, "", JSON.stringify(astState()));
  assert.equal(astState().node?.name, "draft::Base");
  assert.equal(astState().node?.line, 3);
  assert.ok(
    astState().children?.some(
      (node) => node.name === "draft::Base::bufferField",
    ),
  );
  assert.equal(
    vscode.window.activeTextEditor?.document,
    draftHeaderDocument,
    "base navigation must reuse the existing unsaved header document, including URI aliases",
  );
  assert.equal(highlightedSource(), "struct Base { int bufferField; }");
  assert.equal(draftDocument.isDirty, true);
  assert.equal(draftHeaderDocument.isDirty, true);
  assert.equal(
    Buffer.from(await vscode.workspace.fs.readFile(draftUri)).toString(),
    savedDraft,
  );
  assert.equal(
    Buffer.from(await vscode.workspace.fs.readFile(draftHeaderUri)).toString(),
    savedHeader,
  );
  await api.actions.setAction(
    parseNodeAction(baseActionUri.fsPath, baseActionSource),
    true,
    await api.details.actionTarget(),
  );
  await api.actions.run();
  assert.equal(actionState().parseCount, 1);
  assert.ok(
    actionState().results.some(
      (node) => node.name === "draft::Base::bufferField",
    ),
  );
  await api.actions.refresh();
  await vscode.window.showTextDocument(draftHeaderDocument);
  await vscode.commands.executeCommand(
    "workbench.action.revertAndCloseActiveEditor",
  );
  await vscode.window.showTextDocument(draftDocument);
  await vscode.commands.executeCommand(
    "workbench.action.revertAndCloseActiveEditor",
  );

  const firstDirtyUri = vscode.Uri.joinPath(folder.uri, "first-dirty.cpp"),
    firstSaved = "struct SavedOnly {};\n",
    firstDraft =
      "// never saved\nstruct BufferBase { int field; };\nstruct BufferDerived : BufferBase {};\n";
  await vscode.workspace.fs.writeFile(firstDirtyUri, Buffer.from(firstSaved));
  const firstDirtyDocument =
      await vscode.workspace.openTextDocument(firstDirtyUri),
    firstEdit = new vscode.WorkspaceEdit();
  firstEdit.replace(
    firstDirtyUri,
    new vscode.Range(
      firstDirtyDocument.positionAt(0),
      firstDirtyDocument.positionAt(firstDirtyDocument.getText().length),
    ),
    firstDraft,
  );
  await vscode.workspace.applyEdit(firstEdit);
  await vscode.window.showTextDocument(firstDirtyDocument, { preview: false });
  const firstDirtyRoot = await automaticFile(
    "first-dirty.cpp",
    "BufferDerived",
  );
  await api.details.receive({
    type: "properties",
    id: firstDirtyRoot.children!.find((node) => node.name === "BufferDerived")!
      .id,
  });
  const firstBase = astState().semantics?.inheritance?.[0]?.nodeId;
  assert.ok(firstBase);
  await api.details.receive({ type: "related", id: firstBase });
  assert.equal(astState().node?.name, "BufferBase");
  assert.equal(highlightedSource(), "struct BufferBase { int field; }");
  assert.equal(firstDirtyDocument.isDirty, true);
  assert.equal(
    Buffer.from(await vscode.workspace.fs.readFile(firstDirtyUri)).toString(),
    firstSaved,
  );
  await vscode.commands.executeCommand(
    "workbench.action.revertAndCloseActiveEditor",
  );
  console.log(
    "CTK_EXTENSION_HOST_PASS: real Clang save failures preserve the last valid AST, selection, expansion and Properties; status-bar errors, blocked stale actions, no tab-triggered retry, next-save recovery and background failure/recovery; save refresh preserving shifted/changed nodes, exact overloads, expanded branches and Properties; deleted-node parent fallback; inactive-save refresh without stealing the inspector; independent per-file sessions without reparsing, shared action ownership, last-tab release/reopen, CTK Inspector, live renewal, split-tab ownership, symbols, console, YAML actions, grouped matches, retained-node follow-up, stale edits, completion, semantic sections, base/source navigation and actions",
  );
}
