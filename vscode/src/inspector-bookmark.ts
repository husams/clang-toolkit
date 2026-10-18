import { astBinding, field, nativeKind } from "./ast-facts.js";
import type { AstEntry, AstSemantics } from "./ast-model.js";
import { astDisplay } from "./ast-model.js";
import { InspectorTree } from "./inspector-tree.js";
import type { Result } from "./model.js";
import { sourceOffsets, sourceTarget } from "./source-range.js";

interface Anchor {
  kind: string;
  name: string;
  file: string;
  symbol: unknown;
  signature: string;
  definition: unknown;
  implicit: unknown;
  code?: string;
  span?: {
    start: number;
    end: number;
    removed?: boolean;
    deletedOffset?: number;
    deletedLength?: number;
  };
  byteStart?: number;
  nativeSpan?: { start: number; end: number };
}
export interface InspectorBookmark {
  anchor: Anchor;
  expanded: boolean;
  selected: boolean;
  children: InspectorBookmark[];
}
export interface SourceEdit {
  rangeOffset: number;
  rangeLength: number;
  text: string;
}
export interface BookmarkPage {
  node: Result;
  children: AstEntry[];
  semantics?: AstSemantics | undefined;
}
function anchor(node: Result, text: string, file: string): Anchor {
  const binding = astBinding(node),
    target = sourceTarget(node);
  const span =
    target?.file === file && target.end
      ? sourceOffsets(target, text)
      : undefined;
  return {
    kind: nativeKind(node) || node.kind,
    name: node.name,
    file: node.file,
    symbol: binding.symbolIdentity,
    signature: astDisplay(node).signature,
    definition:
      field(binding.node, "isThisDeclarationADefinition") ??
      field(binding.node, "isCompleteDefinition"),
    implicit: field(binding.node, "isImplicit"),
    ...(span
      ? { span, code: text.slice(span.start, span.end).slice(0, 8192) }
      : {}),
    ...(target?.begin.offset !== undefined
      ? { byteStart: target.begin.offset }
      : {}),
    ...(target?.file !== file &&
    target?.begin.offset !== undefined &&
    target.end?.offset !== undefined
      ? { nativeSpan: { start: target.begin.offset, end: target.end.offset } }
      : {}),
  };
}
export function bookmarkTree(
  tree: InspectorTree,
  selectedId: string | undefined,
  text: string,
  file: string,
): InspectorBookmark | undefined {
  const branches = new Map<string, InspectorBookmark>();
  const rows = tree.rows(true);
  for (const row of rows)
    branches.set(row.node.id, {
      anchor: anchor(row.node, text, file),
      expanded: row.expanded,
      selected: row.node.id === selectedId,
      children: [],
    });
  for (const row of rows) {
    const branch = branches.get(row.node.id);
    if (row.parent && branch) branches.get(row.parent)?.children.push(branch);
  }
  const prune = (branch: InspectorBookmark): boolean => {
    branch.children = branch.children.filter(prune);
    return branch.expanded || branch.selected || branch.children.length > 0;
  };
  const root = rows[0] && branches.get(rows[0].node.id);
  if (root) prune(root);
  return root;
}
export function rebaseBookmark(
  bookmark: InspectorBookmark,
  edits: readonly SourceEdit[],
): void {
  const ordered = [...edits].sort((a, b) => b.rangeOffset - a.rangeOffset);
  const visit = (branch: InspectorBookmark) => {
    const span = branch.anchor.span;
    if (span)
      for (const edit of ordered) {
        const from = edit.rangeOffset,
          to = from + edit.rangeLength;
        if (span.removed) {
          const relative = span.deletedOffset ?? 0,
            code = branch.anchor.code;
          if (
            !edit.rangeLength &&
            from === span.start &&
            code &&
            edit.text.slice(relative, relative + code.length) === code
          ) {
            span.start = from + relative;
            span.end = span.start + (span.deletedLength ?? code.length);
            delete span.removed;
            delete span.deletedOffset;
            delete span.deletedLength;
          } else {
            span.start =
              span.start >= to
                ? span.start + edit.text.length - edit.rangeLength
                : span.start >= from
                  ? from
                  : span.start;
            span.end = span.start;
          }
          continue;
        }
        if (
          edit.rangeLength &&
          !edit.text &&
          from <= span.start &&
          to >= span.end &&
          span.end > span.start
        ) {
          span.removed = true;
          span.deletedOffset = span.start - from;
          span.deletedLength = span.end - span.start;
          span.start = span.end = from;
          continue;
        }
        const delta = edit.text.length - edit.rangeLength;
        const start = span.start,
          end = span.end;
        span.start = start >= to ? start + delta : start >= from ? from : start;
        span.end =
          end > to || (edit.rangeLength > 0 && end === to)
            ? end + delta
            : end > from
              ? from + edit.text.length
              : end;
        if (start === end) span.end = span.start;
      }
    for (const child of branch.children) visit(child);
  };
  visit(bookmark);
}
const unique = <T>(items: T[]): T | undefined =>
  items.length === 1 ? items[0] : undefined;
export function matchingNode(
  saved: InspectorBookmark,
  nodes: Result[],
  text: string,
  file: string,
): Result | undefined {
  const old = saved.anchor;
  if (old.span?.removed) return;
  const candidates = nodes
    .map((node) => ({ node, anchor: anchor(node, text, file) }))
    .filter(
      (item) =>
        item.anchor.kind === old.kind &&
        item.anchor.file === old.file &&
        item.anchor.implicit === old.implicit,
    );
  const symbol =
    typeof old.symbol === "string" && old.symbol
      ? candidates.filter(
          (item) =>
            item.anchor.symbol === old.symbol &&
            item.anchor.name === old.name &&
            item.anchor.definition === old.definition,
        )
      : [];
  const named = old.kind.endsWith("Decl")
    ? candidates.filter(
        (item) =>
          item.anchor.name === old.name &&
          item.anchor.signature === old.signature &&
          item.anchor.definition === old.definition,
      )
    : [];
  const oldSpan = old.span ?? old.nativeSpan;
  const positioned = oldSpan
    ? candidates.filter(
        (item) =>
          (item.anchor.span ?? item.anchor.nativeSpan)?.start ===
            oldSpan.start &&
          (item.anchor.span ?? item.anchor.nativeSpan)?.end === oldSpan.end,
      )
    : [];
  const code = old.code?.trim()
    ? candidates.filter((item) => item.anchor.code === old.code)
    : [];
  const structural =
    !oldSpan && !old.code && !old.symbol
      ? candidates.filter((item) => item.anchor.name === old.name)
      : [];
  return (
    unique(symbol) ??
    unique(named) ??
    unique(positioned) ??
    unique(code) ??
    unique(structural)
  )?.node;
}
export function bookmarkHeaders(
  bookmark: InspectorBookmark,
  file: string,
): { file: string; start: number; end: number }[] {
  const headers = new Map<string, number>();
  const visit = (branch: InspectorBookmark) => {
    const { file: path, byteStart } = branch.anchor;
    if (path && path !== file && byteStart !== undefined)
      headers.set(path, byteStart);
    for (const child of branch.children) visit(child);
  };
  visit(bookmark);
  return [...headers].map(([file, start]) => ({ file, start, end: start }));
}
export async function rebuildTree(
  bookmark: InspectorBookmark,
  root: BookmarkPage,
  load: (id: string) => Promise<BookmarkPage>,
  text: string,
  file: string,
  current: () => boolean,
) {
  const tree = new InspectorTree(),
    pages = new Map<string, BookmarkPage>();
  let selected = root;
  const remember = (page: BookmarkPage) => {
    pages.set(page.node.id, page);
    tree.apply(page, undefined, false);
  };
  tree.apply(root);
  pages.set(root.node.id, root);
  const containsSelection = (branch: InspectorBookmark): boolean =>
    branch.selected || branch.children.some(containsSelection);
  const visit = async (
    branch: InspectorBookmark,
    page: BookmarkPage,
  ): Promise<void> => {
    if (!current()) return;
    remember(page);
    if (containsSelection(branch)) selected = page;
    for (const child of branch.children) {
      const match = matchingNode(child, page.children, text, file);
      if (!match || !current()) continue;
      const loaded = await load(match.id);
      if (!current()) return;
      await visit(child, loaded);
    }
    tree.expand(page.node.id, branch.expanded);
  };
  if (bookmark.anchor.kind === (nativeKind(root.node) || root.node.kind))
    await visit(bookmark, root);
  else {
    // An action result may start its outline below the file root. Follow only
    // source-containing or named enclosing declarations to find that subtree.
    const searched = new Set<string>();
    const locate = async (
      page: BookmarkPage,
    ): Promise<BookmarkPage | undefined> => {
      if (!current() || searched.has(page.node.id)) return;
      searched.add(page.node.id);
      const match = matchingNode(bookmark, page.children, text, file);
      if (match) return load(match.id);
      for (const child of page.children) {
        const candidate = anchor(child, text, file),
          span = candidate.span,
          wanted = bookmark.anchor.span;
        if (
          !(
            candidate.name &&
            bookmark.anchor.name.startsWith(`${candidate.name}::`)
          ) &&
          !(
            span &&
            wanted &&
            span.start <= wanted.start &&
            span.end >= wanted.end
          )
        )
          continue;
        if (!current()) return;
        const loaded = await load(child.id);
        remember(loaded);
        tree.expand(loaded.node.id, true);
        const found = await locate(loaded);
        if (found) return found;
      }
    };
    const found = await locate(root);
    if (found && current()) await visit(bookmark, found);
  }
  if (!current()) return;
  tree.select(selected.node.id);
  return { tree, pages, selected };
}
