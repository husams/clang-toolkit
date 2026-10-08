import {
  closeSync,
  existsSync,
  fsyncSync,
  mkdtempSync,
  openSync,
  readSync,
  rmSync,
  writeSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { snapshot } from "./immutable.js";
import type { SemanticRow } from "./semantic-types.js";

const BYTE_TAG = "__ctk_match_spool_bytes__";
const BIGINT_TAG = "__ctk_match_spool_bigint__";

function encode(value: unknown): string {
  const normalize = (item: unknown): unknown => {
    if (typeof item === "bigint") return { [BIGINT_TAG]: item.toString() };
    if (Buffer.isBuffer(item)) return { [BYTE_TAG]: item.toString("base64") };
    if (ArrayBuffer.isView(item)) {
      const bytes = Buffer.from(item.buffer, item.byteOffset, item.byteLength);
      return { [BYTE_TAG]: bytes.toString("base64") };
    }
    if (Array.isArray(item)) return item.map(normalize);
    if (item !== null && typeof item === "object")
      return Object.fromEntries(
        Object.entries(item).map(([key, child]) => [key, normalize(child)]),
      );
    return item;
  };
  return JSON.stringify(normalize(value));
}

function decode(value: string): SemanticRow {
  return JSON.parse(value, (_key, item: unknown) => {
    if (item === null || typeof item !== "object") return item;
    const record = item as Record<string, unknown>;
    if (
      Object.keys(record).length === 1 &&
      typeof record[BYTE_TAG] === "string"
    )
      return new Uint8Array(Buffer.from(record[BYTE_TAG], "base64"));
    if (
      Object.keys(record).length === 1 &&
      typeof record[BIGINT_TAG] === "string"
    )
      return BigInt(record[BIGINT_TAG]);
    return item;
  }) as SemanticRow;
}

function writeAll(fd: number, bytes: Buffer, position: number): void {
  let written = 0;
  while (written < bytes.length)
    written += writeSync(
      fd,
      bytes,
      written,
      bytes.length - written,
      position + written,
    );
}

export interface MatchRowStore {
  readonly length: number;
  get(index: number): SemanticRow;
  append(row: SemanticRow): Promise<void>;
  seal(): void;
  discard(): void;
}

export class MemoryMatchRowStore implements MatchRowStore {
  private readonly rows: SemanticRow[];
  private sealed = false;

  constructor(rows: readonly SemanticRow[] = []) {
    this.rows = rows.map((row) => snapshot(row));
  }

  get length(): number {
    return this.rows.length;
  }

  get(index: number): SemanticRow {
    const row = this.rows[index];
    if (!row) throw new RangeError("matched row is out of range");
    return snapshot(row);
  }

  async append(row: SemanticRow): Promise<void> {
    if (this.sealed) throw new Error("match row store is sealed");
    this.rows.push(snapshot(row));
  }

  seal(): void {
    this.sealed = true;
  }

  discard(): void {
    this.rows.length = 0;
    this.sealed = true;
  }
}

/** Stores stream rows and their random-access offsets without retaining rows in RAM. */
export class DiskMatchRowStore implements MatchRowStore {
  private readonly directory: string;
  private readonly rowsFd: number;
  private readonly offsetsFd: number;
  private rowsBytes = 0;
  private count = 0;
  private sealed = false;
  private discarded = false;

  private constructor() {
    this.directory = mkdtempSync(join(tmpdir(), "clang-toolkit-match-"));
    let rowsFd = -1;
    let offsetsFd = -1;
    try {
      rowsFd = openSync(join(this.directory, "rows.jsonl"), "w+");
      offsetsFd = openSync(join(this.directory, "offsets.bin"), "w+");
    } catch (error) {
      if (offsetsFd !== -1) closeSync(offsetsFd);
      if (rowsFd !== -1) closeSync(rowsFd);
      rmSync(this.directory, { recursive: true, force: true });
      throw error;
    }
    this.rowsFd = rowsFd;
    this.offsetsFd = offsetsFd;
  }

  static create(): DiskMatchRowStore {
    return new DiskMatchRowStore();
  }

  get length(): number {
    return this.count;
  }

  get(index: number): SemanticRow {
    if (!Number.isSafeInteger(index) || index < 0 || index >= this.count)
      throw new RangeError("matched row is out of range");
    const offset = Buffer.allocUnsafe(8);
    const offsetRead = readSync(this.offsetsFd, offset, 0, 8, index * 8);
    if (offsetRead !== 8) throw new Error("match row index is truncated");
    const start = Number(offset.readBigUInt64LE(0));
    let end = this.rowsBytes;
    if (index + 1 < this.count) {
      const next = Buffer.allocUnsafe(8);
      const nextRead = readSync(this.offsetsFd, next, 0, 8, (index + 1) * 8);
      if (nextRead !== 8) throw new Error("match row index is truncated");
      end = Number(next.readBigUInt64LE(0));
    }
    const line = Buffer.allocUnsafe(end - start);
    const lineRead = readSync(this.rowsFd, line, 0, line.length, start);
    if (lineRead !== line.length) throw new Error("match row is truncated");
    const json = line.toString("utf8").replace(/\n$/, "");
    return snapshot(decode(json));
  }

  async append(row: SemanticRow): Promise<void> {
    if (this.sealed || this.discarded)
      throw new Error("match row store is not writable");
    const line = Buffer.from(`${encode(row)}\n`, "utf8");
    const offset = Buffer.allocUnsafe(8);
    offset.writeBigUInt64LE(BigInt(this.rowsBytes));
    writeAll(this.offsetsFd, offset, this.count * 8);
    writeAll(this.rowsFd, line, this.rowsBytes);
    this.rowsBytes += line.length;
    this.count += 1;
  }

  seal(): void {
    if (this.discarded) throw new Error("match row store was discarded");
    if (this.sealed) return;
    fsyncSync(this.rowsFd);
    fsyncSync(this.offsetsFd);
    this.sealed = true;
  }

  discard(): void {
    if (this.discarded) return;
    this.discarded = true;
    const failures: unknown[] = [];
    for (const fd of [this.rowsFd, this.offsetsFd]) {
      try {
        closeSync(fd);
      } catch (error) {
        failures.push(error);
      }
    }
    try {
      rmSync(this.directory, { recursive: true, force: true });
    } catch (error) {
      failures.push(error);
    }
    this.count = 0;
    this.rowsBytes = 0;
    if (failures.length)
      throw new AggregateError(failures, "failed to discard match row spool");
  }

  cleanup(): void {
    if (this.discarded) return;
    this.discarded = true;
    try {
      closeSync(this.rowsFd);
    } catch (error) {
      process.emitWarning(String(error), "match row spool cleanup");
    }
    try {
      closeSync(this.offsetsFd);
    } catch (error) {
      process.emitWarning(String(error), "match row spool cleanup");
    }
    try {
      if (existsSync(this.directory))
        rmSync(this.directory, { recursive: true, force: true });
    } catch (error) {
      process.emitWarning(String(error), "match row spool cleanup");
    }
  }
}

const cleanupRegistry = new FinalizationRegistry<DiskMatchRowStore>((store) => {
  store.cleanup();
});

export function retainDiskStoreUntilCollected(
  value: object,
  store: DiskMatchRowStore,
): void {
  cleanupRegistry.register(value, store);
}
