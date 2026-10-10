"""Offline command reference shared by the console and its documentation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from lark import Tree
from clang_toolkit._generated.analysis.v1.cfg_options_pb2 import CfgOptions
from clang_toolkit.cli.language import parser


@dataclass(frozen=True)
class CommandHelp:
    topic: str
    purpose: str
    usage: tuple[str, ...]
    arguments: tuple[str, ...]
    examples: tuple[str, ...]

    def render(self) -> str:
        sections = [f"{self.topic}: {self.purpose}", "Usage:"]
        sections.extend(f"  {line}" for line in self.usage)
        sections.append("Arguments, options and defaults:")
        sections.extend(f"  {line}" for line in self.arguments)
        sections.append("Examples:")
        sections.extend(f"  {line}" for line in self.examples)
        return "\n".join(sections)


_ENTRIES = (
    CommandHelp(
        "help",
        "Explain console syntax locally; no server is required.",
        ("help [command [subcommand]]", "command [subcommand]?"),
        (
            "No topic: list commands. A topic: purpose, usage, arguments and examples.",
            "Help and errors always appear in the console, regardless of output routing.",
            "Every syntax error explains the expected input and marks its location with a caret; unknown commands suggest help.",
        ),
        ("help match", "parse?", "help cursor open", "cursor open?"),
    ),
    CommandHelp(
        "parse",
        "Parse a file and retain its native tree as a value.",
        ("parse PATH", "let tree = parse PATH"),
        (
            "PATH: quoted file path or a reference to a path/File; relative to the session directory.",
            "Automatically loads compile_commands.json; extra_args append compiler overrides.",
            "Select a database with ctk --compile-commands PATH or set compile_commands PATH.",
            "Use the result with match ... in $tree or a scoped in $tree block.",
        ),
        (
            'parse "examples/parse_match.cc"',
            'let tree = parse "examples/parse_match.cc"',
        ),
    ),
    CommandHelp(
        "match",
        "Match native nodes and optionally retain the resulting rows.",
        (
            "match MATCHER [in TARGET]",
            "let rows = match MATCHER [in TARGET]",
            "match MATCHER in TARGET do { STATEMENT; ... }",
        ),
        (
            "Use `match` after `=` to assign query results; a bare matcher assignment constructs a matcher and accepts no `in` target.",
            'MATCHER: root matcher call or $matcher; .bind("name") names a selected node.',
            "TARGET: quoted file path, directory or glob; File, Directory, file list, parsed tree, match value or binding selection.",
            "Directories recurse over C/C++/Objective-C source files; globs support absolute paths and **. Expansion uses the client's filesystem. Empty selections return an empty collection.",
            "Target variables must already exist; bind labels name bindings in the new results.",
            'With do { ... }, run ordinary statements as each streamed row arrives. Every bind label becomes a local variable: .bind("func") exposes $func.node. Newlines or semicolons separate statements; # starts a comment.',
            "Each row gets a fresh local scope; outer variables are restored afterwards. Streamed bindings provide copied semantic fields; native continuation requires a completed retained result. Row work is serialized across concurrent file streams; row order follows arrival order. Limits: 10000 rows and 1000000 bytes of collected output.",
            "A missing `match` in this assignment form shows its insertion point and a corrected command.",
            "Without in: use the enclosing block tree, otherwise configured files (default []).",
            "Rows use zero-based indices: $rows[0].f; $rows.f selects bind label f across rows.",
            "Collections expose length, isEmpty, rows, zero-based indexing, and unique(field), sort(field), filter(field, expected). Selectors accept dotted paths; unique preserves the first row and sort orders numbers numerically, strings lexically, and other values deterministically by type and text.",
            "A directory, glob or file-list query returns one typed collection with per-row source_file provenance. Files run in parallel up to pool.size, retaining input order. Continue from one binding with match ... in $rows[0].f, or from every row with match ... in $rows.f.",
            "Continuation rows expose source_match_index (the zero-based parent row) and source_file, so multi-file and parent-row provenance remain inspectable.",
            "Read binding fields directly, for example $rows[0].f.node or $rows[0].f.is_complete; .value remains available for existing scripts.",
            "An indexed binding such as $rows[0].f displays its copied semantic value directly; it remains usable as a native match target.",
            "Binding .keys lists readable AST fields and conveniences such as decl_name, omitting node and serializer metadata; .node.keys lists readable immediate and inherited AST properties. Map .keys lists actual map names.",
            "Declaration conveniences include node.name (typed DeclarationName), node.qualified_name (string), node.declared_type, and binding shortcuts such as decl_name, parameter_name, record_name, type_name and decl_type.",
            "Bindings expose symbol_identity (Clang USR for named declarations), raw documentation, location and range. Location file/line/column is valid only when location.valid is true; coordinates are one-based and include macro status. Ranges retain expansion and spelling endpoints.",
            "Call-expression bindings expose call_site with caller identity/name, static callee identity/name and CALL_DISPATCH_DIRECT, CALL_DISPATCH_INDIRECT or CALL_DISPATCH_VIRTUAL. VIRTUAL records the statically selected declaration, not a runtime target.",
            "Completion labels active payloads, fields and methods, and offers inherited fields such as name, qualified_name and return_type.",
            "Match values contain immediate fields; bodies, parameters, operands and other child AST values are unrequested. Retrieve child nodes with a follow-up match.",
            "Read type text through return_type.description.spelling; return_type.type is unrequested.",
            'fieldState("field") reports PRESENT, ABSENT, SEMANTICALLY_ABSENT, INAPPLICABLE, UNREQUESTED, UNAVAILABLE, TRUNCATED or UNSPECIFIED.',
            'hasField("field") checks presence only when the field has presence information; it raises for UNREQUESTED fields. fieldOr("field", default) supplies a default for ABSENT, SEMANTICALLY_ABSENT or INAPPLICABLE fields and raises for UNREQUESTED, UNAVAILABLE, TRUNCATED or UNSPECIFIED fields.',
            "Tab inside hasField, fieldState or fieldOr arguments offers quoted field names.",
            "Uses extra_args (default []) and traversal (default AsIs); server validates matcher types.",
        ),
        (
            'match functionDecl().bind("f") in "examples/parse_match.cc"',
            'let rows = match functionDecl().bind("f") in "examples/parse_match.cc"',
            'let m = match functionDecl(isExpansionInMainFile()).bind("f") in $f',
            "match callExpr() in $rows.f",
            "$rows[0].f.value.node.qualified_name",
            "$rows[1].root.keys",
            "$rows[0].f.qualified_name",
            "$rows[0].f.value.node.name.identifier",
            "$rows[0].f.value.node.function_decl.function.declarator.value.named.qualified_name",
            "$rows[0].f.value.node.cxx_method_decl.method.function.declarator.value.named.qualified_name",
            'let calls = match callExpr().bind("c") in $rows[0].f',
            "$calls[0].source_file",
            "$calls[0].source_match_index",
            "$rows[0].f.symbol_identity",
            "$rows[0].f.location.line",
            "$rows[0].f.range.expansion_begin.column",
            "$rows[0].f.documentation",
            "$calls[0].c.call_site.static_callee_name",
            'let unique = $rows.unique("f.symbol_identity")',
            'let filtered = $unique.filter("f.decl_name", "demo::run")',
            '$rows[0].f.value.node.hasField("body")',
            '$rows[0].f.value.node.fieldState("parameters")',
            '$rows[0].f.value.node.name.fieldOr("identifier", "anonymous")',
        ),
    ),
    CommandHelp(
        "let",
        "Bind a typed expression without printing it.",
        ("let NAME = VALUE", "let NAME(PARAM, ...) = MATCHER"),
        (
            "NAME: identifier without $. References use $name, fields and zero-based [index].",
            "VALUE: an operation, matcher, literal, list, reference, glob, parse, match, foreach, batch or scoped block. Operational commands also evaluate as values; effect-only operations return null. quit/exit remain console control flow.",
            "Consumed operations are silent. match do returns its captured display text; foreach and batch brace bodies contribute their final value, while scoped analysis blocks use yield.",
            "Matcher construction is local; parse/match require a server. Failed evaluation preserves the prior binding.",
            'Parameterized matchers use let named(name) = functionDecl(hasName($name)). Parameters are declared without $ and referenced with $ inside the routine. Calls use named("value") and may be nested or followed by .bind("label").',
            "A routine body must return a matcher. Arguments may be strings, numbers, booleans, matcher values or references. Parameters are local to each call; other references and routines use their current values at call time. Argument counts must match, parameter names must be unique, built-in matcher names are reserved, and call depth is limited to 64.",
            "let silently retains typed query and graph results. Read counts with .length, rows with [index], and select bind label f across rows with $rows.f.",
            "Use unique(field), sort(field) and filter(field, expected) on supported collections; field selectors may be dotted paths.",
            "Lists and dictionaries are mutable local values. Use help collections for literals, properties, methods and mutation statements.",
            "split STRING by SEPARATOR and join LIST with SEPARATOR produce values locally. flatten(VALUE) concatenates one level of list/query-result children in order, skips empty children, and returns a plain list; child rows keep their original objects. Strings, dictionaries and scalars are not child collections. The flattened result is limited to 10000 items.",
        ),
        (
            'let predicate = hasName("main")',
            "let named(name) = functionDecl(hasName($name))",
            'let rows = match named("main").bind("f") in "examples/parse_match.cc"',
            "let matcher = functionDecl($predicate)",
            'let files = glob("examples/*.cc")',
            "let rows = match $matcher in $files",
            'let continued = match callExpr().bind("call") in $rows.f',
            'let unique = $rows.unique("f.symbol_identity").sort("f.decl_name")',
            'let graph = traverse "examples/parse_match.cc" depth 1 projection shallow main-file true',
            "let d = {a: 1, b: 2}",
            "let names = $d.keys",
            "let values = $d.values",
            'let found = $d.hasKey("a")',
            'let parts = split "a/b" by "/"',
            'let text = join parts with ","',
            "let rows = flatten($run.results)",
        ),
    ),
    CommandHelp(
        "collections",
        "Create and work with local mutable lists and dictionaries.",
        (
            "let d = {a: 1, b: 2}",
            "set d['a'] = 1",
            "push xs, 4",
            "let x = pop xs",
            "delete d['a']",
            'let parts = split "a/b" by "/"',
            'let text = join parts with ","',
        ),
        (
            "Dictionary literals accept identifier keys or quoted string keys. Properties: keys, values, length and isEmpty.",
            'Dictionary methods: get("key"), set("key", value), delete("key"), hasKey("key") and clear().',
            "List properties: length and isEmpty. Methods: push(value), pop([index]), insert(index, value), remove(value) and clear().",
            "remove(value) removes the first equal item; it does not take an index.",
            "push NAME, VALUE and push NAME with VALUE append; pop NAME removes and returns the final item.",
            "set NAME[KEY] = VALUE, delete NAME[KEY] and delete NAME[INDEX] mutate a collection in place.",
            "split STRING by SEPARATOR returns a list; join NAME with SEPARATOR returns a string.",
            "Mutations are local to the runtime and do not modify source files or query results.",
        ),
        (
            'let d = {"a": 1, "b": 2}',
            "$d.keys",
            "$d.values",
            '$d.get("a")',
            '$d.hasKey("a")',
            "set d['a'] = 3",
            "delete d['a']",
            "let xs = [1, 2, 3]",
            "push xs, 4",
            "let x = pop xs",
            'let parts = split "a/b" by "/"',
            'let text = join parts with ","',
        ),
    ),
    CommandHelp(
        "import",
        "Load local matcher and value definitions from a console library.",
        ('import "lib/module.ctk"',),
        (
            "A relative path is resolved from the importing library; a top-level import uses the --script source directory or runtime working directory.",
            "Libraries may contain top-level let assignments, parameterized matcher definitions and nested imports. Definitions become visible in the current runtime.",
            "Imports share the current runtime; there are no namespaces or separate exports. Import cycles are rejected.",
        ),
        ('import "lib/module.ctk"',),
    ),
    CommandHelp(
        "push",
        "Append a value to a named local list.",
        ("push NAME, VALUE", "push NAME with VALUE"),
        ("NAME is a local list binding; this statement mutates that list in place.",),
        ("push xs, 4", "push xs with 4"),
    ),
    CommandHelp(
        "pop",
        "Remove and return the last item in a named local list.",
        ("let NAME = pop LIST",),
        ("The list must be nonempty; assign the returned value with let.",),
        ("let x = pop xs",),
    ),
    CommandHelp(
        "delete",
        "Delete one item from a named local list or dictionary.",
        ("delete NAME[KEY]",),
        ("KEY is a string for dictionaries or a zero-based index for lists.",),
        ("delete d['a']", "delete xs[0]"),
    ),
    CommandHelp(
        "split",
        "Split a string into a local list using a separator.",
        ("let NAME = split STRING by SEPARATOR",),
        ("STRING and SEPARATOR are string values; an empty separator is rejected.",),
        ('let parts = split "a/b" by "/"',),
    ),
    CommandHelp(
        "flatten",
        "Concatenate the children of a collection by one level, locally.",
        ("flatten(VALUE)", "let NAME = flatten(VALUE)"),
        (
            "VALUE is a list, tuple or query-result collection. Each child must itself be a list, tuple, MatchSet, MatchValue, native match/binding collection or repeated semantic field.",
            "Children are visited in order; empty children contribute nothing. The result is a plain list and retains the original row objects without copying or requerying.",
            "Flattening is one level only. Strings, dictionaries and scalar children are rejected with their index; output is limited to 10000 items.",
        ),
        (
            "let rows = flatten($run.results)",
            "let grouped = [[1, 2], [], [3]]",
            "flatten($grouped)",
        ),
    ),
    CommandHelp(
        "join",
        "Join a named list of strings using a separator.",
        ("let NAME = join LIST with SEPARATOR",),
        ("Every list item and the separator must be a string.",),
        ('let text = join parts with ","',),
    ),
    CommandHelp(
        "inspect",
        "Inspect a value's bounded shape, fields, methods and availability locally.",
        ("inspect $REFERENCE",),
        (
            "Accepts runtime bindings and indexed/field selections; no server request is made.",
            "Output is bounded to a preview of the value. Use fieldState on semantic values to distinguish UNREQUESTED from absent fields.",
        ),
        ("inspect $rows[0].f",),
    ),
    CommandHelp(
        "in",
        "Evaluate a declarative block with a default parsed tree and local bindings.",
        (
            "in parse PATH { let NAME = VALUE; ... yield VALUE; }",
            "in $tree { let NAME = VALUE; ... yield VALUE; }",
        ),
        (
            "The target must be a parsed tree; assignment statements require semicolons.",
            "Unqualified match uses this tree. Nested blocks restore the enclosing tree on exit.",
            "One terminal yield is required; its final semicolon is optional. Locals disappear on exit.",
            "Yielded native values retain the tree resources they need.",
        ),
        (
            'let result = in parse "examples/parse_match.cc" { let rows = match functionDecl().bind("f"); yield rows; }',
        ),
    ),
    CommandHelp(
        "yield",
        "Return one value from a scoped in block.",
        ("in $tree { ... yield VALUE; }",),
        (
            "Only supported as the terminal expression of an in block, not a standalone command.",
            "VALUE: expression, $reference or bare local name; no default value.",
        ),
        (
            'in parse "examples/parse_match.cc" { let rows = match functionDecl(); yield rows; }',
        ),
    ),
    CommandHelp(
        "print",
        "Render a value through the configured output destination.",
        ("print VALUE [to PATH [mode replace|append]]", "$reference", "QUOTED_STRING"),
        (
            "VALUE: any value expression. Output defaults to stdout; let is silent.",
            "to PATH writes only this print: replaces by default; mode append adds to an existing file.",
            "PATH accepts a quoted/interpolated string or $variable; relative to the session directory.",
            "Double quotes interpolate $name/${reference}; single quotes are literal.",
            "Escape a dollar as \\$ in double quotes. Lists expose length, isEmpty and joinWith(separator).",
        ),
        (
            "let values = [1, 2, 3]",
            "print $values",
            "$values.length",
            '"count=${values.length}"',
        ),
    ),
    CommandHelp(
        "foreach",
        "Iterate values with a scoped iterator, evaluating an expression or statement block.",
        (
            "foreach NAME in LIST do VALUE [done]",
            "let results = foreach NAME in LIST do VALUE done",
            "foreach NAME in LIST do { STATEMENTS }",
        ),
        (
            "LIST accepts ordinary lists, query rows, named binding collections and repeated semantic fields (at most 10000 elements).",
            "Declare the iterator as a plain name and reference it with $name inside the body; legacy $name declarations remain accepted. Use do {} for an empty statement block, or do {} done for an empty dictionary expression.",
            "The iterator shadows outer names only during the body. Multiline value-expression bodies end with done; brace blocks end with }. Assigned brace blocks collect the final value of each iteration without automatic display; standalone blocks retain their per-statement output.",
            "Expression bodies return a new list of results; let captures it silently. Statement blocks run commands with newline or semicolon separators and print only their explicit output. Errors report the element index.",
            "Read a matched row with print $m.root.decl_name, or interpolate a field path inside a string with ${m.root.decl_name}.",
            "Iterate query rows directly; each row exposes its bound values plus source_match_index and source_file. Iterate $rows.f to visit a named binding from every row.",
            "Lists and query collections support .length and indexing; use unique(field), sort(field) or filter(field, expected) before iterating when needed.",
        ),
        (
            'let files = glob("examples/*.cc")',
            'foreach file in $files do "${file.basename}" done',
            "foreach m in $rows do { print $m.root.decl_name; }",
        ),
    ),
    CommandHelp(
        "glob",
        "Create sorted File and Directory values from a relative pattern.",
        ("let files = glob(QUOTED_PATTERN)",),
        (
            "Patterns are relative to the session directory; ** recurses. Absolute patterns are rejected.",
            "No matches returns []; maximum 10000 entries. File/Directory metadata is a snapshot.",
            "Properties: size, modified, basename, dirname, absolute, parts. Match accepts directory targets; file lists must contain only files.",
        ),
        ('let files = glob("examples/*.cc")', "match varDecl() in $files"),
    ),
    CommandHelp(
        "files",
        "Discover and freeze file/profile metadata without parsing translation units.",
        (
            'let inputs = files "src/"',
            'let inputs = files "src/**/*.cpp"',
            'let inputs = files ["src/a.cpp", "src/b.cpp"]',
        ),
        (
            "The result is a FileSet with immutable inputs, compilation profiles and diagnostics.",
            "Discovery runs against the serving machine and obeys server metadata limits.",
            "Use $inputs.length, $inputs.inputs, or file list discovered in $inputs.",
        ),
        ('let inputs = files "src/"', "file list discovered in $inputs"),
    ),
    CommandHelp(
        "file",
        "Open, inspect, refresh and close caller-owned file leases.",
        (
            "file open PATH into $handle",
            "file list [discovered in $manifest]",
            "file info $handle",
            "file close $handle | all",
            "file refresh $handle into $updated",
        ),
        (
            "FileHandle and ParsedTree values are accepted by match and file close.",
            "Closing a file lease preserves independent result cursors and reports remaining pins.",
            "Refresh creates a new snapshot handle; existing results stay on their original snapshot.",
        ),
        (
            'file open "src/widget.cpp" into $source',
            "match functionDecl() in $source",
            "file info $source",
            "file close $source",
        ),
    ),
    CommandHelp(
        "resource",
        "Show current file, work, cursor, cache and admission accounting.",
        ("resource status",),
        (
            "Counters may overlap when multiple owners pin one shared snapshot.",
            "The server reports accounted estimates and configured limits; they are not an RSS ceiling.",
        ),
        ("resource status",),
    ),
    CommandHelp(
        "batch",
        "Process a frozen FileSet and return status plus detached group values.",
        (
            'batch NAME in $manifest size N [jobs J] [memory "768MiB"] [on error stop|continue] [progress on|off] do { STATEMENTS }',
            'batch NAME in $manifest count N [jobs J] [memory "768MiB"] [on error stop|continue] [progress on|off] do { STATEMENTS }',
            'let run = batch NAME in $manifest size N do { STATEMENTS; VALUE; }',
        ),
        (
            "size caps inputs per group; count creates balanced groups. Choose exactly one.",
            "jobs defaults to the effective configured pool_size used by direct multi-file matching; jobs J overrides it only for this batch. It caps parallel file work within a group and may exceed the group size. The body runs serially, with $NAME.inputs, .paths, .index and .length.",
            "Each group is admitted atomically, then its file/query resources are released before the next group.",
            "The default is on error stop. Continue reports failures and still returns a failed run status.",
            "The returned dictionary includes status, results, result_group_indices and results_complete. Each successful group contributes its final evaluated value, copied before cleanup. Match results become detached data; file handles, parsed trees and closures cannot be collected.",
            "Collected values are bounded across the run to 10,000 retained items and 1,000,000 estimated bytes. Failed, skipped or cancelled manifest groups make results_complete false. Operational failures return a failed report in value context; interrupts raise with a partial cancelled report on the exception's .report after cleanup.",
            "let and other value contexts suppress automatic body, progress and report output. Explicit writes still occur. Standalone progress defaults to on; progress off suppresses lifecycle events while keeping body output and the final compact report.",
            "Standalone output is capped at 1,000,000 characters per group. The final status display is capped at 4,000 characters and samples at most 8 groups with unknown cleanup; collected results remain separately bounded and complete or explicitly failed.",
            "Reports include accepted inputs, completed/failed/unattempted files, skipped/cancelled files, successful save exports, output characters, peak accounted/reserved bytes, remaining external pins and cleanup acknowledgment.",
            "Nested batches, yielding analysis blocks, legacy cursor open/continue/restart, background and session start/add/match/resume operations are rejected before admission; use scoped match/parse/file/analysis operations inside batches.",
        ),
        (
            'batch part in $inputs size 20 do { let rows = match functionDecl().bind("f") in $part.inputs; save $rows to "batch-${part.index}.json" as json; }',
            "batch part in $inputs count 5 jobs 1 on error continue do { print $part.index; }",
            'let run = batch part in $inputs size 1 do { let rows = match functionDecl().bind("f") in $part.inputs; $rows; }',
        ),
    ),
    CommandHelp(
        "background",
        "Start a legacy streaming query while the prompt remains active.",
        ("background MATCHER [in FILE_LIST]",),
        (
            "Requires an active asynchronous console client. Unlike match, in accepts only a file list.",
            "Omitted files use configured files (default []); uses configured extra_args.",
            "This streams query events; use declarative match/let for retained analysis values.",
        ),
        ('background functionDecl() in ["examples/parse_match.cc"]',),
    ),
    CommandHelp(
        "set",
        "Persist a project or user configuration override.",
        (
            "set [user] traversal MODE",
            "set [user] extra_args STRING_LIST",
            "set [user] compile_commands PATH",
            "set [user] cache_dir to DIRECTORY",
            "set [user] files to FILE_LIST",
            "set [user] output to PATH_OR_STDOUT [mode replace|append]",
            "set NAME[KEY] = VALUE",
        ),
        (
            "Default scope: ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.",
            "Precedence: project > user > /etc/clang_tools/config.yaml > built-in defaults.",
            "traversal: AsIs (default) or IgnoreUnlessSpelledInSource. extra_args: [] by default.",
            "cache_dir: quoted directory, default null. files: list of paths/Files, default [].",
            "output: quoted/interpolated path, $variable or stdout (default). Files append; mode replace truncates.",
            "cache_dir is a persisted console setting; these console operations do not forward it as an RPC option.",
            "For local collections, set NAME[KEY] = VALUE assigns a dictionary key or existing list index; see help collections.",
        ),
        (
            'set extra_args ["-std=c++20"]',
            'set files to glob("examples/*.cc")',
            'set output to "results.txt"',
            "set output to stdout",
        ),
    ),
    CommandHelp(
        "clear",
        "Remove an override, revealing the lower configuration layers.",
        ("clear [user] KEY",),
        (
            "KEY: traversal, extra_args, compile_commands, cache_dir, files, output or vars.",
            "Default scope is project; user selects the home layer. Does not erase runtime let bindings.",
        ),
        ("clear output", "clear traversal", "clear user extra_args"),
    ),
    CommandHelp(
        "add",
        "Append one compiler argument to the project configuration.",
        ("add extra_arg QUOTED_ARGUMENT",),
        (
            "Only extra_arg is supported. extra_args defaults to []; order is preserved.",
        ),
        ('add extra_arg "-Iinclude"', 'add extra_arg "-std=c++20"'),
    ),
    CommandHelp(
        "save",
        "Persist an evaluated variable, binding or field as detached data.",
        ("save $REFERENCE to PATH [as FORMAT]",),
        (
            "PATH: quoted/interpolated output file or $variable, relative to the session directory; ~/ uses HOME.",
            "FORMAT: yaml, json, proto or csv; inferred from suffix, yaml when no suffix (adds .yaml).",
            "YAML/JSON write ordinary records, lists and scalar values. CSV supports flat primitive/record lists.",
            "proto is binary SavedValue protobuf (api/match/v1/saved_value.proto), with a versioned typed envelope.",
            "JSON/YAML export a binding's AST payload without node/binding wrappers, availability, completeness bookkeeping or row provenance; rows group named payloads in bindings and collections preserve row order.",
            "Actual AST properties and user dictionary keys are preserved. Protobuf snapshots retain typed values and availability metadata.",
            "UTF-8 byte fields become text in JSON/YAML; other bytes use base64: followed by their encoded contents.",
            "Exported native rows are detached and cannot be reused as live match targets.",
        ),
        (
            "let values = [1, 2, 3]",
            'save $values to "values"',
            'save $values to "values.json" as json',
            'let filename = "$HOME/results.proto"',
            "save $values to $filename as proto",
            'save $lst[0].root to "binding.yaml" as yaml',
            'save $lst[0].root.node.qualified_name to "name.json" as json',
        ),
    ),
    CommandHelp(
        "read",
        "Read an ordinary JSON or YAML file as a console value.",
        ("read PATH", "let data = read PATH"),
        (
            "PATH: quoted/interpolated file path, string variable or File; .json, .yaml and .yml are supported.",
            "Files are read on the client computer; relative paths use the session directory and ~/ uses HOME.",
            "Objects expose fields and string-key indexing; lists support zero-based indexing and foreach. Scalar and null roots are also supported; empty YAML returns null.",
            "YAML uses safe loading; recursive aliases are rejected. Errors preserve the previous assignment value.",
            "read returns every document key as written. load also recognizes older typed snapshot envelopes.",
        ),
        (
            'let data = read "config.json"',
            'let data = read "config.yaml"',
            "print $data.project.name",
            "print $data.sources[0]",
            'let filename = "$HOME/config.yml"',
            "let data = read $filename",
        ),
    ),
    CommandHelp(
        "load",
        "Load persisted data into a simple variable.",
        ("load PATH into $NAME",),
        (
            "PATH: quoted/interpolated existing file or $variable; formats .yaml/.yml, .json, .proto and .csv.",
            "Without suffix: probe those extensions and require a unique match.",
            "NAME must be a simple variable. Failed loading preserves its prior value.",
            "JSON/YAML accept ordinary data and older typed snapshots. Protobuf restores exact typed snapshots.",
        ),
        (
            "let values = [1, 2, 3]",
            'save $values to "values.yaml"',
            'load "values.yaml" into $restored',
            "print $restored",
        ),
    ),
    CommandHelp(
        "history",
        "Export or clear recorded command history.",
        ("history save PATH", "history clear"),
        (
            "The console records timestamped commands with a session UUID and optional label.",
            "Up/Down recall submitted commands across console restarts; Ctrl+R searches saved command history.",
            "Multiline commands remain one history entry. Syntax errors are recorded too; cancelled edits are not submitted.",
            "Default store: $XDG_STATE_HOME/clang_tools/history.jsonl, or ~/.local/state/clang_tools/history.jsonl.",
            "See help history save / help history clear.",
        ),
        ('history save "commands.jsonl"',),
    ),
    CommandHelp(
        "history save",
        "Export command history to a file.",
        ("history save PATH",),
        (
            "PATH: quoted destination relative to the session directory; history must be enabled.",
        ),
        ('history save "commands.jsonl"',),
    ),
    CommandHelp(
        "history clear",
        "Clear saved commands and interactive recall history.",
        ("history clear",),
        ("No arguments or options; history must be enabled.",),
        ("history clear",),
    ),
    CommandHelp(
        "session",
        "List, attach or close retained native sessions, label history or control a query.",
        (
            "session label STRING",
            "session start QUERY_STRING",
            "session add PATH",
            "session match",
            "session pause",
            "session resume",
            "session close",
            "session list",
            "session attach ID into $tree",
            "session close ID_OR_VALUE",
        ),
        (
            "list/attach/close ID operate native retained cursors; label is local.",
            "The console opens a query session automatically; start defines its matcher and add supplies files.",
            "See help session <subcommand>. Use parse/match/in/yield for declarative analysis.",
        ),
        ('session label "study functions"',),
    ),
    CommandHelp(
        "session list",
        "List retained native sessions owned by this caller.",
        ("session list",),
        (
            "Shows labeled IDs, files, revisions, row counts, native binding names and idle expiry.",
        ),
        ("session list",),
    ),
    CommandHelp(
        "session attach",
        "Attach a retained session as a reusable tree and renew its idle expiry.",
        ("session attach ID_OR_VALUE into $tree",),
        (
            "ID_OR_VALUE: quoted UUID, UUID variable or retained tree/match value.",
            "Only sessions owned by this caller are available; match in $tree creates independent results.",
            "Attached handles share this cursor; closing it invalidates attachments in other clients.",
            "Use session list to find IDs. Attaching does not restore result rows into a variable.",
        ),
        ('session attach "00000000-0000-4000-8000-000000000001" into $tree',),
    ),
    CommandHelp(
        "server",
        "Inspect the running server.",
        ("server status",),
        ("See help server status for memory and cache accounting.",),
        ("server status",),
    ),
    CommandHelp(
        "server status",
        "Show live server memory and retained resource usage.",
        ("server status",),
        (
            "Reports uptime, current process RSS when available, session count and configured limits.",
            "Sizes use KiB below 1 MiB, MiB below 1 GiB, and GiB otherwise.",
            "Retained/native memory counters are estimates; cache and cursor bytes can overlap.",
            "Unavailable disk or memory cache accounting is explicitly flagged.",
        ),
        ("server status",),
    ),
    CommandHelp(
        "cache",
        "Inspect and prune native caches.",
        ("cache status", "cache prune [memory|disk|all]"),
        ("Active session trees and disk leases survive pruning.",),
        ("cache status", "cache prune memory"),
    ),
    CommandHelp(
        "cache status",
        "Show reusable memory snapshots and persistent native artifacts.",
        ("cache status",),
        (
            "Sizes use KiB below 1 MiB, MiB below 1 GiB, and GiB otherwise.",
            "Disk bytes count native artifacts, excluding SQLite metadata and directory overhead.",
        ),
        ("cache status",),
    ),
    CommandHelp(
        "cache prune",
        "Release reusable memory entries and retire unused disk snapshots.",
        ("cache prune [memory|disk|all]",),
        (
            "Default: memory. all releases memory reuse before disk cleanup.",
            "Pinned native sessions remain valid; their leased artifacts cannot be deleted.",
            "Returns before/after counters. Concurrent work may publish new entries during cleanup.",
        ),
        ("cache prune memory", "cache prune disk", "cache prune all"),
    ),
    CommandHelp(
        "bindings",
        "List local variable bindings and their retained session IDs.",
        ("bindings", "bindings list"),
        (
            "Lists names and types without printing bound values or environment variables.",
            "Native matcher binding names appear in session list; local variables use binding drop/rename.",
        ),
        ("bindings",),
    ),
    CommandHelp(
        "binding",
        "Drop or rename local variables.",
        ("binding drop $name", "binding rename $name to $new_name"),
        (
            "Targets must be simple variables. Rename rejects an occupied destination.",
            "Dropping a final reference releases its cursor; aliases keep it alive.",
        ),
        ("binding rename $rows to $functions", "binding drop $functions"),
    ),
    CommandHelp(
        "binding drop",
        "Remove one local variable.",
        ("binding drop $name",),
        ("Aliases remain valid; dropping the last retained owner releases resources.",),
        ("binding drop $rows",),
    ),
    CommandHelp(
        "binding rename",
        "Rename a local variable without closing its resources.",
        ("binding rename $name to $new_name",),
        ("The destination must not already exist; a same-name rename is a no-op.",),
        ("binding rename $rows to $functions",),
    ),
    CommandHelp(
        "session label",
        "Set the local history label without changing its UUID.",
        ("session label STRING",),
        ("STRING: quoted label; default is no label.",),
        ('session label "study functions"',),
    ),
    CommandHelp(
        "session start",
        "Define the query for the console's session.",
        ("session start QUERY_STRING",),
        (
            "QUERY_STRING is a quoted matcher expression, not a path. The session opens automatically.",
            "Uses configured extra_args and the session working directory.",
        ),
        ('session start "functionDecl()"',),
    ),
    CommandHelp(
        "session add",
        "Add a source file to the console's query session.",
        ("session add PATH",),
        (
            "Define a query with session start first. PATH: quoted file path; uses configured extra_args and the session directory.",
        ),
        (
            'session start "functionDecl()"',
            'session add "examples/parse_match.cc"',
            "session match",
        ),
    ),
    CommandHelp(
        "session match",
        "Run the query over files added to a bidirectional session.",
        ("session match",),
        (
            "Requires session start and files supplied with session add; no arguments or options.",
            "An ordinary match expression executes immediately and does not define this session's query.",
        ),
        (
            'session start "functionDecl()"',
            'session add "examples/parse_match.cc"',
            "session match",
        ),
    ),
    CommandHelp(
        "session pause",
        "Pause the session's query feedback.",
        ("session pause",),
        ("Requires a started query; no arguments or options.",),
        ("session pause",),
    ),
    CommandHelp(
        "session resume",
        "Resume the session's query feedback.",
        ("session resume",),
        ("Requires a started query; no arguments or options.",),
        ("session resume",),
    ),
    CommandHelp(
        "session close",
        "Close a retained native cursor or the console's query session.",
        ("session close ID_OR_VALUE", "session close"),
        (
            "With a quoted UUID, UUID variable, tree, match value or binding: release that retained cursor.",
            "A valid unavailable UUID is an idempotent close; derived independent cursors survive.",
            "Without an argument: close the query session's input. The console remains open.",
        ),
        ("session close $tree", "session close"),
    ),
    CommandHelp(
        "cursor",
        "Operate explicit mutable legacy result cursors.",
        (
            "cursor open PATH MATCHER",
            "cursor continue ID BIND MATCHER [OPTIONS]",
            "cursor restart ID MATCHER [revision NUMBER]",
            "cursor close ID",
        ),
        (
            "Paths, cursor IDs and binding names are quoted. IDs come from cursor open responses.",
            "See help cursor <subcommand>. Declarative match values manage their own retained handles.",
        ),
        ('cursor open "examples/parse_match.cc" functionDecl().bind("f")',),
    ),
    CommandHelp(
        "cursor open",
        "Match a file and return an explicit cursor identifier and revision.",
        ("cursor open PATH MATCHER",),
        (
            "PATH: quoted source file; MATCHER: root call or matcher reference.",
            "Uses extra_args [] and traversal AsIs unless configured. row/scope/revision are rejected here.",
        ),
        ('cursor open "examples/parse_match.cc" functionDecl().bind("f")',),
    ),
    CommandHelp(
        "cursor continue",
        "Replace a cursor result by matching a selected binding.",
        ("cursor continue ID BIND MATCHER [row INDEX] [scope MODE] [revision NUMBER]",),
        (
            "ID/BIND: quoted response cursor ID and existing binding name.",
            "row: zero-based unsigned index; omitted selects all rows. scope: subtree (default) or root_only.",
            "revision: positive expected result revision; omitted sends no guard. Options may occur once.",
        ),
        (
            'cursor continue "CURSOR_ID" "f" callExpr().bind("call") row 0 scope subtree revision 1',
        ),
    ),
    CommandHelp(
        "cursor restart",
        "Replace a cursor result with a query over its entire retained tree.",
        ("cursor restart ID MATCHER [revision NUMBER]",),
        (
            "ID: quoted response cursor ID. revision: positive expected revision; omitted sends no guard.",
            "row/scope are rejected; uses the configured traversal mode.",
        ),
        ('cursor restart "CURSOR_ID" varDecl().bind("v") revision 2',),
    ),
    CommandHelp(
        "cursor close",
        "Release an explicit retained cursor.",
        ("cursor close ID",),
        ("ID: quoted response cursor ID; no options.",),
        ('cursor close "CURSOR_ID"',),
    ),
    CommandHelp(
        "traverse",
        "Visit a file's AST and return a typed traversal value.",
        (
            "traverse PATH [depth NUMBER] [nodes NUMBER] [implicit BOOL] [instantiations BOOL] [projection shallow|recursive] [main-file BOOL] [payload-depth NUMBER] [payload-nodes NUMBER]",
        ),
        (
            "PATH: quoted source file or path/File reference. BOOL: true or false.",
            "depth: 0..256, default 64. nodes: 1..100000, default 10000.",
            "implicit/instantiations: false by default. Each option may occur once.",
            "projection: shallow by default; recursive includes nested semantic payloads. payload-depth: 1..64 (default 24); payload-nodes: 1..100000 (default 10000 per node payload). These limits are independent of traversal depth/nodes.",
            "main-file true restricts traversal to the main source file; default false includes header declarations.",
            "Assign to a variable to use nodes and depth_limited as typed fields. A standalone command continues to print ProtoJSON.",
            "Uses configured extra_args and the session directory.",
        ),
        (
            'traverse "examples/parse_match.cc" depth 12 nodes 10000 projection shallow main-file true payload-depth 2 payload-nodes 1000',
            'let graph = traverse "examples/parse_match.cc" depth 1 projection shallow main-file true',
            "print $graph.nodes.length",
        ),
    ),
    CommandHelp(
        "cfg",
        "Build control-flow graphs for an exact qualified function name in a file.",
        (
            "cfg FUNCTION in PATH [option NAME BOOL] [functions NUMBER] [blocks NUMBER] [elements NUMBER] [projection shallow|recursive] [main-file BOOL] [payload-depth NUMBER] [payload-nodes NUMBER]",
        ),
        (
            "FUNCTION: bare, qualified or quoted exact name. PATH: quoted file or path/File reference.",
            "option NAME BOOL: a CfgOptions boolean field. prune_trivially_false_edges defaults to true; others to false.",
            "Option names: " + ", ".join(CfgOptions.DESCRIPTOR.fields_by_name),
            "functions: 1..1000 (default 100); blocks: 1..100000 (default 10000); elements: 1..1000000 (default 100000).",
            "projection: shallow by default; recursive expands nested semantic payloads. payload-depth: 1..64 (default 24); payload-nodes: 1..100000 (default 10000 per payload). These limits are independent of function/block/element limits.",
            "main-file true restricts graph construction to the main source file; default false includes headers.",
            "Assign a graph expression such as let flow = cfg FUNCTION in PATH to navigate graphs/blocks/elements. A standalone cfg command retains ProtoJSON output.",
            "Options may occur once. Uses configured extra_args. Legacy cfg FUNCTION is recognized but reports a local error requiring in PATH.",
        ),
        (
            'cfg one in "examples/parse_match.cc" option add_implicit_dtors true blocks 10000 projection shallow main-file true payload-depth 2 payload-nodes 1000',
            'let flow = cfg one in "examples/parse_match.cc" projection shallow main-file true',
            "print $flow.graphs.length",
        ),
    ),
    CommandHelp(
        "callgraph",
        "Build the static native AST call graph for a file and return a typed value.",
        (
            "callgraph PATH [nodes NUMBER] [edges NUMBER] [implicit BOOL] [instantiations BOOL] [projection shallow|recursive] [main-file BOOL] [payload-depth NUMBER] [payload-nodes NUMBER]",
        ),
        (
            "PATH: quoted file or path/File reference. nodes: 1..100000 (default 10000).",
            "edges: 1..1000000 (default 100000). Options may occur once.",
            "Omitted implicit/instantiations use Clang CallGraph defaults (both true).",
            "projection: shallow by default; recursive expands nested semantic payloads. payload-depth: 1..64 (default 24); payload-nodes: 1..100000 (default 10000 per payload). These limits are independent of graph node/edge limits.",
            "main-file true scopes the graph to main-file declarations; default false includes headers. is_complete and external_edges_omitted expose graph coverage.",
            "The graph is static: indirect calls do not establish target edges, and virtual entries identify the statically selected declaration rather than runtime targets.",
            "Assign a graph expression to navigate nodes and edges. A standalone callgraph command continues to print ProtoJSON.",
            "Uses configured extra_args. Bare legacy callgraph is recognized but reports a local error requiring a path.",
        ),
        (
            'callgraph "examples/parse_match.cc" nodes 10000 edges 100000 projection shallow main-file true payload-depth 2 payload-nodes 1000',
            'let calls = callgraph "examples/parse_match.cc" nodes 100 projection shallow main-file true',
            "print $calls.nodes.length",
        ),
    ),
    CommandHelp(
        "script",
        "Execute the bounded server DSL and display its typed response.",
        ("script SOURCE [in PATH]",),
        (
            "SOURCE: quoted DSL source or string reference, not a script filename.",
            "PATH: optional quoted source file or path/File reference used as the DSL's default file.",
            "Uses configured extra_args and the session directory. Step budget defaults to 100; it is not a console option.",
        ),
        (
            'script "emit 7;"',
            "script 'let rows = match functionDecl() in \"examples/parse_match.cc\"; emit rows;'",
        ),
    ),
    CommandHelp(
        "quit",
        "Exit the console and clean up its client resources.",
        ("quit", "exit"),
        ("No arguments/options; Ctrl+D also exits. Ctrl+C cancels current input.",),
        ("quit",),
    ),
    CommandHelp(
        "exit",
        "Exit the console (alias of quit).",
        ("exit",),
        ("No arguments or options; closes the client and runtime resources.",),
        ("exit",),
    ),
)

COMMAND_HELP = {entry.topic: entry for entry in _ENTRIES}
HAS_NATIVE_ANALYSIS_GRAMMAR = any(
    rule.origin.name == "cfg_option" for rule in parser().rules
)
# Native analysis extensions may be present in a working checkout before they
# are published. Describe only the grammar shipped with this checkout, without
# importing optional runtime adapters or depending on uncommitted native code.
if not HAS_NATIVE_ANALYSIS_GRAMMAR:
    COMMAND_HELP["cfg"] = CommandHelp(
        "cfg",
        "Inspect the legacy control-flow command's current implementation boundary.",
        ("cfg FUNCTION",),
        (
            "FUNCTION: bare or qualified name. The legacy client hook is not implemented in this build.",
            "Native file selection and build options require the native analysis extension; no usable graph is returned here.",
        ),
        ("cfg one",),
    )
    COMMAND_HELP["callgraph"] = CommandHelp(
        "callgraph",
        "Inspect the legacy call-graph command's current implementation boundary.",
        ("callgraph [PATH]",),
        (
            "The legacy call-graph client hook is not implemented in this build.",
            "File selection parses, but the runtime rejects it until the native analysis extension is available.",
        ),
        ("callgraph",),
    )
    COMMAND_HELP["traverse"] = CommandHelp(
        "traverse",
        "Inspect the legacy AST traversal command's current implementation boundary.",
        ("traverse PATH",),
        (
            "PATH: quoted source file or reference. The grammar accepts this form, but execution is not implemented in this build.",
            "Native visitor options and execution require the native analysis extension.",
        ),
        ('traverse "examples/parse_match.cc"',),
    )
COMMAND_HELP["add extra_arg"] = replace(COMMAND_HELP["add"], topic="add extra_arg")

for setting, usage, detail, example in (
    (
        "traversal",
        "set [user] traversal MODE",
        "MODE: AsIs (default) or IgnoreUnlessSpelledInSource.",
        "set traversal IgnoreUnlessSpelledInSource",
    ),
    (
        "extra_args",
        "set [user] extra_args STRING_LIST",
        "STRING_LIST: ordered compiler arguments; default [].",
        'set extra_args ["-std=c++20"]',
    ),
    (
        "compile_commands",
        "set [user] compile_commands PATH",
        "PATH: server-side JSON file or directory; default null enables automatic discovery.",
        'set compile_commands "build"',
    ),
    (
        "cache_dir",
        "set [user] cache_dir to DIRECTORY",
        "DIRECTORY: quoted directory; default null. Stored setting; not forwarded by current console RPCs.",
        'set cache_dir to ".ctk-cache"',
    ),
    (
        "files",
        "set [user] files to FILE_LIST",
        "FILE_LIST: list of paths or File values, including glob results; directories are rejected. Default [].",
        'set files to glob("examples/*.cc")',
    ),
    (
        "output",
        "set [user] output to PATH_OR_STDOUT [mode replace]",
        "Default stdout. File output appends unless mode replace explicitly truncates it. Help and errors remain visible.",
        'set output to "results.txt"',
    ),
):
    topic = f"set {setting}"
    COMMAND_HELP[topic] = CommandHelp(
        topic,
        f"Set the {setting} configuration override.",
        (usage,),
        (
            detail,
            "Default scope: project ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.",
        ),
        (example,),
    )
    user_topic = f"set user {setting}"
    COMMAND_HELP[user_topic] = replace(
        COMMAND_HELP[topic],
        topic=user_topic,
        arguments=(
            detail,
            "Writes the user ~/.clang_tools.yaml layer; a project override still takes precedence.",
        ),
        examples=(example.replace("set ", "set user ", 1),),
    )

COMMAND_HELP["clear user"] = replace(
    COMMAND_HELP["clear"],
    topic="clear user",
    usage=("clear user KEY",),
    arguments=(
        "KEY: traversal, extra_args, compile_commands, cache_dir, files, output or vars.",
        "Removes the home-layer override; project overrides still take precedence. Runtime let bindings remain.",
    ),
    examples=("clear user output", "clear user traversal", "clear user extra_args"),
)
COMMAND_HELP["set user"] = replace(
    COMMAND_HELP["set"],
    topic="set user",
    usage=tuple(
        line.replace("set [user] ", "set user ") for line in COMMAND_HELP["set"].usage
    ),
    arguments=(
        "Writes ~/.clang_tools.yaml; project overrides still take precedence.",
        *COMMAND_HELP["set"].arguments[1:],
    ),
    examples=tuple(
        line.replace("set ", "set user ", 1) for line in COMMAND_HELP["set"].examples
    ),
)
COMMANDS = tuple(entry.topic for entry in _ENTRIES if " " not in entry.topic)


def render_help(statement: Tree) -> str:
    """Render a help statement already recognized by the shared Lark parser."""
    if statement.data == "help_shortcut":
        topic = " ".join(str(statement.children[0]).split())
    else:
        topic_tree = next(
            (child for child in statement.children if isinstance(child, Tree)), None
        )
        topic = (
            " ".join(map(str, topic_tree.children)) if topic_tree is not None else ""
        )
    if not topic:
        lines = ["Commands and expression forms (help is available without a server):"]
        lines.extend(f"  {name:12} {COMMAND_HELP[name].purpose}" for name in COMMANDS)
        lines.append(
            "Use help <command> or <command>? for usage, arguments, defaults and examples."
        )
        lines.append(
            "Multiword topics: help cursor open / cursor open?; help session add / session add?."
        )
        lines.append(
            "Examples using PATH need an existing source file; CURSOR_ID placeholders come from cursor open."
        )
        return "\n".join(lines)
    entry = COMMAND_HELP.get(topic)
    if entry is None:
        return f"unknown help topic: {topic}; use help to list commands"
    return entry.render()


def reference_markdown() -> str:
    """Generate the checked-in command reference from the same offline entries."""
    sections = [
        "# Console command reference",
        "",
        "Use `help COMMAND` or `COMMAND?` in the console. Multiword topics work too:",
        "`help cursor open` and `cursor open?` are equivalent. Help is local and remains",
        "visible when command output is redirected. Bare `help` lists all forms.",
        "",
        "Uppercase words are placeholders; brackets denote optional syntax. Examples",
        "use the checked-in `examples/parse_match.cc` fixture. Run them from the repository",
        "root with a native server for analysis operations. Use returned cursor IDs in",
        "place of `CURSOR_ID`; the console opens its query session automatically.",
        "",
    ]
    for entry in COMMAND_HELP.values():
        sections.extend(
            (
                f"## {entry.topic}",
                "",
                entry.purpose,
                "",
                "```text",
                *entry.usage,
                "```",
                "",
            )
        )
        sections.extend(f"- {argument}" for argument in entry.arguments)
        sections.extend(("", "```text", *entry.examples, "```", ""))
    return "\n".join(sections)
