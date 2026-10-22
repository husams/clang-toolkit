import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { realpath } from "node:fs/promises";
import { dirname } from "node:path";
import { promisify } from "node:util";
import * as vscode from "vscode";

/** Runs inside one real VS Code extension host against the native server. */
export async function testSymbolNavigation(
  extensionUri: vscode.Uri,
  workspace: vscode.Uri,
): Promise<void> {
  const external = vscode.Uri.file(`${dirname(workspace.fsPath)}/library`);
  await vscode.workspace.fs.createDirectory(external);
  const header = vscode.Uri.joinPath(external, "api.hpp");
  const definition = vscode.Uri.joinPath(external, "api.cpp");
  await vscode.workspace.fs.writeFile(
    header,
    Buffer.from(
      "namespace vendor { int choose(int); double choose(double); struct Item { int method(); int value; }; }\n",
    ),
  );
  await vscode.workspace.fs.writeFile(
    definition,
    Buffer.from(
      '#include "api.hpp"\nint vendor::choose(int value) { return value; }\ndouble vendor::choose(double value) { return value; }\nint vendor::Item::method() { return value; }\n',
    ),
  );
  const source = vscode.Uri.joinPath(workspace, "references.cpp");
  const text =
    '#include "../library/api.hpp"\nint entry(vendor::Item &item) { /* 😀 */ int local = 1; return vendor::choose(local) + item.method() + item.value; }\n';
  await vscode.workspace.fs.writeFile(source, Buffer.from(text));
  for (const [directory, file] of [
    [external, definition],
    [workspace, source],
  ] as const) {
    await vscode.workspace.fs.writeFile(
      vscode.Uri.joinPath(directory, "compile_commands.json"),
      Buffer.from(
        JSON.stringify([
          {
            directory: directory.fsPath,
            file: file.fsPath,
            arguments: ["clang++", "-std=c++20", "-c", file.fsPath],
          },
        ]),
      ),
    );
  }
  const settings = vscode.workspace.getConfiguration("ctk", source);
  const python = settings.get<string>("pythonPath");
  assert.ok(python);
  const { stdout } = await promisify(execFile)(
    python,
    [
      "-I",
      "-B",
      "-c",
      `
import sys,time,json
sys.path.insert(0, ${JSON.stringify(vscode.Uri.joinPath(extensionUri, "console").fsPath)})
from clang_toolkit import Client
client=Client(${JSON.stringify(settings.get("server", ""))})
try:
 for root in ${JSON.stringify([external.fsPath, workspace.fsPath])}:
  client.start_project_index(root, compile_commands=root, poll_interval_seconds=3600)
  end=time.monotonic()+60
  while time.monotonic()<end:
   status=client.project_index_status(root)
   if status.state==5:
    assert not status.translation_units_failed, status
    break
   if status.state==7: raise RuntimeError(status.error)
   time.sleep(.1)
  else: raise RuntimeError('Index did not complete: '+root)
 print('CTK_NAVIGATION_PROJECTS_INDEXED')
finally: client.close()
`,
    ],
    { timeout: 150000 },
  );
  assert.match(stdout, /CTK_NAVIGATION_PROJECTS_INDEXED/);
  const document = await vscode.workspace.openTextDocument(source);
  const editor = await vscode.window.showTextDocument(document);
  let links: vscode.DocumentLink[] = [];
  const waitForLinks = async () => {
    const deadline = Date.now() + 60000;
    while (Date.now() < deadline) {
      links =
        (await vscode.commands.executeCommand<vscode.DocumentLink[]>(
          "vscode.executeLinkProvider",
          source,
        )) ?? [];
      if (links.some((link) => document.getText(link.range) === "choose"))
        return;
      await new Promise((done) => setTimeout(done, 100));
    }
    assert.fail("Native reference links did not load automatically");
  };
  await waitForLinks();
  const names = links.map((link) => document.getText(link.range));
  for (const name of [
    "vendor",
    "Item",
    "item",
    "local",
    "choose",
    "method",
    "value",
  ])
    assert.ok(names.includes(name), `Missing reference: ${name}`);
  const choose = links.find(
    (link) => document.getText(link.range) === "choose",
  );
  assert.ok(choose?.target);
  const targets = await vscode.commands.executeCommand<vscode.Location[]>(
    "vscode.executeDefinitionProvider",
    source,
    choose.range.start,
  );
  assert.equal(targets?.length, 1);
  assert.equal(
    await realpath(targets[0]!.uri.fsPath),
    await realpath(definition.fsPath),
  );
  assert.equal(
    targets[0]?.range.start.line,
    1,
    "select the int overload definition, not the double overload or header declaration",
  );
  const args: unknown[] = JSON.parse(decodeURIComponent(choose.target.query));
  await vscode.commands.executeCommand(choose.target.path, ...args);
  assert.equal(
    await realpath(vscode.window.activeTextEditor!.document.uri.fsPath),
    await realpath(definition.fsPath),
  );
  assert.equal(vscode.window.activeTextEditor?.selection.start.line, 1);
  await vscode.window.showTextDocument(document);
  await editor.edit((edit) =>
    edit.insert(new vscode.Position(0, 0), "// unsaved 😀\n"),
  );
  await waitForLinks();
  const shifted = links.find(
    (link) => document.getText(link.range) === "choose",
  );
  assert.equal(shifted?.range.start.line, 2);
  assert.equal(document.isDirty, true);
  console.log(
    "CTK_SYMBOL_NAVIGATION_HOST_PASS: automatic native references, UTF-8 ranges, exact overloads across two projects, clickable external definition and unsaved edits",
  );
}
