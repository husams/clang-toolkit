import { EventEmitter } from "node:events";
import { fileURLToPath } from "node:url";
import {
  type ClientReadableStream,
  Metadata,
  type StatusObject,
  status,
} from "@grpc/grpc-js";
import { loadSync } from "@grpc/proto-loader";
import { describe, expect, it } from "vitest";
import { matchStreamEventSchema } from "../src/boundary.js";
import type { MatchStreamEvent__Output } from "../src/generated/ctk/match/v1/MatchStreamEvent.js";
import {
  DiskMatchRowStore,
  type MatchRowStore,
} from "../src/match-row-store.js";
import { consumeMatchStream } from "../src/match-stream.js";
import type { SemanticRow } from "../src/semantic-types.js";

class ReadableStub extends EventEmitter {
  private readonly pending: (() => void)[] = [];
  private paused = false;
  canceled = false;

  send(event: MatchStreamEvent__Output): void {
    this.pending.push(() => this.emit("data", event));
    this.flush();
  }

  emitNow(event: "data" | "end", value?: MatchStreamEvent__Output): void {
    if (event === "data") this.emit(event, value);
    else this.emit(event);
  }

  end(): void {
    this.pending.push(() => this.emit("end"));
    this.flush();
  }

  finish(value: StatusObject): void {
    this.pending.push(() => this.emit("status", value));
    this.flush();
  }

  finishNow(value: StatusObject): void {
    this.emit("status", value);
  }

  pause(): this {
    this.paused = true;
    return this;
  }

  resume(): this {
    this.paused = false;
    this.flush();
    return this;
  }

  cancel(): void {
    this.canceled = true;
  }

  private flush(): void {
    if (this.paused || this.pending.length === 0) return;
    const next = this.pending.shift();
    if (next)
      queueMicrotask(() => {
        next();
        this.flush();
      });
  }
}

const completion = {
  event: "completed",
  completed: {
    sessionId: "31f15cce-29b0-4b05-bbf9-5cae8ddcb1ca",
    resultRevision: "1",
    rowCount: "1",
    expiresAt: { seconds: "1791390000", nanos: 0 },
  },
} satisfies MatchStreamEvent__Output;

const row = {
  event: "row",
  row: { bindings: {} },
} satisfies MatchStreamEvent__Output;
const ok: StatusObject = {
  code: status.OK,
  details: "",
  metadata: new Metadata(),
};

function store(): DiskMatchRowStore {
  return DiskMatchRowStore.create();
}

describe("retained Match streaming", () => {
  it("decodes and retains base specifiers with copied binding metadata", async () => {
    const schemaDirectory = fileURLToPath(
      new URL("../schema/", import.meta.url),
    );
    const definitions = loadSync(
      [`${schemaDirectory}match/v1/match_stream.proto`],
      {
        includeDirs: [schemaDirectory],
        longs: String,
        enums: String,
        defaults: true,
        oneofs: true,
      },
    );
    const eventDefinition = definitions["ctk.match.v1.MatchStreamEvent"];
    if (
      eventDefinition === undefined ||
      !("format" in eventDefinition) ||
      eventDefinition.format !== "Protocol Buffer 3 DescriptorProto"
    )
      throw new Error("MatchStreamEvent descriptor is missing");

    const input = {
      event: "row",
      row: {
        bindings: {
          base: {
            baseSpecifier: {
              type: {},
              access: "ACCESS_SPECIFIER_PUBLIC",
              isVirtual: true,
              isPackExpansion: false,
            },
            availability: [],
            supportedScopes: [],
            isComplete: true,
            location: {
              file: "/tmp/example.cc",
              line: 4,
              column: 7,
              valid: true,
              isMacro: false,
            },
            range: {
              expansionBegin: {
                file: "/tmp/example.cc",
                line: 4,
                column: 7,
                valid: true,
                isMacro: false,
              },
              expansionEnd: {
                file: "/tmp/example.cc",
                line: 4,
                column: 18,
                valid: true,
                isMacro: false,
              },
            },
            symbolIdentity: "c:@S@Derived",
            documentation: "Copied declaration documentation",
            callSite: null,
          },
        },
      },
    };
    const encoded = eventDefinition.serialize(input);
    const decoded = eventDefinition.deserialize(
      encoded,
    ) as MatchStreamEvent__Output;
    const parsed = matchStreamEventSchema.parse(decoded);
    const parsedBinding = parsed.row?.bindings.base;
    expect(parsedBinding?.value).toBe("baseSpecifier");
    expect(parsedBinding).toMatchObject({
      baseSpecifier: {
        access: "ACCESS_SPECIFIER_PUBLIC",
        isVirtual: true,
        isPackExpansion: false,
      },
      availability: [],
      supportedScopes: [],
      location: { file: "/tmp/example.cc", line: 4, column: 7 },
      range: {
        expansionBegin: { line: 4, column: 7 },
        expansionEnd: { line: 4, column: 18 },
      },
      symbolIdentity: "c:@S@Derived",
      documentation: "Copied declaration documentation",
      callSite: null,
    });

    const stream = new ReadableStub();
    const rows = store();
    const task = consumeMatchStream(
      stream as unknown as ClientReadableStream<MatchStreamEvent__Output>,
      rows,
      () => {},
    );
    stream.send(decoded);
    stream.send(completion);
    stream.end();
    stream.finish(ok);
    await task;
    expect(rows.get(0)?.bindings.base).toMatchObject({
      baseSpecifier: { isVirtual: true },
      location: { file: "/tmp/example.cc" },
      symbolIdentity: "c:@S@Derived",
      documentation: "Copied declaration documentation",
      supportedScopes: [],
    });
    rows.discard();
  });

  it("spools rows before awaiting progressive callbacks and verifies completion", async () => {
    const stream = new ReadableStub();
    const rows = store();
    const seen: number[] = [];
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let completionValue: unknown;
    const task = consumeMatchStream(
      stream as unknown as ClientReadableStream<MatchStreamEvent__Output>,
      rows,
      (value) => {
        completionValue = value;
      },
      async (_value, index) => {
        seen.push(index);
        await gate;
      },
    );
    stream.send(row);
    stream.send(completion);
    stream.end();
    stream.finish(ok);
    await new Promise((resolve) => setImmediate(resolve));
    expect(seen).toEqual([0]);
    expect(rows.length).toBe(1);
    release?.();
    await task;
    expect(completionValue).toEqual({
      sessionId: completion.completed?.sessionId,
      resultRevision: "1",
      rowCount: "1",
    });
    expect(rows.get(0)).toEqual({ bindings: {} });
  });

  it("waits for active row callbacks before finalizing terminal status", async () => {
    const stream = new ReadableStub();
    const rows = store();
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const task = consumeMatchStream(
      stream as unknown as ClientReadableStream<MatchStreamEvent__Output>,
      rows,
      () => {},
      async () => gate,
    );
    stream.emitNow("data", row);
    await new Promise((resolve) => setImmediate(resolve));
    stream.emitNow("data", completion);
    stream.emitNow("end");
    stream.finishNow(ok);
    let settled = false;
    void task.then(() => {
      settled = true;
    });
    await new Promise((resolve) => setImmediate(resolve));
    expect(settled).toBe(false);
    release?.();
    await task;
    expect(settled).toBe(true);
    expect(rows.length).toBe(1);
    rows.discard();
  });

  it("rejects missing, duplicate, count-mismatched, or late completion protocol", async () => {
    const cases: MatchStreamEvent__Output[][] = [
      [row],
      [completion, completion],
      [
        row,
        {
          ...completion,
          completed: { ...completion.completed, rowCount: "2" },
        },
      ],
      [completion, row],
    ];
    for (const events of cases) {
      const stream = new ReadableStub();
      const rows = store();
      const task = consumeMatchStream(
        stream as unknown as ClientReadableStream<MatchStreamEvent__Output>,
        rows,
        () => {},
      );
      for (const event of events) stream.send(event);
      stream.end();
      stream.finish(ok);
      await expect(task).rejects.toThrow();
      expect(stream.canceled).toBe(true);
      rows.discard();
    }
  });

  it("rejects non-OK terminal status after completion", async () => {
    const stream = new ReadableStub();
    const rows = store();
    const task = consumeMatchStream(
      stream as unknown as ClientReadableStream<MatchStreamEvent__Output>,
      rows,
      () => {},
    );
    stream.send(completion);
    stream.end();
    stream.finish({
      code: status.CANCELLED,
      details: "cancelled",
      metadata: ok.metadata,
    });
    await expect(task).rejects.toMatchObject({ code: status.CANCELLED });
    rows.discard();
  });

  it("cancels when an awaited onRow callback fails", async () => {
    const stream = new ReadableStub();
    const rows = store();
    const task = consumeMatchStream(
      stream as unknown as ClientReadableStream<MatchStreamEvent__Output>,
      rows,
      () => {},
      async () => {
        throw new Error("callback failed");
      },
    );
    stream.send(row);
    await expect(task).rejects.toThrow("callback failed");
    expect(stream.canceled).toBe(true);
    rows.discard();
  });

  it("keeps aggregate results on disk with a disk-backed random-access index", async () => {
    const rows: MatchRowStore = store();
    for (let index = 0; index < 10_000; index += 1)
      await rows.append({
        bindings: {},
        sourceMatchIndex: String(index),
      } as SemanticRow);
    rows.seal();
    expect(rows.length).toBe(10_000);
    expect(rows.get(0)?.sourceMatchIndex).toBe("0");
    expect(rows.get(9_999)?.sourceMatchIndex).toBe("9999");
    rows.discard();
  });

  it("restores binary fields as independent read copies", async () => {
    const rows = store();
    await rows.append({
      bindings: {
        x: {
          unsupported: {
            bytes: Buffer.from([7, 8]),
            exact: 42n,
            uint64: "18446744073709551615",
          },
        },
      },
    } as unknown as SemanticRow);
    rows.seal();
    const first = rows.get(0) as unknown as {
      bindings: {
        x: {
          unsupported: {
            bytes: Uint8Array;
            exact: bigint;
            uint64: string;
          };
        };
      };
    };
    first.bindings.x.unsupported.bytes[0] = 99;
    const second = rows.get(0) as unknown as {
      bindings: {
        x: {
          unsupported: {
            bytes: Uint8Array;
            exact: bigint;
            uint64: string;
          };
        };
      };
    };
    expect([...second.bindings.x.unsupported.bytes]).toEqual([7, 8]);
    expect(second.bindings.x.unsupported.exact).toBe(42n);
    expect(second.bindings.x.unsupported.uint64).toBe("18446744073709551615");
    expect(Object.isFrozen(second.bindings.x.unsupported)).toBe(true);
    rows.discard();
  });
});
