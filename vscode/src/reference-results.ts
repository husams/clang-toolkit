import { basename, relative } from "node:path";
import * as vscode from "vscode";

export interface Occurrence {
  project: string;
  file: string;
  line: number;
  column: number;
  preview: string;
  length: number;
}
type Entry = { label: string; children: Entry[]; occurrence?: Occurrence };

export class ReferenceResults
  implements vscode.TreeDataProvider<Entry>, vscode.Disposable
{
  private entries: Entry[] = [];
  private readonly changed = new vscode.EventEmitter<Entry | undefined>();
  readonly onDidChangeTreeData = this.changed.event;
  private readonly view = vscode.window.createTreeView("ctk.references", {
    treeDataProvider: this,
    showCollapseAll: true,
  });

  show(
    name: string,
    occurrences: Occurrence[],
    errors: string[],
    coverage?: { completed: number; total: number; projects: number },
  ): void {
    const projects = new Map<string, Map<string, Occurrence[]>>();
    for (const occurrence of occurrences) {
      const files =
        projects.get(occurrence.project) ?? new Map<string, Occurrence[]>();
      projects.set(occurrence.project, files);
      const rows = files.get(occurrence.file) ?? [];
      files.set(occurrence.file, rows);
      rows.push(occurrence);
    }
    this.entries = [...projects].map(([project, files]) => ({
      label: `${basename(project)} — ${project}`,
      children: [...files].map(([file, rows]) => ({
        label: `${relative(project, file)} (${rows.length})`,
        children: rows.map((occurrence) => ({
          label: `${occurrence.line}:${occurrence.column}  ${occurrence.preview.trim()}`,
          children: [],
          occurrence,
        })),
      })),
    }));
    if (errors.length)
      this.entries.push({
        label: `${errors.length} errors — results are incomplete`,
        children: errors.map((label) => ({ label, children: [] })),
      });
    this.view.title = `References: ${name}`;
    this.view.message = `${occurrences.length} locations${coverage ? ` · ${coverage.completed}/${coverage.total} files · ${coverage.projects} projects` : ""}${errors.length ? " · incomplete" : ""}`;
    this.changed.fire(undefined);
    void vscode.commands.executeCommand(
      "setContext",
      "ctk.hasReferences",
      true,
    );
    void vscode.commands.executeCommand("ctk.references.focus");
  }
  getChildren(entry?: Entry): Entry[] {
    return entry?.children ?? this.entries;
  }
  getTreeItem(entry: Entry): vscode.TreeItem {
    const item = new vscode.TreeItem(
      entry.label,
      entry.children.length
        ? vscode.TreeItemCollapsibleState.Expanded
        : vscode.TreeItemCollapsibleState.None,
    );
    if (entry.occurrence) {
      item.resourceUri = vscode.Uri.file(entry.occurrence.file);
      item.tooltip = `${entry.occurrence.file}:${entry.occurrence.line}:${entry.occurrence.column}\n${entry.occurrence.preview}`;
      item.command = {
        command: "ctk.openReference",
        title: "Open reference",
        arguments: [entry.occurrence],
      };
    }
    return item;
  }
  dispose(): void {
    this.view.dispose();
    this.changed.dispose();
  }
}
