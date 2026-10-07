import type { CursorOwner } from "./cursor-owner.js";

export const handleOwner = Symbol("clang-toolkit-owner");

export abstract class CursorHandle implements AsyncDisposable {
  constructor(protected readonly owner: CursorOwner) {}

  get [handleOwner](): CursorOwner {
    return this.owner;
  }
  get closed(): boolean {
    return this.owner.closed;
  }
  close(): Promise<void> {
    return this.owner.close();
  }
  [Symbol.asyncDispose](): Promise<void> {
    return this.close();
  }
}
