import { z } from "zod";

export const graphKindSchema = z.enum(["callgraph", "cfg"]);
export type GraphKind = z.infer<typeof graphKindSchema>;
export const graphSchema = z
  .object({
    key: z.string().min(1),
    kind: graphKindSchema,
    root: z.string().min(1),
    name: z.string(),
    complete: z.boolean(),
    warnings: z.array(z.string()),
    nodes: z.array(
      z.object({
        id: z.string().min(1),
        name: z.string(),
        detail: z.string().default(""),
        file: z.string(),
        line: z.number().int().positive(),
        column: z.number().int().positive(),
      }),
    ),
    edges: z.array(
      z.object({
        id: z.string(),
        from: z.string(),
        to: z.string(),
        label: z.string().default(""),
      }),
    ),
  })
  .superRefine((graph, context) => {
    const ids = new Set(graph.nodes.map((node) => node.id));
    if (
      ids.size !== graph.nodes.length ||
      !ids.has(graph.root) ||
      graph.edges.some((edge) => !ids.has(edge.from) || !ids.has(edge.to))
    )
      context.addIssue({
        code: "custom",
        message: "Invalid graph identity or edge endpoint",
      });
  });
export type AnalysisGraph = z.infer<typeof graphSchema>;
export type GraphLoad = (kind: GraphKind, id: string) => Promise<AnalysisGraph>;
