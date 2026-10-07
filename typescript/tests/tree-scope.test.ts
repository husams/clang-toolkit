import { describe, expect, it, vi } from "vitest";
import type { Client } from "../src/client.js";
import { handleOwner } from "../src/cursor-handle.js";
import { CursorOwner } from "../src/cursor-owner.js";
import { MatchValue } from "../src/match-value.js";
import { ParsedTree } from "../src/parsed-tree.js";
import { TreeScope } from "../src/tree-scope.js";

function owner(id: string, release = vi.fn(async () => {})): CursorOwner {
  return new CursorOwner({}, id, "1", release, () => true);
}

function pendingCount(scope: TreeScope): number {
  return (scope as unknown as { pending: Set<unknown> }).pending.size;
}

describe("scope failures never publish a retained local cursor", () => {
  it("closes the selected owner when another pending native query fails", async () => {
    const tree = new ParsedTree(owner("tree"), "file.cc", {});
    const selected = new MatchValue(owner("selected"), []);
    let rejectPending: (error: Error) => void = () => {};
    const deferred = new Promise<MatchValue>((_resolve, reject) => {
      rejectPending = reject;
    });
    const sdk = {
      match: vi.fn((query: string) =>
        query === "selected" ? Promise.resolve(selected) : deferred,
      ),
    } as unknown as Client;
    const scope = new TreeScope(sdk, tree);
    await scope.match("selected");
    scope.match("background");
    const finish = scope.finish(selected[handleOwner]);
    rejectPending(new Error("native query failed"));
    await expect(finish).rejects.toThrow(AggregateError);
    expect(pendingCount(scope)).toBe(0);
    expect(selected.closed).toBe(true);
    expect(tree.closed).toBe(true);
  });

  it("retains a background failure that settles before finish starts", async () => {
    const tree = new ParsedTree(owner("tree"), "file.cc", {});
    const selected = new MatchValue(owner("selected"), []);
    let rejectBackground: (error: Error) => void = () => {};
    const background = new Promise<MatchValue>((_resolve, reject) => {
      rejectBackground = reject;
    });
    const sdk = {
      match: vi.fn((query: string) =>
        query === "selected" ? Promise.resolve(selected) : background,
      ),
    } as unknown as Client;
    const scope = new TreeScope(sdk, tree);
    await scope.match("selected");
    scope.match("background");
    rejectBackground(new Error("native query failed"));
    await new Promise<void>((resolve) => setImmediate(resolve));

    await expect(scope.finish(selected[handleOwner])).rejects.toThrow(
      AggregateError,
    );
    expect(pendingCount(scope)).toBe(0);
    expect(selected.closed).toBe(true);
    expect(tree.closed).toBe(true);
  });

  it("releases successful operation promises after finish", async () => {
    const tree = new ParsedTree(owner("tree"), "file.cc", {});
    const selected = new MatchValue(owner("selected"), []);
    const scope = new TreeScope(
      { match: vi.fn(async () => selected) } as unknown as Client,
      tree,
    );
    await scope.match("selected");

    await scope.finish(selected[handleOwner]);

    expect(pendingCount(scope)).toBe(0);
    expect(selected.closed).toBe(false);
    expect(tree.closed).toBe(true);
  });

  it("closes selected local ownership when releasing another local fails", async () => {
    const tree = new ParsedTree(owner("tree"), "file.cc", {});
    const selected = new MatchValue(owner("selected"), []);
    const failingRelease = vi.fn(async () => {
      throw new Error("CloseSession failed");
    });
    const local = new MatchValue(owner("local", failingRelease), []);
    const sdk = {
      match: vi.fn((query: string) =>
        Promise.resolve(query === "local" ? local : selected),
      ),
    } as unknown as Client;
    const scope = new TreeScope(sdk, tree);
    await scope.match("local");
    await scope.match("selected");
    await expect(scope.finish(selected[handleOwner])).rejects.toThrow(
      AggregateError,
    );
    expect(failingRelease).toHaveBeenCalledTimes(1);
    expect(selected.closed).toBe(true);
  });

  it("preserves borrowed owners when scope cleanup fails", async () => {
    const tree = new ParsedTree(
      owner(
        "tree",
        vi.fn(async () => {
          throw new Error("close failed");
        }),
      ),
      "file.cc",
      {},
    );
    const borrowed = new MatchValue(owner("borrowed"), []);
    const scope = new TreeScope({ match: vi.fn() } as unknown as Client, tree);
    await expect(scope.finish(borrowed[handleOwner])).rejects.toThrow(
      AggregateError,
    );
    expect(borrowed.closed).toBe(false);
  });

  it("reports both local and selected close failures", async () => {
    const failure = () =>
      vi.fn(async () => {
        throw new Error("release failed");
      });
    const tree = new ParsedTree(owner("tree", failure()), "file.cc", {});
    const selectedRelease = failure();
    const selected = new MatchValue(owner("selected", selectedRelease), []);
    const scope = new TreeScope(
      { match: vi.fn(async () => selected) } as unknown as Client,
      tree,
    );
    await scope.match("selected");
    try {
      await scope.finish(selected[handleOwner]);
      throw new Error("expected cleanup failure");
    } catch (error) {
      expect(error).toBeInstanceOf(AggregateError);
      expect((error as AggregateError).errors).toHaveLength(2);
    }
    expect(selectedRelease).toHaveBeenCalledTimes(1);
    expect(selected.closed).toBe(true);
  });
});
