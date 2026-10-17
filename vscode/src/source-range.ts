import { z } from "zod";
import { astBinding } from "./ast-model.js";
import type { Result } from "./model.js";

const pointSchema = z.object({
  valid: z.literal(true),
  file: z.string().min(1),
  line: z.number().int().positive(),
  column: z.number().int().positive(),
  offset: z
    .union([z.number(), z.string().regex(/^\d+$/).transform(Number)])
    .pipe(z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER))
    .optional(),
});
type SourcePoint = z.infer<typeof pointSchema>;
export interface SourceTarget {
  file: string;
  begin: SourcePoint;
  end?: SourcePoint;
}

export function sourceTarget(result: Result): SourceTarget | undefined {
  const binding = astBinding(result);
  const parsed = z
    .object({
      expansionBegin: z.unknown().optional(),
      expansionEndExclusive: z.unknown().optional(),
    })
    .safeParse(binding.range);
  const begin = pointSchema.safeParse(parsed.data?.expansionBegin);
  if (begin.success) {
    const end = pointSchema.safeParse(parsed.data?.expansionEndExclusive);
    return {
      file: begin.data.file,
      begin: begin.data,
      ...(end.success && end.data.file === begin.data.file
        ? { end: end.data }
        : {}),
    };
  }
  const location = pointSchema.safeParse(binding.location);
  if (location.success)
    return { file: location.data.file, begin: location.data };
  if ("locationValid" in result && result.locationValid === false) return;
  const fallback = pointSchema.safeParse({ ...result, valid: true });
  if (fallback.success)
    return { file: fallback.data.file, begin: fallback.data };
}

// Clang counts UTF-8 bytes; VS Code selections count UTF-16 code units.
function offset(point: SourcePoint, bytes: Buffer): number | undefined {
  let index: number = point.offset ?? 0;
  if (point.offset === undefined) {
    for (let line = 1; line < point.line; line++) {
      const newline = bytes.indexOf(10, index);
      if (newline < 0) return;
      index = newline + 1;
    }
    const newline = bytes.indexOf(10, index);
    let end = newline < 0 ? bytes.length : newline;
    if (bytes[end - 1] === 13) end--;
    index += point.column - 1;
    if (index > end) return;
  }
  if (index > bytes.length || ((bytes[index] ?? 0) & 0xc0) === 0x80) return;
  return bytes.subarray(0, index).toString("utf8").length;
}

export function sourceOffsets(
  target: SourceTarget,
  text: string,
): { start: number; end: number } | undefined {
  const bytes = Buffer.from(text, "utf8");
  const start = offset(target.begin, bytes);
  if (start === undefined) return;
  const end = target.end ? offset(target.end, bytes) : undefined;
  // Never guess the length of Clang's legacy end-token coordinate.
  return { start, end: end !== undefined && end >= start ? end : start };
}
