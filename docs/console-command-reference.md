# Console command reference

Use `help COMMAND` or `COMMAND?` in the console. Multiword topics work too:
`help cursor open` and `cursor open?` are equivalent. Help is local and remains
visible when command output is redirected. Bare `help` lists all forms.

All bundled Clang matchers also have local help: `help functionDecl`,
`hasName?`, or `help hasDescendant`. Use `help matchers` and
`help matchers node|narrowing|traversal` to browse by kind. Matcher help
includes LLVM reference descriptions, overload signatures and examples.

Uppercase words are placeholders; brackets denote optional syntax. Examples
use the checked-in `examples/parse_match.cc` fixture. Run them from the repository
root with a native server for analysis operations. Use returned cursor IDs in
place of `CURSOR_ID`; the console opens its query session automatically.

## peek

Inspect immediate native neighbours of a bound node.

```text
peek children|parents [MATCHER] in TARGET [nodes NUMBER]
```

- TARGET is a retained binding, such as $rows[0].f.
- Filters test each neighbour itself; children never searches grandchildren.
- Standalone output streams rows; assignment retains an independent collection.
- Rows expose .target and explicit matcher bindings. No current command is needed.
- nodes counts examined candidates before filtering: default 10000, range 1..100000.
- Native visitor children include implicit and type-location edges.
- Parents preserve shared Decl/Stmt occurrences; auxiliary children retain their exact navigation parent.
- MATCHER may be an inline expression or a saved matcher reference such as $base_edges.
- cxxBaseSpecifier(hasType(cxxRecordDecl().bind("base"))) filters base edges and binds their referenced classes in the same operation; .target remains the base edge.

```text
let methods = peek children cxxMethodDecl() in $rows[0].record
peek parents in $calls[0].call
```

## step

Return a selected neighbour as a new retained node reference.

```text
step children|parents [MATCHER] [at INDEX] in TARGET [nodes NUMBER]
```

- Without at, exactly one candidate is required; zero and ambiguity are errors.
- INDEX is zero-based after filtering. The starting reference remains reusable.
- Supports continued match, traverse, peek and step. No mutable current state.
- Bare auxiliary bindings without native parent lookup fail explicitly; children selected by navigation retain their parent.

```text
let body = step children compoundStmt() in $functions[0].f
let parent = step parents in $body
```

## help

Explain console syntax locally; no server is required.

```text
help [command [subcommand]]
command [subcommand]?
help MATCHER
MATCHER?
```

- No topic: list commands. A topic: purpose, usage, arguments and examples.
- Clang matcher help includes category, overloads, argument/node types and reference examples; help matchers lists the categories.
- Help and errors always appear in the console, regardless of output routing.
- Every syntax error explains the expected input and marks its location with a caret; unknown commands suggest help.

```text
help match
parse?
help cursor open
cursor open?
help functionDecl
hasName?
```

## matchers

Browse all bundled Clang matchers by category.

```text
help matchers [node|narrowing|traversal]
help MATCHER
MATCHER?
```

- LLVM 22.1.8: 483 registered matcher names with offline help.
- Node matchers select an AST node kind; narrowing matchers test attributes; traversal matchers follow related nodes.
- Completion hints identify the kind and describe the matcher in root, nested and assignment contexts.
- The matcher reference includes C++ source snippets alongside matcher examples.

```text
help matchers node
help matchers narrowing
help matchers traversal
help hasDescendant
```

## parse

Parse a file and retain its native tree as a value.

```text
parse PATH
let tree = parse PATH
```

- PATH: quoted file path or a reference to a path/File; relative to the session directory.
- Automatically loads compile_commands.json; extra_args append compiler overrides.
- Select a database with ctk --compile-commands PATH or set compile_commands PATH.
- Use the result with match ... in $tree or a scoped in $tree block.

```text
parse "examples/parse_match.cc"
let tree = parse "examples/parse_match.cc"
```

## match

Match native nodes and optionally retain the resulting rows.

```text
match MATCHER [in TARGET] [scope SCOPE]
let rows = match MATCHER [in TARGET] [scope SCOPE]
match MATCHER in TARGET [scope SCOPE] do { STATEMENT; ... }
```

- Use `match` after `=` to assign query results; a bare matcher assignment constructs a matcher and accepts no `in` target.
- MATCHER: root matcher call or $matcher; .bind("name") names a selected node.
- TARGET: quoted file path, directory or glob; File, Directory, file list, parsed tree, match value or binding selection.
- Directories recurse over C/C++/Objective-C source files; globs support absolute paths and **. Expansion uses the client's filesystem. Empty selections return an empty collection.
- Target variables must already exist; bind labels name bindings in the new results.
- Explicit scope requires a retained binding selection: children tests immediate native children, self (or root_only) tests the bound node, and subtree tests it and eligible descendants. Omission preserves the binding's scope. Nested matcher constraints retain full AST context; earlier variables remain reusable.
- With do { ... }, run ordinary statements as each streamed row arrives. Every bind label becomes a local variable: .bind("func") exposes $func.node. Newlines or semicolons separate statements; # starts a comment.
- Each row gets a fresh local scope; outer variables are restored afterwards. Streamed bindings provide copied semantic fields; native continuation requires a completed retained result. Row work is serialized across concurrent file streams; row order follows arrival order. Limits: 10000 rows and 1000000 bytes of collected output.
- A missing `match` in this assignment form shows its insertion point and a corrected command.
- Without in: use the enclosing block tree, otherwise configured files (default []).
- Rows use zero-based indices: $rows[0].f; $rows.f selects bind label f across rows.
- Collections expose length, isEmpty, rows, zero-based indexing, and unique(field), sort(field), filter(field, expected). Selectors accept dotted paths; unique preserves the first row and sort orders numbers numerically, strings lexically, and other values deterministically by type and text.
- A directory, glob or file-list query returns one typed collection with per-row source_file provenance. Files run in parallel up to pool.size, retaining input order. Continue from one binding with match ... in $rows[0].f, or from every row with match ... in $rows.f.
- Continuation rows expose source_match_index (the zero-based parent row) and source_file, so multi-file and parent-row provenance remain inspectable.
- Read binding fields directly, for example $rows[0].f.node or $rows[0].f.is_complete; .value remains available for existing scripts.
- An indexed binding such as $rows[0].f displays its copied semantic value directly; it remains usable as a native match target.
- Binding .keys lists readable AST fields and conveniences such as decl_name, omitting node and serializer metadata; .node.keys lists readable immediate and inherited AST properties. Map .keys lists actual map names.
- Declaration conveniences include node.name (typed DeclarationName), node.qualified_name (string), node.declared_type, and binding shortcuts such as decl_name, parameter_name, record_name, type_name and decl_type.
- Bindings expose symbol_identity (Clang USR for named declarations), raw documentation, location and range. Location file/line/column is valid only when location.valid is true; coordinates are one-based and include macro status. The optional location.offset is a zero-based byte offset in the physical source file. All valid range points also supply offsets; expansion_end and spelling_end retain final-token-start coordinates, while expansion_end_exclusive and spelling_end_exclusive point past the final token for [begin, end) byte slices. The expansion exclusive end covers a final macro invocation. Slice only valid points with offsets in the same file; spelling endpoints can span files.
- Call-expression bindings expose call_site with caller identity/name, static callee identity/name and CALL_DISPATCH_DIRECT, CALL_DISPATCH_INDIRECT or CALL_DISPATCH_VIRTUAL. VIRTUAL records the statically selected declaration, not a runtime target.
- Completion labels active payloads, fields and methods, and offers inherited fields such as name, qualified_name and return_type.
- Match values contain immediate fields; bodies, parameters, operands and other child AST values are unrequested. Retrieve child nodes with a follow-up match.
- Read type text through return_type.description.spelling; return_type.type is unrequested.
- fieldState("field") reports PRESENT, ABSENT, SEMANTICALLY_ABSENT, INAPPLICABLE, UNREQUESTED, UNAVAILABLE, TRUNCATED or UNSPECIFIED.
- hasField("field") checks presence only when the field has presence information; it raises for UNREQUESTED fields. fieldOr("field", default) supplies a default for ABSENT, SEMANTICALLY_ABSENT or INAPPLICABLE fields and raises for UNREQUESTED, UNAVAILABLE, TRUNCATED or UNSPECIFIED fields.
- Tab inside hasField, fieldState or fieldOr arguments offers quoted field names.
- Uses extra_args (default []) and traversal (default AsIs); server validates matcher types.

```text
match functionDecl().bind("f") in "examples/parse_match.cc"
let rows = match functionDecl().bind("f") in "examples/parse_match.cc"
let m = match functionDecl(isExpansionInMainFile()).bind("f") in $f
match callExpr() in $rows.f
$rows[0].f.value.node.qualified_name
$rows[1].root.keys
$rows[0].f.qualified_name
$rows[0].f.value.node.name.identifier
$rows[0].f.value.node.function_decl.function.declarator.value.named.qualified_name
$rows[0].f.value.node.cxx_method_decl.method.function.declarator.value.named.qualified_name
let calls = match callExpr().bind("c") in $rows[0].f
$calls[0].source_file
$calls[0].source_match_index
$rows[0].f.symbol_identity
$rows[0].f.location.line
$rows[0].f.range.expansion_begin.column
$rows[0].f.documentation
$calls[0].c.call_site.static_callee_name
let unique = $rows.unique("f.symbol_identity")
let filtered = $unique.filter("f.decl_name", "demo::run")
$rows[0].f.value.node.hasField("body")
$rows[0].f.value.node.fieldState("parameters")
$rows[0].f.value.node.name.fieldOr("identifier", "anonymous")
```

## let

Bind a typed expression without printing it.

```text
let NAME = VALUE
let NAME(PARAM, ...) = MATCHER
```

- NAME: identifier without $. References use $name, fields and zero-based [index].
- VALUE: an operation, matcher, literal, list, reference, glob, parse, match, foreach, batch or scoped block. Operational commands also evaluate as values; effect-only operations return null. quit/exit remain console control flow.
- Consumed operations are silent. match do returns its captured display text; foreach and batch brace bodies contribute their final value, while scoped analysis blocks use yield.
- Matcher construction is local; parse/match require a server. Failed evaluation preserves the prior binding.
- Parameterized matchers use let named(name) = functionDecl(hasName($name)). Parameters are declared without $ and referenced with $ inside the routine. Calls use named("value") and may be nested or followed by .bind("label").
- A routine body must return a matcher. Arguments may be strings, numbers, booleans, matcher values or references. Parameters are local to each call; other references and routines use their current values at call time. Argument counts must match, parameter names must be unique, built-in matcher names are reserved, and call depth is limited to 64.
- let silently retains typed query and graph results. Read counts with .length, rows with [index], and select bind label f across rows with $rows.f.
- Use unique(field), sort(field) and filter(field, expected) on supported collections; field selectors may be dotted paths.
- Lists and dictionaries are mutable local values. Use help collections for literals, properties, methods and mutation statements.
- split STRING by SEPARATOR and join LIST with SEPARATOR produce values locally. flatten(VALUE) concatenates one level of list/query-result children in order, skips empty children, and returns a plain list; child rows keep their original objects. Strings, dictionaries and scalars are not child collections. The flattened result is limited to 10000 items.

```text
let predicate = hasName("main")
let named(name) = functionDecl(hasName($name))
let rows = match named("main").bind("f") in "examples/parse_match.cc"
let matcher = functionDecl($predicate)
let files = glob("examples/*.cc")
let rows = match $matcher in $files
let continued = match callExpr().bind("call") in $rows.f
let unique = $rows.unique("f.symbol_identity").sort("f.decl_name")
let graph = traverse "examples/parse_match.cc" depth 1 projection shallow main-file true
let d = {a: 1, b: 2}
let names = $d.keys
let values = $d.values
let found = $d.hasKey("a")
let parts = split "a/b" by "/"
let text = join parts with ","
let rows = flatten($run.results)
```

## collections

Create and work with local mutable lists and dictionaries.

```text
let d = {a: 1, b: 2}
set d['a'] = 1
push xs, 4
let x = pop xs
delete d['a']
let parts = split "a/b" by "/"
let text = join parts with ","
```

- Dictionary literals accept identifier keys or quoted string keys. Properties: keys, values, length and isEmpty.
- Dictionary methods: get("key"), set("key", value), delete("key"), hasKey("key") and clear().
- List properties: length and isEmpty. Methods: push(value), pop([index]), insert(index, value), remove(value) and clear().
- remove(value) removes the first equal item; it does not take an index.
- push NAME, VALUE and push NAME with VALUE append; pop NAME removes and returns the final item.
- set NAME[KEY] = VALUE, delete NAME[KEY] and delete NAME[INDEX] mutate a collection in place.
- split STRING by SEPARATOR returns a list; join NAME with SEPARATOR returns a string.
- String method: strip() trims leading/trailing whitespace; strip(chars) trims any of the specified characters.
- Mutations are local to the runtime and do not modify source files or query results.

```text
let d = {"a": 1, "b": 2}
$d.keys
$d.values
$d.get("a")
$d.hasKey("a")
set d['a'] = 3
delete d['a']
let xs = [1, 2, 3]
push xs, 4
let x = pop xs
let parts = split "a/b" by "/"
let text = join parts with ","
```

## import

Load local matcher and value definitions from a console library.

```text
import "lib/module.ctk"
```

- A relative path is resolved from the importing library; a top-level import uses the --script source directory or runtime working directory.
- Libraries may contain top-level let assignments, parameterized matcher definitions and nested imports. Definitions become visible in the current runtime.
- Imports share the current runtime; there are no namespaces or separate exports. Import cycles are rejected.

```text
import "lib/module.ctk"
```

## push

Append a value to a named local list.

```text
push NAME, VALUE
push NAME with VALUE
```

- NAME is a local list binding; this statement mutates that list in place.

```text
push xs, 4
push xs with 4
```

## pop

Remove and return the last item in a named local list.

```text
let NAME = pop LIST
```

- The list must be nonempty; assign the returned value with let.

```text
let x = pop xs
```

## delete

Delete one item from a named local list or dictionary.

```text
delete NAME[KEY]
```

- KEY is a string for dictionaries or a zero-based index for lists.

```text
delete d['a']
delete xs[0]
```

## split

Split a string into a local list using a separator.

```text
let NAME = split STRING by SEPARATOR
```

- STRING and SEPARATOR are string values; an empty separator is rejected.

```text
let parts = split "a/b" by "/"
```

## flatten

Concatenate the children of a collection by one level, locally.

```text
flatten(VALUE)
let NAME = flatten(VALUE)
```

- VALUE is a list, tuple or query-result collection. Each child must itself be a list, tuple, MatchSet, MatchValue, native match/binding collection or repeated semantic field.
- Children are visited in order; empty children contribute nothing. The result is a plain list and retains the original row objects without copying or requerying.
- Flattening is one level only. Strings, dictionaries and scalar children are rejected with their index; output is limited to 10000 items.

```text
let rows = flatten($run.results)
let grouped = [[1, 2], [], [3]]
flatten($grouped)
```

## join

Join a named list of strings using a separator.

```text
let NAME = join LIST with SEPARATOR
```

- Every list item and the separator must be a string.

```text
let text = join parts with ","
```

## inspect

Inspect a value's bounded shape, fields, methods and availability locally.

```text
inspect $REFERENCE
```

- Accepts runtime bindings and indexed/field selections; no server request is made.
- Output is bounded to a preview of the value. Use fieldState on semantic values to distinguish UNREQUESTED from absent fields.

```text
inspect $rows[0].f
```

## in

Evaluate a declarative block with a default parsed tree and local bindings.

```text
in parse PATH { let NAME = VALUE; ... yield VALUE; }
in $tree { let NAME = VALUE; ... yield VALUE; }
```

- The target must be a parsed tree; assignment statements require semicolons.
- Unqualified match uses this tree. Nested blocks restore the enclosing tree on exit.
- One terminal yield is required; its final semicolon is optional. Locals disappear on exit.
- Yielded native values retain the tree resources they need.

```text
let result = in parse "examples/parse_match.cc" { let rows = match functionDecl().bind("f"); yield rows; }
```

## yield

Return one value from a scoped in block.

```text
in $tree { ... yield VALUE; }
```

- Only supported as the terminal expression of an in block, not a standalone command.
- VALUE: expression, $reference or bare local name; no default value.

```text
in parse "examples/parse_match.cc" { let rows = match functionDecl(); yield rows; }
```

## print

Render a value through the configured output destination.

```text
print VALUE [to PATH [mode replace|append]]
$reference
QUOTED_STRING
```

- VALUE: any value expression. Output defaults to stdout; let is silent.
- to PATH writes only this print: replaces by default; mode append adds to an existing file.
- PATH accepts a quoted/interpolated string or $variable; relative to the session directory.
- Double quotes interpolate $name/${reference}; single quotes are literal.
- Escape a dollar as \$ in double quotes. Lists expose length, isEmpty and joinWith(separator).

```text
let values = [1, 2, 3]
print $values
$values.length
"count=${values.length}"
```

## foreach

Iterate values with a scoped iterator, evaluating an expression or statement block.

```text
foreach NAME in LIST do VALUE [done]
let results = foreach NAME in LIST do VALUE done
foreach NAME in LIST do { STATEMENTS }
```

- LIST accepts ordinary lists, query rows, named binding collections and repeated semantic fields (at most 10000 elements).
- Declare the iterator as a plain name and reference it with $name inside the body; legacy $name declarations remain accepted. Use do {} for an empty statement block, or do {} done for an empty dictionary expression.
- The iterator shadows outer names only during the body. Multiline value-expression bodies end with done; brace blocks end with }. Assigned brace blocks collect the final value of each iteration without automatic display; standalone blocks retain their per-statement output.
- Expression bodies return a new list of results; let captures it silently. Statement blocks run commands with newline or semicolon separators and print only their explicit output. Errors report the element index.
- Read a matched row with print $m.root.decl_name, or interpolate a field path inside a string with ${m.root.decl_name}.
- Iterate query rows directly; each row exposes its bound values plus source_match_index and source_file. Iterate $rows.f to visit a named binding from every row.
- Lists and query collections support .length and indexing; use unique(field), sort(field) or filter(field, expected) before iterating when needed.

```text
let files = glob("examples/*.cc")
foreach file in $files do "${file.basename}" done
foreach m in $rows do { print $m.root.decl_name; }
```

## glob

Create sorted File and Directory values from a relative pattern.

```text
let files = glob(QUOTED_PATTERN)
```

- Patterns are relative to the session directory; ** recurses. Absolute patterns are rejected.
- No matches returns []; maximum 10000 entries. File/Directory metadata is a snapshot.
- Properties: size, modified, basename, dirname, absolute, parts. Match accepts directory targets; file lists must contain only files.

```text
let files = glob("examples/*.cc")
match varDecl() in $files
```

## files

Discover and freeze file/profile metadata without parsing translation units.

```text
let inputs = files "src/"
let inputs = files "src/**/*.cpp"
let inputs = files ["src/a.cpp", "src/b.cpp"]
```

- The result is a FileSet with immutable inputs, compilation profiles and diagnostics.
- Discovery runs against the serving machine and obeys server metadata limits.
- Use $inputs.length, $inputs.inputs, or file list discovered in $inputs.

```text
let inputs = files "src/"
file list discovered in $inputs
```

## file

Open, inspect, refresh and close caller-owned file leases.

```text
file open PATH into $handle
file list [discovered in $manifest]
file info $handle
file close $handle | all
file refresh $handle into $updated
```

- FileHandle and ParsedTree values are accepted by match and file close.
- Closing a file lease preserves independent result cursors and reports remaining pins.
- Refresh creates a new snapshot handle; existing results stay on their original snapshot.

```text
file open "src/widget.cpp" into $source
match functionDecl() in $source
file info $source
file close $source
```

## resource

Show current file, work, cursor, cache and admission accounting.

```text
resource status
```

- Counters may overlap when multiple owners pin one shared snapshot.
- The server reports accounted estimates and configured limits; they are not an RSS ceiling.

```text
resource status
```

## batch

Process a frozen FileSet and return status plus detached group values.

```text
batch NAME in $manifest size N [jobs J] [memory "768MiB"] [on error stop|continue] [progress on|off] do { STATEMENTS }
batch NAME in $manifest count N [jobs J] [memory "768MiB"] [on error stop|continue] [progress on|off] do { STATEMENTS }
let run = batch NAME in $manifest size N do { STATEMENTS; VALUE; }
background batch NAME in $manifest size N [request "stable-key"] do { NATIVE STATEMENTS }
durable batch NAME in $manifest count N [jobs J] [memory "768MiB"] [on error continue] do { NATIVE STATEMENTS }
batch status|cancel|resume|retry $run_or_id
batch promote $run
```

- size caps inputs per group; count creates balanced groups. Choose exactly one.
- jobs defaults to the effective configured pool_size used by direct multi-file matching; jobs J overrides it only for this batch. It caps parallel file work within a group and may exceed the group size. The body runs serially, with $NAME.inputs, .paths, .index and .length.
- Each group is admitted atomically, then its file/query resources are released before the next group.
- The default is on error stop. Continue reports failures and still returns a failed run status.
- The returned dictionary includes status, results, result_group_indices and results_complete. Each successful group contributes its final evaluated value, copied before cleanup. Match results become detached data; file handles, parsed trees and closures cannot be collected.
- Collected values are bounded across the run to 10,000 retained items and 1,000,000 estimated bytes. Failed, skipped or cancelled manifest groups make results_complete false. Operational failures return a failed report in value context; interrupts raise with a partial cancelled report on the exception's .report after cleanup.
- let and other value contexts suppress automatic body and report output. Progress defaults to on in all contexts, with one-second running updates and per-file counts, including during cleanup. The workspace refreshes its progress display in place; other modes print on stdout. Progress is independent of output destinations and body output limits. progress off suppresses progress while keeping standalone body output and the final compact report.
- Standalone output is capped at 1,000,000 characters per group. The final status display is capped at 4,000 characters and samples at most 8 groups with unknown cleanup; collected results remain separately bounded and complete or explicitly failed.
- Reports include accepted inputs, completed/failed/unattempted files, skipped/cancelled files, successful save exports, output characters, peak accounted/reserved bytes, remaining external pins and cleanup acknowledgment.
- Nested batches, yielding analysis blocks, legacy cursor open/continue/restart, background and session start/add/match/resume operations are rejected before admission; use scoped match/parse/file/analysis operations inside batches.
- Durable/background batches run a native server-side body against frozen inputs. Use request "stable-key" when retrying a StartBatch call after losing its response; status reports carry revisions, and cancel/resume/retry use the revision from the last report.
- batch promote copies the completed detached ScriptResponse values into the local console. These values remain inspectable after reconnect and do not retain native AST resources.

```text
batch part in $inputs size 20 do { let rows = match functionDecl().bind("f") in $part.inputs; save $rows to "batch-${part.index}.json" as json; }
batch part in $inputs count 5 jobs 1 on error continue do { print $part.index; }
let run = batch part in $inputs size 1 do { let rows = match functionDecl().bind("f") in $part.inputs; $rows; }
background batch part in $inputs size 20 request "functions-v1" do { let rows = match functionDecl().bind("f") in $part.inputs; save $rows to "batch-${part.index}.json" as json; $rows; }
let run = batch status $run
let results = batch promote $run
```

## background

Start a legacy streaming query while the prompt remains active.

```text
background MATCHER [in FILE_LIST]
```

- Requires an active asynchronous console client. Unlike match, in accepts only a file list.
- Omitted files use configured files (default []); uses configured extra_args.
- This streams query events; use declarative match/let for retained analysis values.

```text
background functionDecl() in ["examples/parse_match.cc"]
```

## set

Persist a project or user configuration override.

```text
set [user] traversal MODE
set [user] extra_args STRING_LIST
set [user] compile_commands PATH
set [user] cache_dir to DIRECTORY
set [user] files to FILE_LIST
set [user] output to PATH_OR_STDOUT [mode replace|append]
set NAME[KEY] = VALUE
```

- Default scope: ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.
- Precedence: project > user > /etc/clang_tools/config.yaml > built-in defaults.
- traversal: AsIs (default) or IgnoreUnlessSpelledInSource. extra_args: [] by default.
- cache_dir: quoted directory, default null. files: list of paths/Files, default [].
- output: quoted/interpolated path, $variable or stdout (default). Files append; mode replace truncates.
- cache_dir is a persisted console setting; these console operations do not forward it as an RPC option.
- For local collections, set NAME[KEY] = VALUE assigns a dictionary key or existing list index; see help collections.

```text
set extra_args ["-std=c++20"]
set files to glob("examples/*.cc")
set output to "results.txt"
set output to stdout
```

## clear

Remove an override, revealing the lower configuration layers.

```text
clear [user] KEY
```

- KEY: traversal, extra_args, compile_commands, cache_dir, files, output or vars.
- Default scope is project; user selects the home layer. Does not erase runtime let bindings.

```text
clear output
clear traversal
clear user extra_args
```

## add

Append one compiler argument to the project configuration.

```text
add extra_arg QUOTED_ARGUMENT
```

- Only extra_arg is supported. extra_args defaults to []; order is preserved.

```text
add extra_arg "-Iinclude"
add extra_arg "-std=c++20"
```

## save

Persist an evaluated variable, binding or field as detached data.

```text
save $REFERENCE to PATH [as FORMAT]
```

- PATH: quoted/interpolated output file or $variable, relative to the session directory; ~/ uses HOME.
- FORMAT: yaml, json, proto or csv; inferred from suffix, yaml when no suffix (adds .yaml).
- YAML/JSON write ordinary records, lists and scalar values. CSV supports flat primitive/record lists.
- proto is binary SavedValue protobuf (api/match/v1/saved_value.proto), with a versioned typed envelope.
- JSON/YAML export a binding's AST payload without node/binding wrappers, availability, completeness bookkeeping or row provenance; rows group named payloads in bindings and collections preserve row order.
- Actual AST properties and user dictionary keys are preserved. Protobuf snapshots retain typed values and availability metadata.
- UTF-8 byte fields become text in JSON/YAML; other bytes use base64: followed by their encoded contents.
- Exported native rows are detached and cannot be reused as live match targets.

```text
let values = [1, 2, 3]
save $values to "values"
save $values to "values.json" as json
let filename = "$HOME/results.proto"
save $values to $filename as proto
save $lst[0].root to "binding.yaml" as yaml
save $lst[0].root.node.qualified_name to "name.json" as json
```

## read

Read an ordinary JSON, YAML, text or CSV file as a console value.

```text
read PATH [as FORMAT]
let data = read PATH [as FORMAT]
```

- PATH: quoted/interpolated file path, string variable or File; .json, .yaml, .yml, .txt, .text and .csv are supported.
- FORMAT: json, yaml, text or csv; inferred from the suffix. An explicit format can read any suffix or an extensionless file.
- Files are read on the client computer; relative paths use the session directory and ~/ uses HOME.
- Objects expose fields and string-key indexing; lists support zero-based indexing and foreach. Scalar and null roots are also supported; empty YAML returns null.
- Text returns a list of UTF-8 lines without line endings; spaces and blank lines are preserved. Use $line.strip() to trim whitespace or $line.strip(chars) to trim specific characters.
- CSV uses its first row as headers and returns a list of dictionaries with string cells; quotes, embedded commas/newlines and UTF-8 BOMs are supported. Empty files return an empty list; duplicate/empty headers and uneven rows are rejected.
- YAML uses safe loading; recursive aliases are rejected. Errors preserve the previous assignment value.
- read returns every document key as written. load also recognizes older typed snapshot envelopes.

```text
let data = read "config.json"
let data = read "config.yaml"
print $data.project.name
print $data.sources[0]
let filename = "$HOME/config.yml"
let data = read $filename
let lines = read "names.txt"
let names = foreach line in $lines do $line.strip() done
let lines = read "build.log" as text
let rows = read "people.csv"
print $rows[0].name.strip()
```

## load

Load persisted data into a simple variable.

```text
load PATH into $NAME
```

- PATH: quoted/interpolated existing file or $variable; formats .yaml/.yml, .json, .proto and .csv.
- Without suffix: probe those extensions and require a unique match.
- NAME must be a simple variable. Failed loading preserves its prior value.
- JSON/YAML accept ordinary data and older typed snapshots. Protobuf restores exact typed snapshots.

```text
let values = [1, 2, 3]
save $values to "values.yaml"
load "values.yaml" into $restored
print $restored
```

## history

Export or clear recorded command history.

```text
history save PATH
history clear
```

- The console records timestamped commands with a session UUID and optional label.
- Up/Down recall submitted commands across console restarts; Ctrl+R searches saved command history.
- Multiline commands remain one history entry. Syntax errors are recorded too; cancelled edits are not submitted.
- Default store: $XDG_STATE_HOME/clang_tools/history.jsonl, or ~/.local/state/clang_tools/history.jsonl.
- See help history save / help history clear.

```text
history save "commands.jsonl"
```

## history save

Export command history to a file.

```text
history save PATH
```

- PATH: quoted destination relative to the session directory; history must be enabled.

```text
history save "commands.jsonl"
```

## history clear

Clear saved commands and interactive recall history.

```text
history clear
```

- No arguments or options; history must be enabled.

```text
history clear
```

## session

List, attach or close retained native sessions, label history or control a query.

```text
session label STRING
session start QUERY_STRING
session add PATH
session match
session pause
session resume
session close
session list
session attach ID into $tree
session close ID_OR_VALUE
```

- list/attach/close ID operate native retained cursors; label is local.
- The console opens a query session automatically; start defines its matcher and add supplies files.
- See help session <subcommand>. Use parse/match/in/yield for declarative analysis.

```text
session label "study functions"
```

## session list

List retained native sessions owned by this caller.

```text
session list
```

- Shows labeled IDs, files, revisions, row counts, native binding names and idle expiry.

```text
session list
```

## session attach

Attach a retained session as a reusable tree and renew its idle expiry.

```text
session attach ID_OR_VALUE into $tree
```

- ID_OR_VALUE: quoted UUID, UUID variable or retained tree/match value.
- Only sessions owned by this caller are available; match in $tree creates independent results.
- Attached handles share this cursor; closing it invalidates attachments in other clients.
- Use session list to find IDs. Attaching does not restore result rows into a variable.

```text
session attach "00000000-0000-4000-8000-000000000001" into $tree
```

## server

Inspect the running server.

```text
server status
```

- See help server status for memory and cache accounting.

```text
server status
```

## server status

Show live server memory and retained resource usage.

```text
server status
```

- Reports uptime, current process RSS when available, session count and configured limits.
- Sizes use KiB below 1 MiB, MiB below 1 GiB, and GiB otherwise.
- Retained/native memory counters are estimates; cache and cursor bytes can overlap.
- Unavailable disk or memory cache accounting is explicitly flagged.

```text
server status
```

## cache

Inspect and prune native caches.

```text
cache status
cache prune [memory|disk|all]
```

- Active session trees and disk leases survive pruning.

```text
cache status
cache prune memory
```

## cache status

Show reusable memory snapshots and persistent native artifacts.

```text
cache status
```

- Sizes use KiB below 1 MiB, MiB below 1 GiB, and GiB otherwise.
- Disk bytes count native artifacts, excluding SQLite metadata and directory overhead.

```text
cache status
```

## cache prune

Release reusable memory entries and retire unused disk snapshots.

```text
cache prune [memory|disk|all]
```

- Default: memory. all releases memory reuse before disk cleanup.
- Pinned native sessions remain valid; their leased artifacts cannot be deleted.
- Returns before/after counters. Concurrent work may publish new entries during cleanup.

```text
cache prune memory
cache prune disk
cache prune all
```

## bindings

List local variable bindings and their retained session IDs.

```text
bindings
bindings list
```

- Lists names and types without printing bound values or environment variables.
- Native matcher binding names appear in session list; local variables use binding drop/rename.

```text
bindings
```

## binding

Drop or rename local variables.

```text
binding drop $name
binding rename $name to $new_name
```

- Targets must be simple variables. Rename rejects an occupied destination.
- Dropping a final reference releases its cursor; aliases keep it alive.

```text
binding rename $rows to $functions
binding drop $functions
```

## binding drop

Remove one local variable.

```text
binding drop $name
```

- Aliases remain valid; dropping the last retained owner releases resources.

```text
binding drop $rows
```

## binding rename

Rename a local variable without closing its resources.

```text
binding rename $name to $new_name
```

- The destination must not already exist; a same-name rename is a no-op.

```text
binding rename $rows to $functions
```

## session label

Set the local history label without changing its UUID.

```text
session label STRING
```

- STRING: quoted label; default is no label.

```text
session label "study functions"
```

## session start

Define the query for the console's session.

```text
session start QUERY_STRING
```

- QUERY_STRING is a quoted matcher expression, not a path. The session opens automatically.
- Uses configured extra_args and the session working directory.

```text
session start "functionDecl()"
```

## session add

Add a source file to the console's query session.

```text
session add PATH
```

- Define a query with session start first. PATH: quoted file path; uses configured extra_args and the session directory.

```text
session start "functionDecl()"
session add "examples/parse_match.cc"
session match
```

## session match

Run the query over files added to a bidirectional session.

```text
session match
```

- Requires session start and files supplied with session add; no arguments or options.
- An ordinary match expression executes immediately and does not define this session's query.

```text
session start "functionDecl()"
session add "examples/parse_match.cc"
session match
```

## session pause

Pause the session's query feedback.

```text
session pause
```

- Requires a started query; no arguments or options.

```text
session pause
```

## session resume

Resume the session's query feedback.

```text
session resume
```

- Requires a started query; no arguments or options.

```text
session resume
```

## session close

Close a retained native cursor or the console's query session.

```text
session close ID_OR_VALUE
session close
```

- With a quoted UUID, UUID variable, tree, match value or binding: release that retained cursor.
- A valid unavailable UUID is an idempotent close; derived independent cursors survive.
- Without an argument: close the query session's input. The console remains open.

```text
session close $tree
session close
```

## cursor

Operate explicit mutable legacy result cursors.

```text
cursor open PATH MATCHER
cursor continue ID BIND MATCHER [OPTIONS]
cursor restart ID MATCHER [revision NUMBER]
cursor close ID
```

- Paths, cursor IDs and binding names are quoted. IDs come from cursor open responses.
- See help cursor <subcommand>. Declarative match values manage their own retained handles.

```text
cursor open "examples/parse_match.cc" functionDecl().bind("f")
```

## cursor open

Match a file and return an explicit cursor identifier and revision.

```text
cursor open PATH MATCHER
```

- PATH: quoted source file; MATCHER: root call or matcher reference.
- Uses extra_args [] and traversal AsIs unless configured. row/scope/revision are rejected here.

```text
cursor open "examples/parse_match.cc" functionDecl().bind("f")
```

## cursor continue

Replace a cursor result by matching a selected binding.

```text
cursor continue ID BIND MATCHER [row INDEX] [scope MODE] [revision NUMBER]
```

- ID/BIND: quoted response cursor ID and existing binding name.
- row: zero-based unsigned index; omitted selects all rows. scope: subtree (default), root_only or children.
- revision: positive expected result revision; omitted sends no guard. Options may occur once.

```text
cursor continue "CURSOR_ID" "f" callExpr().bind("call") row 0 scope subtree revision 1
```

## cursor restart

Replace a cursor result with a query over its entire retained tree.

```text
cursor restart ID MATCHER [revision NUMBER]
```

- ID: quoted response cursor ID. revision: positive expected revision; omitted sends no guard.
- row/scope are rejected; uses the configured traversal mode.

```text
cursor restart "CURSOR_ID" varDecl().bind("v") revision 2
```

## cursor close

Release an explicit retained cursor.

```text
cursor close ID
```

- ID: quoted response cursor ID; no options.

```text
cursor close "CURSOR_ID"
```

## traverse

Stream native AST visits from a path, parsed tree or binding.

```text
traverse TARGET [depth NUMBER] [nodes NUMBER] [implicit BOOL] [instantiations BOOL] [projection shallow|recursive] [main-file BOOL] [payload-depth NUMBER] [payload-nodes NUMBER]
```

- TARGET: quoted path, File, parsed tree or native binding reference. BOOL: true or false.
- depth: 0..256, default 64. nodes: 1..100000, default 10000.
- implicit/instantiations: false by default. Each option may occur once.
- projection: shallow by default; recursive includes nested semantic payloads. payload-depth: 1..64 (default 24); payload-nodes: 1..100000 (default 10000 per node payload). These limits are independent of traversal depth/nodes.
- main-file true restricts traversal to the main source file; default false includes header declarations.
- Standalone commands stream each node as ProtoJSON, followed by completion metadata. Assignment explicitly collects nodes and depth_limited.
- Uses configured extra_args and the session directory.

```text
traverse "examples/parse_match.cc" depth 12 nodes 10000 projection shallow main-file true payload-depth 2 payload-nodes 1000
let graph = traverse "examples/parse_match.cc" depth 1 projection shallow main-file true
print $graph.nodes.length
```

## cfg

Build control-flow graphs for an exact qualified function name in a file.

```text
cfg FUNCTION in PATH [option NAME BOOL] [functions NUMBER] [blocks NUMBER] [elements NUMBER] [projection shallow|recursive] [main-file BOOL] [payload-depth NUMBER] [payload-nodes NUMBER]
```

- FUNCTION: bare, qualified or quoted exact name. PATH: quoted file or path/File reference.
- option NAME BOOL: a CfgOptions boolean field. prune_trivially_false_edges defaults to true; others to false.
- Option names: prune_trivially_false_edges, add_eh_edges, add_initializers, add_implicit_dtors, add_temporary_dtors, add_lifetime, add_scopes, add_loop_exit, add_static_init_branches, add_cxx_new_allocator, add_cxx_default_init_expr_in_ctors, add_cxx_default_init_expr_in_aggregates, add_rich_cxx_constructors, mark_elided_cxx_constructors, add_virtual_base_branches, omit_implicit_value_initializers, assume_reachable_default_in_switch_statements, always_add_statements
- functions: 1..1000 (default 100); blocks: 1..100000 (default 10000); elements: 1..1000000 (default 100000).
- projection: shallow by default; recursive expands nested semantic payloads. payload-depth: 1..64 (default 24); payload-nodes: 1..100000 (default 10000 per payload). These limits are independent of function/block/element limits.
- main-file true restricts graph construction to the main source file; default false includes headers.
- Assign a graph expression such as let flow = cfg FUNCTION in PATH to navigate graphs/blocks/elements. A standalone cfg command retains ProtoJSON output.
- Options may occur once. Uses configured extra_args. Legacy cfg FUNCTION is recognized but reports a local error requiring in PATH.

```text
cfg one in "examples/parse_match.cc" option add_implicit_dtors true blocks 10000 projection shallow main-file true payload-depth 2 payload-nodes 1000
let flow = cfg one in "examples/parse_match.cc" projection shallow main-file true
print $flow.graphs.length
```

## callgraph

Build the static native AST call graph for a file and return a typed value.

```text
callgraph PATH [nodes NUMBER] [edges NUMBER] [implicit BOOL] [instantiations BOOL] [projection shallow|recursive] [main-file BOOL] [payload-depth NUMBER] [payload-nodes NUMBER]
```

- PATH: quoted file or path/File reference. nodes: 1..100000 (default 10000).
- edges: 1..1000000 (default 100000). Options may occur once.
- Omitted implicit/instantiations use Clang CallGraph defaults (both true).
- projection: shallow by default; recursive expands nested semantic payloads. payload-depth: 1..64 (default 24); payload-nodes: 1..100000 (default 10000 per payload). These limits are independent of graph node/edge limits.
- main-file true scopes the graph to main-file declarations; default false includes headers. is_complete and external_edges_omitted expose graph coverage.
- The graph is static: indirect calls do not establish target edges, and virtual entries identify the statically selected declaration rather than runtime targets.
- Assign a graph expression to navigate nodes and edges. A standalone callgraph command continues to print ProtoJSON.
- Uses configured extra_args. Bare legacy callgraph is recognized but reports a local error requiring a path.

```text
callgraph "examples/parse_match.cc" nodes 10000 edges 100000 projection shallow main-file true payload-depth 2 payload-nodes 1000
let calls = callgraph "examples/parse_match.cc" nodes 100 projection shallow main-file true
print $calls.nodes.length
```

## script

Execute the bounded server DSL and display its typed response.

```text
script SOURCE [in PATH]
```

- SOURCE: quoted DSL source or string reference, not a script filename.
- PATH: optional quoted source file or path/File reference used as the DSL's default file.
- Uses configured extra_args and the session directory. Step budget defaults to 100; it is not a console option.

```text
script "emit 7;"
script 'let rows = match functionDecl() in "examples/parse_match.cc"; emit rows;'
```

## quit

Exit the console and clean up its client resources.

```text
quit
exit
```

- No arguments/options; Ctrl+D also exits. Ctrl+C cancels current input.

```text
quit
```

## exit

Exit the console (alias of quit).

```text
exit
```

- No arguments or options; closes the client and runtime resources.

```text
exit
```

## add extra_arg

Append one compiler argument to the project configuration.

```text
add extra_arg QUOTED_ARGUMENT
```

- Only extra_arg is supported. extra_args defaults to []; order is preserved.

```text
add extra_arg "-Iinclude"
add extra_arg "-std=c++20"
```

## set traversal

Set the traversal configuration override.

```text
set [user] traversal MODE
```

- MODE: AsIs (default) or IgnoreUnlessSpelledInSource.
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set traversal IgnoreUnlessSpelledInSource
```

## set user traversal

Set the traversal configuration override.

```text
set [user] traversal MODE
```

- MODE: AsIs (default) or IgnoreUnlessSpelledInSource.
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user traversal IgnoreUnlessSpelledInSource
```

## set extra_args

Set the extra_args configuration override.

```text
set [user] extra_args STRING_LIST
```

- STRING_LIST: ordered compiler arguments; default [].
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set extra_args ["-std=c++20"]
```

## set user extra_args

Set the extra_args configuration override.

```text
set [user] extra_args STRING_LIST
```

- STRING_LIST: ordered compiler arguments; default [].
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user extra_args ["-std=c++20"]
```

## set compile_commands

Set the compile_commands configuration override.

```text
set [user] compile_commands PATH
```

- PATH: server-side JSON file or directory; default null enables automatic discovery.
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set compile_commands "build"
```

## set user compile_commands

Set the compile_commands configuration override.

```text
set [user] compile_commands PATH
```

- PATH: server-side JSON file or directory; default null enables automatic discovery.
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user compile_commands "build"
```

## set cache_dir

Set the cache_dir configuration override.

```text
set [user] cache_dir to DIRECTORY
```

- DIRECTORY: quoted directory; default null. Stored setting; not forwarded by current console RPCs.
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set cache_dir to ".ctk-cache"
```

## set user cache_dir

Set the cache_dir configuration override.

```text
set [user] cache_dir to DIRECTORY
```

- DIRECTORY: quoted directory; default null. Stored setting; not forwarded by current console RPCs.
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user cache_dir to ".ctk-cache"
```

## set files

Set the files configuration override.

```text
set [user] files to FILE_LIST
```

- FILE_LIST: list of paths or File values, including glob results; directories are rejected. Default [].
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set files to glob("examples/*.cc")
```

## set user files

Set the files configuration override.

```text
set [user] files to FILE_LIST
```

- FILE_LIST: list of paths or File values, including glob results; directories are rejected. Default [].
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user files to glob("examples/*.cc")
```

## set output

Set the output configuration override.

```text
set [user] output to PATH_OR_STDOUT [mode replace]
```

- Default stdout. File output appends unless mode replace explicitly truncates it. Help and errors remain visible.
- Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.

```text
set output to "results.txt"
```

## set user output

Set the output configuration override.

```text
set [user] output to PATH_OR_STDOUT [mode replace]
```

- Default stdout. File output appends unless mode replace explicitly truncates it. Help and errors remain visible.
- Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.

```text
set user output to "results.txt"
```

## clear user

Remove an override, revealing the lower configuration layers.

```text
clear user KEY
```

- KEY: traversal, extra_args, compile_commands, cache_dir, files, output or vars.
- Removes the home-layer override; project overrides still take precedence. Runtime let bindings remain.

```text
clear user output
clear user traversal
clear user extra_args
```

## set user

Persist a project or user configuration override.

```text
set user traversal MODE
set user extra_args STRING_LIST
set user compile_commands PATH
set user cache_dir to DIRECTORY
set user files to FILE_LIST
set user output to PATH_OR_STDOUT [mode replace|append]
set NAME[KEY] = VALUE
```

- Writes ~/.clang_tools.yaml; project overrides still take precedence.
- Precedence: project > user > /etc/clang_tools/config.yaml > built-in defaults.
- traversal: AsIs (default) or IgnoreUnlessSpelledInSource. extra_args: [] by default.
- cache_dir: quoted directory, default null. files: list of paths/Files, default [].
- output: quoted/interpolated path, $variable or stdout (default). Files append; mode replace truncates.
- cache_dir is a persisted console setting; these console operations do not forward it as an RPC option.
- For local collections, set NAME[KEY] = VALUE assigns a dictionary key or existing list index; see help collections.

```text
set user extra_args ["-std=c++20"]
set user files to glob("examples/*.cc")
set user output to "results.txt"
set user output to stdout
```

## matchers node

Browse node matchers from LLVM 22.1.8.

```text
help matchers node
help MATCHER
MATCHER?
```

- accessSpecDecl: Matches C++ access specifier declarations.
- addrLabelExpr: Matches address of label statements (GNU extension).
- arrayInitIndexExpr: The arrayInitIndexExpr consists of two subexpressions: a common expression (the source array) that is evaluated once up-front, and a per-element initializer that runs once for each array element. Within the per-element initializer, the current index may be obtained via an ArrayInitIndexExpr.
- arrayInitLoopExpr: Matches a loop initializing the elements of an array in a number of contexts: * in the implicit copy/move constructor for a class with an array member * when a lambda-expression captures an array by value * when a decomposition declaration decomposes an array
- arraySubscriptExpr: Matches array subscript expressions.
- arrayType: Matches all kinds of arrays.
- arrayTypeLoc: Matches `ArrayTypeLoc`s.
- asmStmt: Matches asm statements.
- atomicExpr: Matches atomic builtins. Example matches __atomic_load_n(ptr, 1) void foo() { int *ptr; __atomic_load_n(ptr, 1); }
- atomicType: Matches atomic types.
- attr: Matches attributes. Attributes may be attached with a variety of different syntaxes (including keywords, C++11 attributes, GNU ``__attribute``` and MSVC `__declspec``, and ``#pragma``s). They may also be implicit.
- autoType: Matches types nodes representing C++11 auto types.
- autoreleasePoolStmt: Matches an Objective-C autorelease pool statement.
- binaryConditionalOperator: Matches binary conditional operator expressions (GNU extension).
- binaryOperator: Matches binary operator expressions.
- bindingDecl: Matches binding declarations Example matches foo and bar (matcher = bindingDecl()
- blockDecl: Matches block declarations.
- blockExpr: Matches a reference to a block.
- blockPointerType: Matches block pointer types, i.e. types syntactically represented as "void (^)(int)".
- breakStmt: Matches break statements.
- builtinType: Matches builtin Types.
- cStyleCastExpr: Matches a C-style cast expression.
- callExpr: Matches call expressions.
- caseStmt: Matches case statements inside switch statements.
- castExpr: Matches any cast nodes of Clang's AST.
- characterLiteral: Matches character literals (also matches wchar_t).
- chooseExpr: Matches GNU __builtin_choose_expr.
- classTemplateDecl: Matches C++ class template declarations.
- classTemplatePartialSpecializationDecl: Matches C++ class template partial specializations.
- classTemplateSpecializationDecl: Matches C++ class template specializations.
- coawaitExpr: Matches co_await expressions.
- complexType: Matches C99 complex types.
- compoundLiteralExpr: Matches compound (i.e. non-scalar) literals
- compoundStmt: Matches compound statements.
- conceptDecl: Matches concept declarations.
- conditionalOperator: Matches conditional operator expressions.
- constantArrayType: Matches C arrays with a specified constant size.
- constantExpr: Matches a constant expression wrapper.
- continueStmt: Matches continue statements.
- convertVectorExpr: Matches builtin function __builtin_convertvector.
- coreturnStmt: Matches co_return statements.
- coroutineBodyStmt: Matches coroutine body statements.
- coyieldExpr: Matches co_yield expressions.
- cudaKernelCallExpr: Matches CUDA kernel call expression.
- cxxBindTemporaryExpr: Matches nodes where temporaries are created.
- cxxBoolLiteral: Matches bool literals.
- cxxCatchStmt: Matches catch statements.
- cxxConstCastExpr: Matches a const_cast expression.
- cxxConstructExpr: Matches constructor call expressions (including implicit ones).
- cxxConstructorDecl: Matches C++ constructor declarations.
- cxxConversionDecl: Matches conversion operator declarations.
- cxxCtorInitializer: Matches constructor initializers.
- cxxDeductionGuideDecl: Matches user-defined and implicitly generated deduction guide.
- cxxDefaultArgExpr: Matches the value of a default argument at the call site.
- cxxDeleteExpr: Matches delete expressions.
- cxxDependentScopeMemberExpr: Matches member expressions where the actual member referenced could not be resolved because the base expression or the member name was dependent.
- cxxDestructorDecl: Matches explicit C++ destructor declarations.
- cxxDynamicCastExpr: Matches a dynamic_cast expression.
- cxxFoldExpr: Matches C++17 fold expressions.
- cxxForRangeStmt: Matches range-based for statements.
- cxxFunctionalCastExpr: Matches functional cast expressions
- cxxMemberCallExpr: Matches member call expressions.
- cxxMethodDecl: Matches method declarations.
- cxxNewExpr: Matches new expressions.
- cxxNoexceptExpr: Matches noexcept expressions.
- cxxNullPtrLiteralExpr: Matches nullptr literal.
- cxxOperatorCallExpr: Matches overloaded operator calls.
- cxxRecordDecl: Matches C++ class declarations.
- cxxReinterpretCastExpr: Matches a reinterpret_cast expression.
- cxxRewrittenBinaryOperator: Matches rewritten binary operators
- cxxStaticCastExpr: Matches a C++ static_cast expression.
- cxxStdInitializerListExpr: Matches C++ initializer list expressions.
- cxxTemporaryObjectExpr: Matches functional cast expressions having N != 1 arguments
- cxxThisExpr: Matches implicit and explicit this expressions.
- cxxThrowExpr: Matches throw expressions.
- cxxTryStmt: Matches try statements.
- cxxUnresolvedConstructExpr: Matches unresolved constructor call expressions.
- decayedType: Matches decayed type Example matches i[] in declaration of f. (matcher = valueDecl(hasType(decayedType(hasDecayedType(pointerType()))))) Example matches i[1]. (matcher = expr(hasType(decayedType(hasDecayedType(pointerType()))))) void f(int i[]) { i[1] = 0; }
- decl: Matches declarations.
- declRefExpr: Matches expressions that refer to declarations.
- declStmt: Matches declaration statements.
- declaratorDecl: Matches declarator declarations (field, variable, function and non-type template parameter declarations).
- decltypeType: Matches types nodes representing C++11 decltype(<expr>) types.
- decompositionDecl: Matches decomposition-declarations.
- deducedTemplateSpecializationType: Matches C++17 deduced template specialization types, e.g. deduced class template types.
- defaultStmt: Matches default statements inside switch statements.
- dependentCoawaitExpr: Matches co_await expressions where the type of the promise is dependent
- dependentNameType: Matches a dependent name type
- dependentScopeDeclRefExpr: Matches expressions that refer to dependent scope declarations.
- dependentSizedArrayType: Matches C++ arrays whose size is a value-dependent expression.
- dependentSizedExtVectorType: Matches C++ extended vector type where either the type or size is dependent.
- designatedInitExpr: Matches C99 designated initializer expressions [C99 6.7.8].
- doStmt: Matches do statements.
- enumConstantDecl: Matches enum constants.
- enumDecl: Matches enum declarations.
- enumType: Matches enum types.
- explicitCastExpr: Matches explicit cast expressions.
- exportDecl: Matches any export declaration.
- expr: Matches expressions.
- exprWithCleanups: Matches expressions that introduce cleanups to be run at the end of the sub-expression's evaluation.
- fieldDecl: Matches field declarations.
- fileScopeAsmDecl: Matches top level asm declarations.
- fixedPointLiteral: Matches fixed-point literals eg. 0.5r, 0.5hr, 0.5lr, 0.5uhr, 0.5ur, 0.5ulr 1.0k, 1.0hk, 1.0lk, 1.0uhk, 1.0uk, 1.0ulk Exponents 1.0e10k Hexadecimal numbers 0x0.2p2r
- floatLiteral: Matches float literals of all sizes / encodings, e.g. 1.0, 1.0f, 1.0L and 1e10.
- forStmt: Matches for statements.
- friendDecl: Matches friend declarations.
- functionDecl: Matches function declarations.
- functionProtoType: Matches FunctionProtoType nodes.
- functionTemplateDecl: Matches C++ function template declarations.
- functionType: Matches FunctionType nodes.
- genericSelectionExpr: Matches C11 _Generic expression.
- gnuNullExpr: Matches GNU __null expression.
- gotoStmt: Matches goto statements.
- ifStmt: Matches if statements.
- imaginaryLiteral: Matches imaginary literals, which are based on integer and floating point literals e.g.: 1i, 1.0i
- implicitCastExpr: Matches the implicit cast nodes of Clang's AST.
- implicitValueInitExpr: Matches implicit initializers of init list expressions.
- incompleteArrayType: Matches C arrays with unspecified size.
- indirectFieldDecl: Matches indirect field declarations.
- initListExpr: Matches init list expressions.
- injectedClassNameType: Matches injected class name types.
- integerLiteral: Matches integer literals of all sizes / encodings, e.g. 1, 1L, 0x1 and 1U.
- lValueReferenceType: Matches lvalue reference types.
- labelDecl: Matches a declaration of label.
- labelStmt: Matches label statements.
- lambdaExpr: Matches lambda expressions.
- linkageSpecDecl: Matches a declaration of a linkage specification.
- macroQualifiedType: Matches qualified types when the qualifier is applied via a macro.
- materializeTemporaryExpr: Matches nodes where temporaries are materialized.
- memberExpr: Matches member expressions.
- memberPointerType: Matches member pointer types. Given struct A { int i; } A::* ptr = A::i; memberPointerType() matches "A::* ptr"
- namedDecl: Matches a declaration of anything that could have a name.
- namespaceAliasDecl: Matches a declaration of a namespace alias.
- namespaceDecl: Matches a declaration of a namespace.
- nestedNameSpecifier: Matches nested name specifiers.
- nestedNameSpecifierLoc: Same as nestedNameSpecifier but matches NestedNameSpecifierLoc.
- nonTypeTemplateParmDecl: Matches non-type template parameter declarations.
- nullStmt: Matches null statements.
- objcCatchStmt: Matches Objective-C @catch statements.
- objcCategoryDecl: Matches Objective-C category declarations.
- objcCategoryImplDecl: Matches Objective-C category definitions.
- objcFinallyStmt: Matches Objective-C @finally statements.
- objcImplementationDecl: Matches Objective-C implementation declarations.
- objcInterfaceDecl: Matches Objective-C interface declarations.
- objcIvarDecl: Matches Objective-C instance variable declarations.
- objcIvarRefExpr: Matches a reference to an ObjCIvar.
- objcMessageExpr: Matches ObjectiveC Message invocation expressions.
- objcMethodDecl: Matches Objective-C method declarations.
- objcObjectPointerType: Matches an Objective-C object pointer type, which is different from a pointer type, despite being syntactically similar.
- objcPropertyDecl: Matches Objective-C property declarations.
- objcProtocolDecl: Matches Objective-C protocol declarations.
- objcStringLiteral: Matches ObjectiveC String literal expressions.
- objcThrowStmt: Matches Objective-C statements.
- objcTryStmt: Matches Objective-C @try statements.
- ompExecutableDirective: Matches any ``#pragma omp`` executable directive.
- opaqueValueExpr: Matches opaque value expressions. They are used as helpers to reference another expressions and can be met in BinaryConditionalOperators, for example.
- parenExpr: Matches parentheses used in expressions.
- parenListExpr: Matches paren list expressions. ParenListExprs don't have a predefined type and are used for late parsing. In the final AST, they can be met in template declarations.
- parenType: Matches ParenType nodes.
- parmVarDecl: Matches parameter variable declarations.
- pointerType: Matches pointer types, but does not match Objective-C object pointer types.
- pointerTypeLoc: Matches pointer `TypeLoc`s.
- predefinedExpr: Matches predefined identifier expressions [C99 6.4.2.2].
- qualType: Matches QualTypes in the clang AST.
- qualifiedTypeLoc: Matches `QualifiedTypeLoc`s in the clang AST.
- rValueReferenceType: Matches rvalue reference types.
- recordDecl: Matches class, struct, and union declarations.
- recordType: Matches record types (e.g. structs, classes).
- referenceType: Matches both lvalue and rvalue reference types.
- referenceTypeLoc: Matches reference `TypeLoc`s.
- returnStmt: Matches return statements.
- staticAssertDecl: Matches a C++ static_assert declaration.
- stmt: Matches statements.
- stmtExpr: Matches statement expression (GNU extension).
- stringLiteral: Matches string literals (also matches wide string literals).
- substNonTypeTemplateParmExpr: Matches substitutions of non-type template parameters.
- substTemplateTypeParmType: Matches types that represent the result of substituting a type for a template type parameter.
- switchCase: Matches case and default statements inside switch statements.
- switchStmt: Matches switch statements.
- tagDecl: Matches tag declarations.
- tagType: Matches tag types (record and enum types).
- templateSpecializationType: Matches template specialization types.
- templateSpecializationTypeLoc: Matches template specialization `TypeLoc`s.
- templateTemplateParmDecl: Matches template template parameter declarations.
- templateTypeParmDecl: Matches template type parameter declarations.
- templateTypeParmType: Matches template type parameter types.
- translationUnitDecl: Matches the top declaration context.
- type: Matches Types in the clang AST.
- typeAliasDecl: Matches type alias declarations.
- typeAliasTemplateDecl: Matches type alias template declarations.
- typeLoc: Matches TypeLocs in the clang AST.
- typedefDecl: Matches typedef declarations.
- typedefNameDecl: Matches typedef name declarations.
- typedefType: Matches typedef types.
- unaryExprOrTypeTraitExpr: Matches sizeof (C99), alignof (C++11) and vec_step (OpenCL)
- unaryOperator: Matches unary operator expressions.
- unaryTransformType: Matches types nodes representing unary type transformations.
- unresolvedLookupExpr: Matches reference to a name that can be looked up during parsing but could not be resolved to a specific declaration.
- unresolvedMemberExpr: Matches unresolved member expressions.
- unresolvedUsingTypenameDecl: Matches unresolved using value declarations that involve the typename.
- unresolvedUsingValueDecl: Matches unresolved using value declarations.
- userDefinedLiteral: Matches user defined literal operator call.
- usingDecl: Matches using declarations.
- usingDirectiveDecl: Matches using namespace declarations.
- usingEnumDecl: Matches using-enum declarations.
- usingShadowDecl: Matches shadow declarations introduced into a scope by a (resolved) using declaration.
- usingType: Matches types specified through a using declaration.
- valueDecl: Matches any value declaration.
- varDecl: Matches variable declarations.
- variableArrayType: Matches C arrays with a specified size that is not an integer-constant-expression.
- whileStmt: Matches while statements.

```text
help functionDecl
help hasName
help hasDescendant
```

## matchers narrowing

Browse narrowing matchers from LLVM 22.1.8.

```text
help matchers narrowing
help MATCHER
MATCHER?
```

- allOf: Matches if all given matchers match.
- anyOf: Matches if any of the given matchers matches.
- anything: Matches any node.
- argumentCountAtLeast: Checks that a call expression or a constructor call expression has at least the specified number of arguments (including absent default arguments).
- argumentCountIs: Checks that a call expression or a constructor call expression has a specific number of arguments (including absent default arguments).
- asString: Matches if the matched type is represented by the given string.
- booleanType: Matches type bool.
- declCountIs: Matches declaration statements that contain a specific number of declarations.
- declaresSameEntityAsBoundNode: Matches a declaration if it declares the same entity as the node previously bound to ID.
- designatorCountIs: Matches designated initializer expressions that contain a specific number of designators.
- equals: Matches literals that are equal to the given value of type ValueT.
- equalsBoundNode: Matches if a node equals a previously bound node.
- hasAnyName: Matches NamedDecl nodes that have any of the specified names.
- hasAnyOperatorName: Matches operator expressions (binary or unary) that have any of the specified names.
- hasAnyOverloadedOperatorName: Matches overloaded operator names.
- hasAnySelector: Matches when at least one of the supplied string equals to the Selector.getAsString()
- hasAttr: Matches declaration that has a given attribute.
- hasAutomaticStorageDuration: Matches a variable declaration that has automatic storage duration.
- hasBitWidth: Matches non-static data members that are bit-fields of the specified bit width.
- hasCastKind: Matches casts that has a given cast kind.
- hasDefaultArgument: Matches a declaration that has default arguments.
- hasDefinition: Matches a class declaration that is defined.
- hasDependentName: Matches the dependent name of a DependentScopeDeclRefExpr or DependentNameType
- hasDynamicExceptionSpec: Matches functions that have a dynamic exception specification.
- hasExternalFormalLinkage: Matches a declaration that has external formal linkage.
- hasGlobalStorage: Matches a variable declaration that does not have local storage.
- hasKeywordSelector: Matches when the selector is a keyword selector
- hasLocalQualifiers: Matches QualType nodes that have local CV-qualifiers attached to the node, not hidden within a typedef.
- hasLocalStorage: Matches a variable declaration that has function scope and is a non-static local variable.
- hasMemberName: Matches template-dependent, but known, member names.
- hasName: Matches NamedDecl nodes that have the specified name.
- hasNullSelector: Matches when the selector is the empty selector
- hasOperatorName: Matches the operator Name of operator expressions and fold expressions (binary or unary).
- hasOverloadedOperatorName: Matches overloaded operator names.
- hasSelector: Matches when BaseName == Selector.getAsString()
- hasSize: Matches nodes that have the specified size.
- hasStaticStorageDuration: Matches a variable declaration that has static storage duration. It includes the variable declared at namespace scope and those declared with "static" and "extern" storage class specifiers.
- hasThreadStorageDuration: Matches a variable declaration that has thread storage duration.
- hasTrailingReturn: Matches a function declared with a trailing return type.
- hasUnarySelector: Matches when the selector is a Unary Selector
- isAllowedToContainClauseKind: Matches if the OpenMP directive is allowed to contain the specified OpenMP clause kind.
- isAnonymous: Matches anonymous namespace declarations.
- isAnyCharacter: Matches QualType nodes that are of character type.
- isAnyPointer: Matches QualType nodes that are of any pointer type; this includes the Objective-C object pointer type, which is different despite being syntactically similar.
- isArray: Matches array new expressions.
- isArrow: Matches member expressions that are called with '->' as opposed to '.'.
- isAssignmentOperator: Matches all kinds of assignment operators.
- isAtPosition: Matches the ParmVarDecl nodes that are at the N'th position in the parameter list. The parameter list could be that of either a block, function, or objc-method.
- isBaseInitializer: Matches a constructor initializer if it is initializing a base, as opposed to a member.
- isBinaryFold: Matches binary fold expressions, i.e. fold expressions with an initializer.
- isBitField: Matches non-static data members that are bit-fields.
- isCatchAll: Matches a C++ catch statement that has a catch-all handler.
- isClass: Matches TagDecl object that are spelled with "class."
- isClassMessage: Returns true when the Objective-C message is sent to a class.
- isClassMethod: Returns true when the Objective-C method declaration is a class method.
- isComparisonOperator: Matches comparison operators.
- isConst: Matches if the given method declaration is const.
- isConstQualified: Matches QualType nodes that are const-qualified, i.e., that include "top-level" const.
- isConsteval: Matches consteval function declarations and if consteval/if ! consteval statements.
- isConstexpr: Matches constexpr variable and function declarations, and if constexpr.
- isConstinit: Matches constinit variable declarations.
- isCopyAssignmentOperator: Matches if the given method declaration declares a copy assignment operator.
- isCopyConstructor: Matches constructor declarations that are copy constructors.
- isDefaultConstructor: Matches constructor declarations that are default constructors.
- isDefaulted: Matches defaulted function declarations.
- isDefinition: Matches if a declaration has a body attached.
- isDelegatingConstructor: Matches constructors that delegate to another constructor.
- isDeleted: Matches deleted function declarations.
- isDerivedFrom: Overloaded method as shortcut for isDerivedFrom(hasName(...)).
- isDirectlyDerivedFrom: Overloaded method as shortcut for isDirectlyDerivedFrom(hasName(...)).
- isEnum: Matches TagDecl object that are spelled with "enum."
- isExceptionVariable: Matches a variable declaration that is an exception variable from a C++ catch block, or an Objective-C statement.
- isExpandedFromMacro: Matches statements that are (transitively) expanded from the named macro. Does not match if only part of the statement is expanded from that macro or if different parts of the statement are expanded from different appearances of the macro.
- isExpansionInFileMatching: Matches AST nodes that were expanded within files whose name is partially matching a given regex.
- isExpansionInMainFile: Matches AST nodes that were expanded within the main-file.
- isExpansionInSystemHeader: Matches AST nodes that were expanded within system-header-files.
- isExplicit: Matches constructor, conversion function, and deduction guide declarations that have an explicit specifier if this explicit specifier is resolved to true.
- isExplicitObjectMemberFunction: Matches if the given method declaration declares a member function with an explicit object parameter.
- isExplicitTemplateSpecialization: Matches explicit template specializations of function, class, or static member variable template instantiations.
- isExternC: Matches extern "C" function or variable declarations.
- isFinal: Matches if the given method or class declaration is final.
- isImplicit: Matches an entity that has been implicitly added by the compiler (e.g. implicit default/copy constructors).
- isInAnonymousNamespace: Matches declarations in an anonymous namespace.
- isInStdNamespace: Matches declarations in the namespace `std`, but not in nested namespaces.
- isInTemplateInstantiation: Matches statements inside of a template instantiation.
- isInitCapture: Matches a variable serving as the implicit variable for a lambda init- capture.
- isInline: Matches functions, variables and namespace declarations that are marked with the inline keyword.
- isInstanceMessage: Returns true when the Objective-C message is sent to an instance.
- isInstanceMethod: Returns true when the Objective-C method declaration is an instance method.
- isInstantiated: Matches declarations that are template instantiations or are inside template instantiations.
- isInstantiationDependent: Matches expressions that are instantiation-dependent even if it is neither type- nor value-dependent.
- isInteger: Matches QualType nodes that are of integer type.
- isLambda: Matches the generated class of lambda expressions.
- isLeftFold: Matches left-folding fold expressions.
- isListInitialization: Matches a constructor call expression which uses list initialization.
- isMain: Determines whether the function is "main", which is the entry point into an executable program.
- isMemberInitializer: Matches a constructor initializer if it is initializing a member, as opposed to a base.
- isMoveAssignmentOperator: Matches if the given method declaration declares a move assignment operator.
- isMoveConstructor: Matches constructor declarations that are move constructors.
- isNoReturn: Matches FunctionDecls that have a noreturn attribute.
- isNoThrow: Matches functions that have a non-throwing exception specification.
- isOverride: Matches if the given method declaration overrides another method.
- isPrivate: Matches private C++ declarations and C++ base specifiers that specify private inheritance.
- isProtected: Matches protected C++ declarations and C++ base specifiers that specify protected inheritance.
- isPublic: Matches public C++ declarations and C++ base specifiers that specify public inheritance.
- isPure: Matches if the given method declaration is pure.
- isRightFold: Matches right-folding fold expressions.
- isSameOrDerivedFrom: Overloaded method as shortcut for isSameOrDerivedFrom(hasName(...)).
- isScoped: Matches C++11 scoped enum declaration.
- isSignedInteger: Matches QualType nodes that are of signed integer type.
- isStandaloneDirective: Matches standalone OpenMP directives, i.e., directives that can't have a structured block.
- isStaticLocal: Matches a static variable with local scope.
- isStaticStorageClass: Matches variable/function declarations that have "static" storage class specifier ("static" keyword) written in the source.
- isStruct: Matches TagDecl object that are spelled with "struct."
- isTemplateInstantiation: Matches template instantiations of function, class, or static member variable template instantiations.
- isTypeDependent: Matches expressions that are type-dependent because the template type is not yet instantiated.
- isUnaryFold: Matches unary fold expressions, i.e. fold expressions without an initializer.
- isUnion: Matches TagDecl object that are spelled with "union."
- isUnsignedInteger: Matches QualType nodes that are of unsigned integer type.
- isUserProvided: Matches method declarations that are user-provided.
- isValueDependent: Matches expression that are value-dependent because they contain a non-type template parameter.
- isVariadic: Matches if a function declaration is variadic.
- isVirtual: Matches declarations of virtual methods and C++ base specifiers that specify virtual inheritance.
- isVirtualAsWritten: Matches if the given method declaration has an explicit "virtual".
- isVolatileQualified: Matches QualType nodes that are volatile-qualified, i.e., that include "top-level" volatile.
- isWeak: Matches weak function declarations.
- isWritten: Matches a constructor initializer if it is explicitly written in code (as opposed to implicitly added by the compiler).
- mapAnyOf: Matches any of the NodeMatchers with InnerMatchers nested within
- matchesName: Matches NamedDecl nodes whose fully qualified names contain a substring matched by the given RegExp.
- matchesSelector: Matches ObjC selectors whose name contains a substring matched by the given RegExp. matcher = objCMessageExpr(matchesSelector("loadHTMLStringmatches the outer message expr in the code below, but NOT the message invocation for self.bodyView. [self.bodyView loadHTMLString:html baseURL:NULL];
- memberHasSameNameAsBoundNode: Matches template-dependent, but known, member names against an already-bound node
- nullPointerConstant: Matches expressions that resolve to a null pointer constant, such as GNU's __null, C++11's nullptr, or C's NULL macro.
- numSelectorArgs: Matches when the selector has the specified number of arguments
- ofKind: Matches unary expressions of a certain kind.
- parameterCountIs: Matches FunctionDecls and FunctionProtoTypes that have a specific parameter count.
- realFloatingPointType: Matches any real floating-point type (float, double, long double).
- requiresZeroInitialization: Matches a constructor call expression which requires zero initialization.
- statementCountIs: Checks that a compound statement contains a specific number of child statements.
- templateArgumentCountIs: Matches if the number of template arguments equals N.
- unless: Matches if the provided matcher does not match.
- usesADL: Matches call expressions which were resolved using ADL.
- voidType: Matches type void.

```text
help functionDecl
help hasName
help hasDescendant
```

## matchers traversal

Browse traversal matchers from LLVM 22.1.8.

```text
help matchers traversal
help MATCHER
MATCHER?
```

- alignOfExpr: Same as unaryExprOrTypeTraitExpr, but only matching alignof.
- binaryOperation: Matches nodes which can be used with binary operators.
- callee: Matches if the call or fold expression's callee expression matches.
- containsDeclaration: Matches the n'th declaration of a declaration statement.
- eachOf: Matches if any of the given matchers matches.
- forCallable: Matches declaration of the function, method, or block the statement belongs to.
- forDecomposition: Matches the DecompositionDecl the binding belongs to.
- forEach: Matches AST nodes that have child AST nodes that match the provided matcher.
- forEachArgumentWithParam: Matches all arguments and their respective ParmVarDecl.
- forEachArgumentWithParamType: Matches all arguments and their respective types for a CallExpr or CXXConstructExpr. It is very similar to forEachArgumentWithParam but it works on calls through function pointers as well.
- forEachConstructorInitializer: Matches each constructor initializer in a constructor definition.
- forEachDescendant: Matches AST nodes that have descendant AST nodes that match the provided matcher.
- forEachLambdaCapture: Matches each lambda capture in a lambda expression.
- forEachOverridden: Matches each method overridden by the given method. This matcher may produce multiple matches.
- forEachSwitchCase: Matches each case or default statement belonging to the given switch statement. This matcher may produce multiple matches.
- forEachTemplateArgument: Matches templateSpecializationType, class template specialization, variable template specialization, and function template specialization nodes where the template argument matches the inner matcher. This matcher may produce multiple matches.
- forField: Matches the field declaration of a constructor initializer.
- forFunction: Matches declaration of the function the statement belongs to.
- has: Matches AST nodes that have child AST nodes that match the provided matcher.
- hasAncestor: Matches AST nodes that have an ancestor that matches the provided matcher.
- hasAnyArgument: Matches any argument of a call expression or a constructor call expression, or an ObjC-message-send expression.
- hasAnyBase: Matches C++ classes that have a direct or indirect base matching BaseSpecMatcher.
- hasAnyBinding: Matches any binding of a DecompositionDecl.
- hasAnyBody: Matches a function declaration that has a given body present in the AST. Note that this matcher matches all the declarations of a function whose body is present in the AST.
- hasAnyCapture: Matches any capture in a lambda expression.
- hasAnyClause: Matches any clause in an OpenMP directive.
- hasAnyConstructorInitializer: Matches a constructor initializer.
- hasAnyDeclaration: Matches an OverloadExpr if any of the declarations in the set of overloads matches the given matcher.
- hasAnyParameter: Matches any parameter of a function or an ObjC method declaration or a block.
- hasAnyPlacementArg: Matches any placement new expression arguments.
- hasAnySubstatement: Matches compound statements where at least one substatement matches a given matcher. Also matches StmtExprs that have CompoundStmt as children.
- hasAnyTemplateArgument: Matches templateSpecializationTypes, class template specializations, variable template specializations, and function template specializations that have at least one TemplateArgument matching the given InnerMatcher.
- hasAnyTemplateArgumentLoc: Matches template specialization `TypeLoc`s, class template specializations, variable template specializations, and function template specializations that have at least one `TemplateArgumentLoc` matching the given `InnerMatcher`.
- hasAnyUsingShadowDecl: Matches any using shadow declaration.
- hasArgument: Matches the n'th argument of a call expression or a constructor call expression.
- hasArgumentOfType: Matches unary expressions that have a specific type of argument.
- hasArraySize: Matches array new expressions with a given array size.
- hasBase: Matches the base expression of an array subscript expression.
- hasBinding: Matches the Nth binding of a DecompositionDecl.
- hasBody: Matches a 'for', 'while', 'while' statement or a function or coroutine definition that has a given body. Note that in case of functions or coroutines this matcher only matches the definition itself and not the other declarations of the same function or coroutine.
- hasCanonicalType: Matches QualTypes whose canonical type matches InnerMatcher.
- hasCaseConstant: If the given case statement does not use the GNU case range extension, matches the constant given in the statement.
- hasCondition: Matches the condition expression of an if statement, for loop, while loop, do-while loop, switch statement or conditional operator.
- hasConditionVariableStatement: Matches the condition variable statement in an if statement, for loop, while loop or switch statement.
- hasDecayedType: Matches the decayed type, whose decayed type matches InnerMatcher
- hasDeclContext: Matches declarations whose declaration context, interpreted as a Decl, matches InnerMatcher.
- hasDeclaration: Matches a node if the declaration associated with that node matches the given matcher.
- hasDeducedType: Matches AutoType nodes where the deduced type is a specific type.
- hasDescendant: Matches AST nodes that have descendant AST nodes that match the provided matcher.
- hasDestinationType: Matches casts whose destination type matches a given matcher.
- hasDirectBase: Matches C++ classes that have a direct base matching BaseSpecMatcher.
- hasEitherOperand: Matches if either the left hand side or the right hand side of a binary operator or fold expression matches.
- hasElementType: Matches arrays and C99 complex types that have a specific element type.
- hasElse: Matches the else-statement of an if statement.
- hasExplicitSpecifier: Matches the expression in an explicit specifier if present in the given declaration.
- hasFalseExpression: Matches the false branch expression of a conditional operator (binary or ternary).
- hasFoldInit: Matches the operand that does not contain the parameter pack.
- hasImplicitDestinationType: Matches implicit casts whose destination type matches a given matcher.
- hasInClassInitializer: Matches non-static data members that have an in-class initializer.
- hasIncrement: Matches the increment statement of a for loop.
- hasIndex: Matches the index expression of an array subscript expression.
- hasInit: Matches the n'th item of an initializer list expression.
- hasInitStatement: Matches selection statements with initializer.
- hasInitializer: Matches a variable declaration that has an initializer expression that matches the given matcher.
- hasLHS: Matches the left hand side of binary operator expressions.
- hasLoopInit: Matches the initialization statement of a for loop.
- hasLoopVariable: Matches the initialization statement of a for loop.
- hasMethod: Matches the first method of a class or struct that satisfies InnerMatcher.
- hasObjectExpression: Matches a member expression where the object expression is matched by a given matcher. Implicit object expressions are included; that is, it matches use of implicit `this`.
- hasOperands: Matches if both matchers match with opposite sides of the binary operator or fold expression.
- hasParameter: Matches the n'th parameter of a function or an ObjC method declaration or a block.
- hasParent: Matches AST nodes that have a parent that matches the provided matcher.
- hasPattern: Matches the operand that contains the parameter pack.
- hasPlacementArg: Matches placement new expression arguments.
- hasPointeeLoc: Matches pointer `TypeLoc`s that have a pointee `TypeLoc` matching `PointeeMatcher`.
- hasPrefix: Matches on the prefix of a NestedNameSpecifierLoc.
- hasQualifier: Matches Types whose qualifier, a NestedNameSpecifier, matches InnerMatcher if the qualifier exists.
- hasRHS: Matches the right hand side of binary operator expressions.
- hasRangeInit: Matches the range initialization statement of a for loop.
- hasReceiver: Matches if the Objective-C message is sent to an instance, and the inner matcher matches on that instance.
- hasReceiverType: Matches on the receiver of an ObjectiveC Message expression.
- hasReferentLoc: Matches reference `TypeLoc`s that have a referent `TypeLoc` matching `ReferentMatcher`.
- hasReplacementType: Matches template type parameter substitutions that have a replacement type that matches the provided matcher.
- hasReturnTypeLoc: Matches a function declared with the specified return `TypeLoc`.
- hasReturnValue: Matches the return value expression of a return statement
- hasSingleDecl: Matches the Decl of a DeclStmt which has a single declaration.
- hasSizeExpr: Matches VariableArrayType nodes that have a specific size expression.
- hasSourceExpression: Matches if the cast's source expression or opaque value's source expression matches the given matcher.
- hasSpecializedTemplate: Matches the specialized template of a specialization declaration.
- hasStructuredBlock: Matches the structured-block of the OpenMP executable directive
- hasSyntacticForm: Matches the syntactic form of init list expressions (if expression have it).
- hasTargetDecl: Matches a using shadow declaration where the target declaration is matched by the given matcher.
- hasTemplateArgument: Matches templateSpecializationType, class template specializations, variable template specializations, and function template specializations where the n'th TemplateArgument matches the given InnerMatcher.
- hasTemplateArgumentLoc: Matches template specialization `TypeLoc`s, class template specializations, variable template specializations, and function template specializations where the n'th `TemplateArgumentLoc` matches the given `InnerMatcher`.
- hasThen: Matches the then-statement of an if statement.
- hasTrueExpression: Matches the true branch expression of a conditional operator.
- hasType: Overloaded to match the declaration of the expression's or value declaration's type.
- hasTypeLoc: Matches if the type location of a node matches the inner matcher.
- hasUnaryOperand: Matches if the operand of a unary operator matches.
- hasUnderlyingDecl: Matches a NamedDecl whose underlying declaration matches the given matcher.
- hasUnderlyingType: Matches QualType nodes to find the underlying type.
- hasUnqualifiedDesugaredType: Matches if the matched type matches the unqualified desugared type of the matched node.
- hasUnqualifiedLoc: Matches `QualifiedTypeLoc`s that have an unqualified `TypeLoc` matching `InnerMatcher`.
- hasValueType: Matches atomic types with a specific value type.
- ignoringElidableConstructorCall: Matches expressions that match InnerMatcher that are possibly wrapped in an elidable constructor and other corresponding bookkeeping nodes.
- ignoringImpCasts: Matches expressions that match InnerMatcher after any implicit casts are stripped off.
- ignoringImplicit: Matches expressions that match InnerMatcher after any implicit AST nodes are stripped off.
- ignoringParenCasts: Matches expressions that match InnerMatcher after parentheses and casts are stripped off.
- ignoringParenImpCasts: Matches expressions that match InnerMatcher after implicit casts and parentheses are stripped off.
- ignoringParens: Overload ignoringParens for Expr.
- innerType: Matches ParenType nodes where the inner type is a specific type.
- invocation: Matches function calls and constructor calls
- loc: Matches NestedNameSpecifierLocs for which the given inner NestedNameSpecifier-matcher matches.
- member: Matches a member expression where the member is matched by a given matcher.
- ofClass: Matches the class declaration that the given method declaration belongs to.
- on: Matches on the implicit object argument of a member call expression, after stripping off any parentheses or implicit casts.
- onImplicitObjectArgument: Matches on the implicit object argument of a member call expression. Unlike `on`, matches the argument directly without stripping away anything.
- optionally: Matches any node regardless of the submatcher.
- pointee: Narrows PointerType (and similar) matchers to those where the pointee matches a given matcher.
- pointsTo: Overloaded to match the pointee type's declaration.
- references: Overloaded to match the referenced type's declaration.
- returns: Matches the return type of a function declaration.
- sizeOfExpr: Same as unaryExprOrTypeTraitExpr, but only matching sizeof.
- specifiesNamespace: Matches nested name specifiers that specify a namespace matching the given namespace matcher.
- specifiesType: Matches nested name specifiers that specify a type matching the given QualType matcher without qualifiers.
- specifiesTypeLoc: Matches nested name specifier locs that specify a type matching the given TypeLoc.
- thisPointerType: Overloaded to match the type's declaration.
- throughUsingDecl: Matches if a node refers to a declaration through a specific using shadow declaration.
- to: Matches a DeclRefExpr that refers to a declaration that matches the specified matcher.
- withInitializer: Matches the initializer expression of a constructor initializer.

```text
help functionDecl
help hasName
help hasDescendant
```
