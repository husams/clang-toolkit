import type { ActionNode } from "./actions.js";

export interface ActionMatch<T extends ActionNode> {
  id: string;
  anchor: T;
  bindings: T[];
}

export interface ActionFile<T extends ActionNode> {
  file: string;
  matches: ActionMatch<T>[];
}

// Group complete match rows first: a binding in another file must stay with
// its caller/root, and repeated nodes in distinct matches must remain distinct.
export function groupActionMatches<T extends ActionNode>(
  results: readonly T[],
): ActionFile<T>[] {
  const rows = new Map<string, ActionMatch<T>>();
  for (const result of results) {
    let row = rows.get(result.matchId);
    if (!row) {
      row = { id: result.matchId, anchor: result, bindings: [] };
      rows.set(result.matchId, row);
    }
    row.bindings.push(result);
    if (result.binding === "root") row.anchor = result;
  }
  const files = new Map<string, ActionFile<T>>();
  for (const row of rows.values()) {
    let file = files.get(row.anchor.file);
    if (!file) {
      file = { file: row.anchor.file, matches: [] };
      files.set(file.file, file);
    }
    file.matches.push(row);
  }
  return [...files.values()];
}
