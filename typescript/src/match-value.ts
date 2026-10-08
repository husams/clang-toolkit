import { status } from "@grpc/grpc-js";
import { BindingSelection } from "./binding-selection.js";
import { ClangToolkitError } from "./clang-toolkit-error.js";
import { CursorHandle } from "./cursor-handle.js";
import type { CursorOwner } from "./cursor-owner.js";
import { snapshot } from "./immutable.js";
import { MatchRow } from "./match-row.js";
import {
  DiskMatchRowStore,
  type MatchRowStore,
  MemoryMatchRowStore,
  retainDiskStoreUntilCollected,
} from "./match-row-store.js";
import type { SemanticRow } from "./semantic-types.js";

export class MatchValue extends CursorHandle {
  private readonly values: MatchRowStore;

  constructor(
    owner: CursorOwner,
    rows: readonly SemanticRow[] | MatchRowStore,
  ) {
    super(owner);
    this.values = Array.isArray(rows)
      ? new MemoryMatchRowStore(rows)
      : (rows as MatchRowStore);
    if (this.values instanceof DiskMatchRowStore)
      retainDiskStoreUntilCollected(this, this.values);
  }

  get rows(): readonly SemanticRow[] {
    return snapshot(Array.from(this.iterateRows()));
  }
  get length(): number {
    return this.values.length;
  }
  *iterateRows(): IterableIterator<SemanticRow> {
    for (let index = 0; index < this.length; index += 1)
      yield this.values.get(index);
  }
  [Symbol.iterator](): IterableIterator<SemanticRow> {
    return this.iterateRows();
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
    return new MatchRow(this.owner, index, this.values.get(index));
  }
}
