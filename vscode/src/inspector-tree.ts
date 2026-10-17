import type { AstEntry, AstPage } from "./ast-model.js";
import type { Result } from "./model.js";

interface Page {
  node: Result;
  children?: AstEntry[];
}
export interface InspectorRow {
  node: Result;
  depth: number;
  parent: string | undefined;
  expanded: boolean;
  loaded: boolean;
  expandable: boolean;
  selected: boolean;
}

export class InspectorTree {
  private root: string | undefined;
  private selected: string | undefined;
  private pages = new Map<string, Page>();
  private parents = new Map<string, string>();
  private expanded = new Set<string>();
  reset(): void {
    this.root = undefined;
    this.selected = undefined;
    this.pages.clear();
    this.parents.clear();
    this.expanded.clear();
  }
  private remember(page: Page): void {
    this.pages.set(page.node.id, page);
    for (const node of page.children ?? []) {
      this.parents.set(node.id, page.node.id);
      const known = this.pages.get(node.id);
      this.pages.set(node.id, known ? { ...known, node } : { node });
    }
  }
  apply(page: Page, path?: AstPage[], select = true): void {
    const root = path?.[0]?.node.id;
    if (
      (root && root !== this.root) ||
      (!path && !this.pages.has(page.node.id))
    ) {
      this.reset();
      this.root = root ?? page.node.id;
    }
    for (const ancestor of path ?? []) {
      this.remember(ancestor);
      this.expanded.add(ancestor.node.id);
    }
    this.remember(page);
    if (select) {
      this.selected = page.node.id;
      this.expanded.add(page.node.id);
      let parent = this.parents.get(page.node.id);
      const seen = new Set<string>();
      while (parent && !seen.has(parent)) {
        seen.add(parent);
        this.expanded.add(parent);
        parent = this.parents.get(parent);
      }
    }
  }
  node(id: string): Result | undefined {
    return this.pages.get(id)?.node;
  }
  loaded(id: string): boolean {
    return this.pages.get(id)?.children !== undefined;
  }
  expand(id: string, expanded: boolean): void {
    if (expanded) this.expanded.add(id);
    else this.expanded.delete(id);
  }
  clearSelection(): void {
    this.selected = undefined;
  }
  select(id: string): void {
    if (this.pages.has(id)) this.selected = id;
  }
  rows(includeCollapsed = false): InspectorRow[] {
    const rows: InspectorRow[] = [],
      seen = new Set<string>();
    const visit = (id: string, depth: number, parent?: string) => {
      const page = this.pages.get(id);
      if (!page || seen.has(id)) return;
      seen.add(id);
      const expanded = this.expanded.has(id);
      rows.push({
        node: page.node,
        depth,
        parent,
        expanded,
        loaded: page.children !== undefined,
        expandable: page.children === undefined || page.children.length > 0,
        selected: id === this.selected,
      });
      if (expanded || includeCollapsed)
        for (const child of page.children ?? []) visit(child.id, depth + 1, id);
    };
    if (this.root) visit(this.root, 0);
    return rows;
  }
}
