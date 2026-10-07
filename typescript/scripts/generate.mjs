import { execFileSync } from "node:child_process";
import { rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const sdk = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(sdk, "..");
const schema = join(sdk, "schema");
const generated = join(sdk, "src", "generated");
rmSync(schema, { recursive: true, force: true });
rmSync(generated, { recursive: true, force: true });
execFileSync(
  process.env.CTK_PYTHON ?? "python3",
  [join(root, "api", "assemble_ast.py"), `--output=${schema}`],
  { stdio: "inherit" },
);
execFileSync(
  join(sdk, "node_modules", ".bin", "proto-loader-gen-types"),
  [
    "--grpcLib=@grpc/grpc-js",
    "--longs=String",
    "--enums=String",
    "--defaults",
    "--oneofs",
    "--importFileExtension=.js",
    `--outDir=${generated}`,
    `--includeDirs=${schema}`,
    "--",
    join(schema, "match/v1/match_service.proto"),
    join(schema, "analysis/v1/analysis_service.proto"),
  ],
  { stdio: "inherit" },
);
