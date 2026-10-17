import { stripVTControlCharacters } from "node:util";
import { z } from "zod";

const compilerDiagnostic = z.object({
  file: z.string().min(1),
  line: z.number().int().positive().safe(),
  column: z.number().int().positive().safe(),
  message: z.string().min(1),
});
export type CompilerDiagnostic = z.infer<typeof compilerDiagnostic>;

// The native parser returns Clang's file:line:byte-column diagnostics inside
// its RPC error. Keep compiler locations; never invent a location for RPC errors.
export function compilerDiagnostics(error: string): CompilerDiagnostic[] {
  const diagnostics = new Map<string, CompilerDiagnostic>();
  for (const line of stripVTControlCharacters(error).split(/\r?\n/)) {
    const match = /^(.+?):(\d+):(\d+):\s*(?:fatal error|error):\s*(.+)$/.exec(
      line.trim(),
    );
    if (!match) continue;
    const parsed = compilerDiagnostic.safeParse({
      file: match[1],
      line: Number(match[2]),
      column: Number(match[3]),
      message: match[4],
    });
    if (parsed.success)
      diagnostics.set(JSON.stringify(parsed.data), parsed.data);
  }
  return [...diagnostics.values()];
}
