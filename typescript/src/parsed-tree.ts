import { CursorHandle } from "./cursor-handle.js";
import type { CursorOwner } from "./cursor-owner.js";
import { snapshot } from "./immutable.js";
import type { FileOptions } from "./options.js";

export class ParsedTree extends CursorHandle {
  readonly file: string;
  readonly options: Readonly<FileOptions>;
  constructor(owner: CursorOwner, file: string, options: FileOptions) {
    super(owner);
    this.file = file;
    this.options = snapshot(options);
  }
}
