import { status } from "@grpc/grpc-js";
import { BindingSelection } from "./binding-selection.js";
import { ClangToolkitError } from "./clang-toolkit-error.js";
import { CursorHandle } from "./cursor-handle.js";
import type { CursorOwner } from "./cursor-owner.js";
import { snapshot } from "./immutable.js";
import { MatchRow } from "./match-row.js";
import type { SemanticRow } from "./semantic-types.js";

export class MatchValue extends CursorHandle {
  private readonly values: readonly SemanticRow[];

  constructor(owner: CursorOwner, rows: readonly SemanticRow[]) {
    super(owner);
    this.values = snapshot(rows);
  }

  get rows(): readonly SemanticRow[] {
    return snapshot(this.values);
  }
  get length(): number {
    return this.values.length;
  }
  binding(name: string): BindingSelection {
    return new BindingSelection(this.owner, name);
  }
  row(index: number): MatchRow {
    if (!Number.isSafeInteger(index) || index < 0 || index >= this.length)
      throw new ClangToolkitError(
        status.NOT_FOUND,
        "matched row is out of range",
      );
    const value = this.values[index];
    if (!value)
      throw new ClangToolkitError(
        status.NOT_FOUND,
        "matched row is out of range",
      );
    return new MatchRow(this.owner, index, value);
  }
}
