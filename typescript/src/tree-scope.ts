import { status } from "@grpc/grpc-js";
import { ClangToolkitError } from "./clang-toolkit-error.js";
import type { Client, MatchTarget } from "./client.js";
import { handleOwner } from "./cursor-handle.js";
import type { CursorOwner } from "./cursor-owner.js";
import type { MatchValue } from "./match-value.js";
import type { MatchOptions } from "./options.js";
import type { ParsedTree } from "./parsed-tree.js";

export class TreeScope {
  private active = true;
  private readonly owners = new Set<CursorOwner>();
  private readonly pending = new Set<Promise<MatchValue>>();

  constructor(
    private readonly client: Client,
    readonly tree: ParsedTree,
  ) {
    this.owners.add(tree[handleOwner]);
  }

  match(
    query: string,
    target: MatchTarget = this.tree,
    options: MatchOptions = {},
  ): Promise<MatchValue> {
    if (!this.active)
      return Promise.reject(
        new ClangToolkitError(
          status.FAILED_PRECONDITION,
          "tree scope is closed",
        ),
      );
    const pending = this.client.match(query, target, options);
    const operation = pending.then((value) => {
      this.owners.add(value[handleOwner]);
      return value;
    });
    // A background call may be intentionally unawaited by the callback. Keep
    // its rejection handled while preserving it in `pending` for finish().
    void operation.catch(() => undefined);
    // Keep settled operations until finish so background failures remain
    // observable even when they reject before the callback returns.
    this.pending.add(operation);
    return operation;
  }

  async finish(keep?: CursorOwner): Promise<void> {
    this.active = false;
    const pending = [...this.pending];
    const operations = await Promise.allSettled(pending);
    this.pending.clear();
    const cleanup = await Promise.allSettled(
      [...this.owners]
        .filter((owner) => owner !== keep)
        .map((owner) => owner.close()),
    );
    const failures = [...operations, ...cleanup].flatMap((result) =>
      result.status === "rejected" ? [result.reason] : [],
    );
    if (failures.length && keep && this.owners.has(keep)) {
      try {
        await keep.close();
      } catch (error) {
        failures.push(error);
      }
    }
    if (failures.length)
      throw new AggregateError(
        failures,
        "tree scope failed to complete or release native handles",
      );
  }
}
