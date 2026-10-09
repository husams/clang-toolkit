# Console and Python SDK coverage

Audit date: 2026-10-09. Checked the current Python client, Lark evaluator,
match values, console command reference and the wiki's console/reasoning guidance.
The SDK does **not** expose every console feature as a dedicated Python method.
The table distinguishes public methods from the expression bridge and terminal UI.

| Console capability | Public Python route | Coverage |
|---|---|---|
| Parse and retain a translation unit | `Client.parse` / `AsyncClient.parse` | Direct typed API; compilation database and compiler overrides supported. |
| Match a file, tree, result or selected binding | `match_in`, `ParsedTree.match`, `BindingSelection.match` | Direct typed values, independent lifetime and source provenance. |
| Compose matchers and parameterize reusable queries | `Matcher`, factories in `clang_toolkit.matchers`, ordinary Python functions | Added immutable composition; string queries remain supported. The server validates Clang matcher compatibility. |
| Stream match rows | `match_in(..., on_row=...)` | Sync and async callbacks; callback payloads are copied protobuf rows. Retained continuation requires the completed result. |
| Directory, glob and file-list matching | `execute('match ... in ...')` | Expression bridge returns a native aggregate. No direct typed `match_many` method. Legacy `Client.match(files=...)` returns JSON strings; async legacy matching returns match events. |
| Scoped `in parse`, `foreach`, grouped counts and parameterized matcher routines | `execute(source)` or ordinary Python loops/functions | One Lark expression or assignment per call; `execute` is annotated `Any`. |
| Source coordinates, symbols, documentation and call facts | `MatchRow.bindings`, `BindingSelection.value` | Public copied protobuf metadata; names/types also have Python selection conveniences. |
| Safe semantic fields and inherited node aliases | `execute` expressions, or explicit protobuf paths/presence/availability | `fieldState`, `fieldOr`, console `hasField` and node aliases belong to the console semantic view. No dedicated public Python view helpers. |
| `unique`, `sort`, `filter`, `joinWith`, shape inspection | `execute` expressions or Python collection operations | Console selector semantics are reachable through the bridge; no dedicated public collection methods. |
| AST traversal, CFG and call graph | `traverse`, `cfg`, `callgraph` | Direct protobuf results; shallow/recursive projection, main-file scope and bounds supported. Sync CFG takes `cfg(function, path=...)`; async takes `cfg(path, function)`. |
| Native server script | `run_script` | Direct API. Native scripting and the console Lark language are different contracts. |
| Query events, background work, pause/resume and incremental file submission | `AsyncClient.query`, `iter_events`, `start_background_query`, `QuerySession`; sync session adapter | Direct APIs. Successful streaming requires a completion event and terminal gRPC OK. |
| Raw cursor open/continue/restart/close | `match_file`, `continue_match`, `restart_match`, `close_match` | Direct sync and async methods; explicit IDs/revisions are the lower-level route. |
| Server version/status, session list/attach, cache pruning | `server_version`, `server_status`, `list_sessions`, `attach_session`, `prune_caches` | Direct sync and async APIs. |
| Read JSON/YAML documents | `execute('read ...')` or Python document libraries | Expression bridge; direct document-reading convenience is absent. |
| Save/load typed console snapshots and YAML/JSON/CSV/protobuf file sinks | Python I/O; console codecs live under `cli.runtime.persistence` | No public SDK codec or command route. Ordinary Python serialization is not the console envelope format. Saved semantic rows cannot restore native handles. |
| Settings, binding rename/drop, print, batch error handling | Client arguments, Python variables/output/control flow | Programmatic alternatives; `execute` rejects command statements and cannot run a console batch. |
| Help, completion, history, highlighting and interactive prompt | Terminal console | UI features; no SDK equivalent is needed for analysis. |

## Recommended Python route

Use `match_in` or `match(..., file=...)` for typed results. Compose a matcher
object and pass it directly; use ordinary Python functions for reusable matcher
parameters. Use the expression bridge only when its documented directory/list
aggregate or console semantic operations are needed. It parses one statement,
retains assignments within that client and returns the runtime value without
printing it. Its internal semantic view types are not a statically typed SDK
contract.

The builder follows the native matcher string grammar: contents are literal,
and it chooses a single/double quote delimiter absent from the value. Strings
containing both delimiters raise `ValueError` when serialized. Native matcher
text and the console expression grammar have different quoting rules; pass
objects directly to the native SDK methods.

The agent skill is in `skills/ctk-cpp-reasoning/`, with bundled API and reasoning
references and a portable uv project containing the SDK wheel and dependency lock.
`scripts/setup.sh [destination]` deploys the skill and installs Python 3.14 and the
SDK environment. `scripts/python.sh` uses that installation's project by default;
an optional nonempty `CTK_SDK_PROJECT` overrides it. Consumers reason through the
public SDK without inspecting installed source or configuration.

## Evidence and boundaries

Primary audit paths: `python/clang_toolkit/client.py`, `match_values.py`,
`cli/runtime/evaluator.py`, `cli/runtime/references.py`, `cli/runtime/semantic.py`,
`cli/runtime/persistence.py`, and `docs/console-command-reference.md`.
Historical wiki checklist: [[pages/planning/clang-toolkit-console-design]],
[[pages/planning/clang-toolkit-reasoning-gap-improvements]] and
[[pages/manuals/clang-toolkit-console-resource-management]].

This is a source-backed capability audit, not a claim that every listed console
command was replayed. Executed suite and native typed-matcher results are recorded
in [sdk-agent-progress.md](sdk-agent-progress.md).
