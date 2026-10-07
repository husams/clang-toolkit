import type { DeepReadonly } from "./semantic-types.js";

function freeze(value: unknown): void {
  if (value === null || typeof value !== "object" || ArrayBuffer.isView(value))
    return;
  for (const child of Object.values(value)) freeze(child);
  Object.freeze(value);
}

// Byte buffers are copied too; modifying a returned buffer cannot alter a handle.
export function snapshot<T>(value: T): DeepReadonly<T> {
  const copy = structuredClone(value);
  freeze(copy);
  return copy as DeepReadonly<T>;
}
