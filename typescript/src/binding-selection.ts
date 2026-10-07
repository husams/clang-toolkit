import { z } from "zod";
import { CursorHandle } from "./cursor-handle.js";
import type { CursorOwner } from "./cursor-owner.js";

export class BindingSelection extends CursorHandle {
  readonly name: string;
  readonly matchIndex: number | undefined;

  constructor(owner: CursorOwner, name: string, matchIndex?: number) {
    super(owner);
    this.name = z.string().min(1).parse(name);
    this.matchIndex =
      matchIndex === undefined
        ? undefined
        : z.number().int().nonnegative().safe().parse(matchIndex);
    Object.freeze(this);
  }
}
