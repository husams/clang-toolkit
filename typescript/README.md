# @clang-toolkit/sdk

Typed Node.js 22+ ESM client for the native clang-toolkit gRPC services. The package includes the assembled protobuf schemas and generated semantic AST types.

File operations discover `compile_commands.json` on the server automatically.
Set `compilationDatabase` in client options or a `parse`/file `match`/`runScript`
operation to select a JSON file or directory explicitly. Commands supply each
file's flags and working directory; `compileArguments` append overrides.
See [compilation databases](../docs/compilation-database.md) for lookup and cache rules.

```sh
pnpm install
pnpm run generate
pnpm run build
pnpm run check
pnpm test
pnpm run test:integration
```

Integration tests launch `../build/dev/server/ctk-server` on temporary Unix sockets and loopback TCP ports; build that native target first. Local loopback permissions are required.

After building, `node examples/parse-match.mjs /absolute/path/example.cc [config.yaml]` runs the JavaScript example; `examples/parse-match.ts` demonstrates the corresponding typed source.

Put connection settings in `clang-toolkit.yaml`:

```yaml
version: 1
network:
  transport: unix
  unix:
    socket_path: /tmp/ctk.sock
client:
  rpc_timeout_ms: null
```

```ts
import { Client } from "@clang-toolkit/sdk";

await using client = await Client.connect({
  workingDirectory: process.cwd(),
  compileArguments: ["-std=c++23"],
});

const tree = await client.parse("example.cc");
const functions = await client.match(
  'functionDecl(isDefinition()).bind("f")', tree,
);
const calls = await client.match('callExpr().bind("call")', functions.binding("f"));
const first = await client.match('integerLiteral().bind("n")', functions.row(0).binding("f"));
const direct = await client.match('integerLiteral().bind("n")', "example.cc");
console.log(calls.length, first.rows, direct.rows);
```

`await Client.connect()` discovers the shared YAML configuration and waits for the connection. `await Client.connect({ configPath: "/path/settings.yaml" })` adds an explicit final layer. `new Client()` and `new Client({ configPath })` also load configuration and connect lazily. Existing `new Client(endpoint, options)` calls keep their explicit endpoint override.

Configuration merges defaults, `/etc/clang-toolkit/clang-toolkit.yaml`, home `clang-toolkit.yaml` then `.clang-toolkit.yaml`, current-directory normal then hidden files, and the optional explicit file. Each discovered file is validated before merging, so later settings cannot hide an invalid earlier file. Missing discovered files are skipped; a missing or unreadable explicit file fails with `ConfigurationError`, including its source and key. Mappings merge recursively; omitted values inherit, `{}` inherits, and permitted `null` values clear socket paths, timeouts, or gRPC limits. Relative sockets resolve beside the file that supplied them. The default socket is the platform temporary directory's `ctk.sock`.

TCP configuration requires both `network.tcp.host` and `network.tcp.port`; hosts must be `localhost` or loopback IPv4/IPv6 addresses. IPv6 targets are bracketed. For example:

```yaml
network:
  transport: tcp
  tcp:
    host: 127.0.0.1
    port: 50051
client:
  grpc:
    max_receive_message_bytes: 4194304
  rpc_timeout_ms: 20000
```

`client.configuration` exposes immutable `effectiveValues`, `provenance`, and the loaded `files`. Leaf keys are dotted YAML keys; integer values use `bigint` to preserve signed 64-bit limits, and provenance is the absolute winning file or `<defaults>`. Socket values remain raw in `effectiveValues`; `target` contains the resolved address. There is no default RPC deadline or configured gRPC message limit. Explicit `channelOptions` and `timeoutMs` override YAML settings; `timeoutMs: null` clears a configured deadline. `connectTimeoutMs` controls only connection readiness and defaults to 30 seconds.

`parse()` acquires a native tree without running a matcher. Paths are server-side paths, relative to the explicit `workingDirectory` or the Node process's current directory. Compilation flags are ordered and remain attached to a retained tree. Every retained-target match creates an independent result cursor with a revision guard; previous trees and rows stay selectable, and closing the source does not close its forks.

`MatchValue.rows` provides detached, typed semantic row snapshots. Objects and arrays are frozen; binary buffers are copied on access. `binding(name)` selects every source row containing that binding. `row(0).binding(name)` selects one row, including index zero. Empty unindexed collections continue to empty collections; missing bindings on nonempty collections and out-of-range rows fail explicitly. Matcher type checking and execution remain in Clang.

Use `close()` or `await using` for a tree, result, binding selection, or the client. Aliases of one result share their owner, so closing an indexed row or selection closes that result. `Client.close()` waits for pending calls and releases all remaining sessions; failures are reported. Server expiry also bounds abandoned sessions. There is no reliance on JavaScript garbage collection for deterministic cleanup.

## Scoped composition

```ts
const calls = await client.withTree("example.cc", async (scope) => {
  const functions = await scope.match('functionDecl(isDefinition()).bind("f")');
  return scope.match('callExpr().bind("call")', functions.binding("f"));
});
const more = await client.match('declRefExpr().bind("ref")', calls.binding("call"));
```

The callback's returned `MatchValue` or `BindingSelection` is the yielded value. The scope closes its tree and every local result except that value's owner, including on exceptions; the yielded value remains usable. A saved scope cannot start new matches after the callback ends. Each `scope.match()` uses the scope tree when its target is omitted.

## Native scripts

```ts
const response = await client.runScript(`
  let analysis = in parse "example.cc" {
    let functions = match functionDecl(isDefinition()).bind("f");
    let calls = match callExpr().bind("call") in $functions.f;
    yield calls;
  };
  let more = match declRefExpr().bind("ref") in $analysis.call;
  emit more;
`, { maxSteps: 100 });
console.log(response.emissions);
```

`runScript()` sends the native ANTLR DSL unchanged to `AnalysisService.RunScript`; it does not parse or evaluate JavaScript. Yielded native bindings can be used by later expressions within that script. Emissions returned to Node are detached semantic values, and cannot be used as live match targets in a later request. The server publishes emissions atomically after successful execution.

Explicit parse/file expressions inherit `workingDirectory` and `compileArguments`
from the call or client defaults; omitted directories use the caller's current
directory. `file` is needed only for operations that use a default file.

## Transport and errors

Unix sockets and plaintext loopback TCP (`127.0.0.1:50051`) are verified against the native server. To connect to a deployment that supplies TLS, pass gRPC credentials explicitly:

```ts
import { credentials } from "@grpc/grpc-js";
const remote = await Client.connect({
  configPath: "/path/tls-deployment.yaml",
  credentials: credentials.createSsl(),
});
```

The present native server provides insecure local transports; this SDK's TLS configuration support does not imply that native HTTPS was tested. `metadata`, `channelOptions`, and `timeoutMs` configure the connection. `MatchOptions.callOptions` and `ScriptOptions.callOptions` can override individual deadlines. Native gRPC failures become `ClangToolkitError` with numeric `code`, `details`, and response `metadata`. Response envelopes are checked with Zod before handles are published; semantic fields have generated protobuf types.

```ts
import { ClangToolkitError } from "@clang-toolkit/sdk";
import { status } from "@grpc/grpc-js";
try {
  await client.match("unknownMatcher()", tree);
} catch (error) {
  if (error instanceof ClangToolkitError && error.code === status.INVALID_ARGUMENT) {
    console.error(error.details);
  } else throw error;
}
```
