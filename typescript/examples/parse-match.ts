import { Client } from "../src/index.js";

const path = process.argv[2];
if (!path)
  throw new Error(
    "usage: node parse-match.js <server-side C++ file> [config.yaml]",
  );
await using client = await Client.connect({
  ...(process.argv[3] === undefined ? {} : { configPath: process.argv[3] }),
  workingDirectory: process.cwd(),
  compileArguments: ["-std=c++23"],
});
const calls = await client.withTree(path, async (scope) => {
  const functions = await scope.match('functionDecl(isDefinition()).bind("f")');
  return scope.match('callExpr().bind("call")', functions.binding("f"));
});
console.log(JSON.stringify(calls.rows, null, 2));
