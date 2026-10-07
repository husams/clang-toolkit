import { z } from "zod";

const unsigned = z.string().regex(/^(0|[1-9][0-9]*)$/);
const revision = unsigned.refine((value) => BigInt(value) > 0n);
const session = z.string().uuid();
const semantic = z.looseObject({});
const binding = z.looseObject({
  node: semantic.nullish(),
  qualifiedType: semantic.nullish(),
  unsupported: semantic.nullish(),
  availability: z.array(semantic),
  supportedScopes: z.array(z.string()),
  isComplete: z.boolean().optional(),
});
export const rowSchema = z.looseObject({
  bindings: z.record(z.string(), binding),
  sourceMatchIndex: unsigned.optional(),
});
export const parseResponseSchema = z.looseObject({
  sessionId: session,
  resultRevision: revision,
});
export const matchResponseSchema = parseResponseSchema.extend({
  results: z.array(rowSchema),
});
export const scriptResponseSchema = z.looseObject({
  executedSteps: z.number().int().nonnegative(),
  emissions: z.array(
    z.looseObject({
      name: z.string(),
      value: z
        .looseObject({
          value: z.enum([
            "scalar",
            "matches",
            "traversal",
            "cfg",
            "callGraph",
            "tree",
          ]),
          scalar: z.looseObject({}).nullish(),
          matches: z.looseObject({ rows: z.array(rowSchema) }).nullish(),
          traversal: semantic.nullish(),
          cfg: semantic.nullish(),
          callGraph: semantic.nullish(),
          tree: semantic.nullish(),
        })
        .refine(
          (value) =>
            value[value.value] !== null && value[value.value] !== undefined,
        ),
    }),
  ),
});
export const fileOptionsSchema = z.object({
  workingDirectory: z.string().min(1).optional(),
  compileArguments: z.array(z.string().min(1)).optional(),
});
export const matchOptionsSchema = fileOptionsSchema.extend({
  traversal: z.enum(["asIs", "spelled"]).optional(),
  scope: z.enum(["subtree", "rootOnly"]).optional(),
});
