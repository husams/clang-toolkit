import { execFileSync } from "node:child_process";
import { cp, mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { build } from "esbuild";

await mkdir("syntaxes", { recursive: true });
const metadata = JSON.parse(
  execFileSync(
    "python3",
    [
      "-c",
      `import ast,json,pathlib
tree=ast.parse(pathlib.Path('../python/clang_toolkit/cli/_matcher_catalog_generated.py').read_text())
for node in tree.body:
 if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == 'MATCHER_METADATA':
  data=ast.literal_eval(node.value)
  print(json.dumps([dict(name=k,category=v[0],summary=v[1],signatures=v[2]) for k,v in data.items()]))
  break
`,
    ],
    { encoding: "utf8" },
  ),
);
await writeFile("media/matchers.json", JSON.stringify(metadata, null, 2));
const words = (category) =>
  metadata
    .filter((entry) => entry.category === category)
    .map((entry) => entry.name)
    .join("|");
await writeFile(
  "syntaxes/ctk.tmLanguage.json",
  JSON.stringify(
    {
      name: "CTK Script",
      scopeName: "source.ctk",
      patterns: [
        { name: "comment.line.double-slash.ctk", begin: "//|#", end: "$" },
        { name: "comment.block.ctk", begin: "/\\*", end: "\\*/" },
        {
          name: "string.quoted.double.ctk",
          begin: '"',
          end: '"',
          patterns: [{ name: "constant.character.escape.ctk", match: "\\\\." }],
        },
        {
          name: "string.quoted.single.ctk",
          begin: "'",
          end: "'",
          patterns: [{ name: "constant.character.escape.ctk", match: "\\\\." }],
        },
        { name: "constant.language.ctk", match: "\\b(true|false|null)\\b" },
        { name: "constant.numeric.ctk", match: "\\b[0-9]+(?:\\.[0-9]+)?\\b" },
        {
          name: "keyword.control.ctk",
          match:
            "\\b(let|emit|yield|in|match|parse|if|else|foreach|while|repeat|until|break|continue|return|import|as|do|done)\\b",
        },
        { name: "variable.parameter.ctk", match: "\\$\\{[A-Z][A-Z0-9_]*\\}" },
        { name: "variable.other.ctk", match: "\\$[A-Za-z_][A-Za-z0-9_]*" },
        {
          name: "entity.name.type.ctk",
          match: `\\b(?:${words("node")})\\b(?=\\s*\\()`,
        },
        {
          name: "support.function.ctk",
          match: `\\b(?:${words("narrowing")}|${words("traversal")})\\b(?=\\s*\\()`,
        },
        {
          name: "entity.name.function.ctk",
          match: "\\b[A-Za-z_][A-Za-z0-9_]*(?=\\s*\\()",
        },
      ],
    },
    null,
    2,
  ),
);

await mkdir("dist", { recursive: true });
await mkdir("artifacts", { recursive: true });
await cp("../typescript/schema", "schema", { recursive: true });
const common = {
  bundle: true,
  platform: "node",
  target: "node22",
  sourcemap: true,
  external: ["vscode"],
};
await build({
  ...common,
  entryPoints: ["src/extension.ts", "src/worker.ts"],
  outdir: "dist",
  format: "esm",
  banner: {
    js: 'import { createRequire as __ctkCreateRequire } from "node:module"; const require = __ctkCreateRequire(import.meta.url);',
  },
});
await build({
  ...common,
  entryPoints: ["tests/extension-host.ts"],
  outfile: "dist/extension-tests.cjs",
  format: "cjs",
});
const require = createRequire(import.meta.url);
const { dependencies } = require("../package.json");
await writeFile(
  "dist/dependencies.json",
  JSON.stringify(dependencies, null, 2),
);
