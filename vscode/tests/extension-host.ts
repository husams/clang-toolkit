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
        'emit match cxxRecordDecl(isExpansionInMainFile(), isDefinition(), unless(isImplicit())).bind("symbol");',
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
  console.log(
    "CTK_EXTENSION_HOST_PASS: unified native analyses, scripts, completion, hover and source/details",
  );
}
