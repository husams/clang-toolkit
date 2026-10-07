import { BindingSelection } from "./binding-selection.js";
import { CursorHandle } from "./cursor-handle.js";
import type { CursorOwner } from "./cursor-owner.js";
import { snapshot } from "./immutable.js";
import type { SemanticRow } from "./semantic-types.js";

export class MatchRow extends CursorHandle {
  constructor(
    owner: CursorOwner,
    readonly index: number,
    private readonly value: SemanticRow,
  ) {
    super(owner);
  }

  get bindings(): SemanticRow["bindings"] {
    return snapshot(this.value.bindings);
  }
  binding(name: string): BindingSelection {
    return new BindingSelection(this.owner, name, this.index);
  }
}
