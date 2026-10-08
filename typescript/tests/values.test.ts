import { status } from "@grpc/grpc-js";
import { describe, expect, it, vi } from "vitest";
import {
  matchResponseSchema,
  parseResponseSchema,
  scriptResponseSchema,
} from "../src/boundary.js";
import { CursorOwner } from "../src/cursor-owner.js";
import type { MatchResult__Output } from "../src/generated/ctk/match/v1/MatchResult.js";
import { DiskMatchRowStore } from "../src/match-row-store.js";
import { MatchValue } from "../src/match-value.js";
import { ParsedTree } from "../src/parsed-tree.js";

const id = "31f15cce-29b0-4b05-bbf9-5cae8ddcb1ca";
describe("immutable values and shared native ownership", () => {
  it("copies semantic rows and keeps indexed binding selectors typed", () => {
    const close = vi.fn(async () => {});
    const owner = new CursorOwner({}, id, "1", close, () => true);
    const rows: MatchResult__Output[] = [
      { bindings: {} },
      { bindings: {}, sourceMatchIndex: "0" },
    ];
    const value = new MatchValue(owner, rows);
    rows.push({ bindings: {} });
    expect(value.length).toBe(2);
    expect(Object.isFrozen(value.rows)).toBe(true);
    expect(Object.isFrozen(value.rows[0]?.bindings)).toBe(true);
    expect(value.binding("f").matchIndex).toBeUndefined();
    expect(value.row(0).binding("f").matchIndex).toBe(0);
    expect(value.rows[1]?.sourceMatchIndex).toBe("0");
    expect(() => value.row(2)).toThrow(
      expect.objectContaining({ code: status.NOT_FOUND }),
    );
  });

  it("aliases share close ownership while independently forked results stay open", async () => {
    const close = vi.fn(async () => {});
    const identity = {};
    const parent = new CursorOwner(identity, id, "1", close, () => true);
    const child = new CursorOwner(
      identity,
      "1a5295b8-e9fb-44f7-9182-5721aa1d66eb",
      "1",
      close,
      () => true,
    );
    const tree = new ParsedTree(parent, "example.cc", {});
    const value = new MatchValue(child, [{ bindings: {} }]);
    await tree.close();
    expect(value.closed).toBe(false);
    await value.row(0).binding("f").close();
    await value.close();
    expect(close).toHaveBeenCalledTimes(2);
    expect(value.closed).toBe(true);
    expect(() => child.assertOpen(identity)).toThrow(
      expect.objectContaining({ code: status.FAILED_PRECONDITION }),
    );
  });

  it("keeps spooled semantic rows readable after native cursor close", async () => {
    const store = DiskMatchRowStore.create();
    await store.append({ bindings: {}, sourceMatchIndex: "0" });
    store.seal();
    const owner = new CursorOwner(
      {},
      id,
      "1",
      async () => {},
      () => true,
    );
    const value = new MatchValue(owner, store);
    const extracted = value.row(0);

    await value.close();

    expect(value.row(0).index).toBe(0);
    expect([...value][0]?.sourceMatchIndex).toBe("0");
    expect(extracted.bindings).toEqual({});
    store.discard();
  });

  it("rejects cross-client owners and invalid selectors before a query", () => {
    const owner = new CursorOwner(
      {},
      id,
      "1",
      async () => {},
      () => true,
    );
    expect(() => owner.assertOpen({})).toThrow(
      expect.objectContaining({ code: status.INVALID_ARGUMENT }),
    );
    expect(() => new MatchValue(owner, []).binding("")).toThrow();
  });
});

describe("external response validation", () => {
  it("rejects missing identities, revisions, collections and script discriminants", () => {
    expect(() =>
      parseResponseSchema.parse({ sessionId: "invalid", resultRevision: "1" }),
    ).toThrow();
    expect(() =>
      parseResponseSchema.parse({ sessionId: id, resultRevision: "0" }),
    ).toThrow();
    expect(() =>
      matchResponseSchema.parse({
        sessionId: id,
        resultRevision: "1",
        results: [{ bindings: { f: {} } }],
      }),
    ).toThrow();
    expect(() =>
      scriptResponseSchema.parse({
        emissions: [{ name: "x", value: { value: "matches", matches: null } }],
        executedSteps: 1,
      }),
    ).toThrow();
    expect(() =>
      scriptResponseSchema.parse({ emissions: [], executedSteps: -1 }),
    ).toThrow();
  });
});
