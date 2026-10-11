# Console scripts

## Launch and syntax

```sh
ctk
ctk --server unix:///tmp/ctk.sock
ctk --server unix:///tmp/ctk.sock --compile-commands /project/build/compile_commands.json
ctk --script /absolute/path/analysis.ctk
ctk --execute 'let xs = [1, 2]; print $xs.length'
```

Endpoint/database paths above are examples; use supplied or configured values. `--script` executes console commands and exits; nonterminal stdin also runs as a script. Execution stops at the first failure by default. Use `--continue-on-error` only when later commands are independent. Relative analysis paths use the session directory. Imports use the importing library's directory; top-level imports use the script source directory.

For console-only interaction, allocate a TTY (`exec_command` with `tty: true`). The repository's `scripts/manual_console.sh` can start a private disposable server for validation; exit stops that server.

In `--script`/`--execute`, newlines or semicolons separate top-level commands. The interactive prompt parses one top-level command per submission: submit separate commands separately, or use a supported brace block for multiple statements. Prefer semicolons inside blocks. Comments use `#`. Declare names without `$`; references use `$name`. Double-quoted strings interpolate `$name` and `${path.to.field}`; single quotes are literal. Escape a dollar in double quotes when literal text is intended.

To create a reusable script using only the console, use `print 'SCRIPT TEXT' to "/absolute/output/analysis.ctk"` with literal string escapes for newlines, and `mode append` for additional chunks. Execute that file through the real CLI's `--script` option. The private validation launcher supports `bash scripts/manual_console.sh --script /absolute/output/analysis.ctk` and supplies its own endpoint; `server status` does not expose the connection endpoint in the checked console, so do not infer an endpoint from status metrics or filesystem paths.

## Match and extract fields

Substitute a server-accessible target for `/project/src/widget.cpp`:

```text
let tree = parse "/project/src/widget.cpp";
let functions = match functionDecl(isDefinition()).bind("f") in $tree;
print $functions.length;
foreach row in $functions do {
    print $row.f.qualified_name;
    print $row.f.return_type.description.spelling;
}
```

On a nonempty result, `$functions[0].f.keys` and `inspect $functions[0].f` discover fields. `$functions[0].f` selects one binding; `$functions.f` selects that label across all rows. Unbound matchers add `root`. Use direct declaration fields (`qualified_name`, `decl_name`, `decl_type`, `symbol_identity`) where supported. `.value.node` is a compatibility path, not needed for ordinary scripts. Binding `.keys` lists semantic properties.

Matches are shallow. Children such as bodies, parameters, initializers, and operands can be `UNREQUESTED` even with `is_complete=true` for the immediate projection. Use `.fieldState("parameters")` on the relevant semantic view. `hasField` raises for unrequested data; `fieldOr` defaults only for absent/inapplicable data. Retrieve children through matching:

```text
let parameters = match parmVarDecl().bind("p") in $functions.f;
foreach row in $parameters do {
    print $row.p.decl_name;
    print $row.source_match_index;
}
let calls = match callExpr().bind("c") in $functions.f;
foreach row in $calls do {
    print $row.c.call_site.static_callee_name;
}
```

`source_match_index` identifies the immediate parent row within the originating file's retained match result. On a combined multi-file collection it can restart at zero for each file: do not index the combined parent collection with it. Use `source_file` to choose the matching file's parent collection first, or retain and continue each file independently when correlating children to parents. Server-reported paths may be canonicalized (the tested macOS `/tmp` target appeared under `/private/tmp`); do not rely on literal path spelling alone. Continuation includes each selected root and descendants; relationship predicates may inspect the full AST. Virtual/indirect static callees do not establish runtime targets.

## Matchers, loops, collections

```text
let named(name) = functionDecl(hasName($name));
let functions = match named("demo::run").bind("f") in "/project/src/widget.cpp";
let names = foreach row in $functions do {
    $row.f.qualified_name;
};
print $names;
```

Assigned operations are silent. Assigned brace `foreach` collects the last value of each iteration; a `let` contributes its assigned value. Explicit file writes still occur. Expression loops can use `foreach row in $functions do $row.f.qualified_name done`.

```text
let labels = ["first", "second"];
push labels, "third";
let final = pop labels;
let settings = {answer: 42, labels: $labels};
set settings['answer'] = 43;
print $settings.answer;
let parts = split "a/b" by "/";
let text = join parts with ",";
print $text;
```

Mutations affect local collections, not native rows or source files. `.unique("f.symbol_identity")` keeps first occurrences, `.sort("f.decl_name")` sorts, and `.filter("f.decl_name", "demo::run")` uses equality. These methods do not imply SQL-style predicates or proposed foreach header clauses.

## Scope and exports

```text
let calls = in parse "/project/src/widget.cpp" {
    let functions = match functionDecl(isDefinition()).bind("f");
    let selected = match callExpr().bind("c") in $functions.f;
    yield selected;
};
save $calls to "/absolute/output/calls.json" as json;
```

`in` requires a parsed tree and exactly one terminal `yield`; locals disappear on exit, while yielded live results retain required resources. JSON/YAML exports contain ordinary data; CSV requires flat lists; proto uses the typed SavedValue envelope. Exported/loaded rows cannot reconstruct continuation handles. `print ... to PATH` writes rendered output; `save` writes structured data. Use requested destinations. Exit releases session-owned values; consult `help close`/`help file close` for selective release.

`import "lib/matchers.ctk"` loads `let` definitions, matcher routines and nested imports, not arbitrary analysis commands.

## Sources

- `docs/console-command-reference.md`
- `docs/parse-match-expressions.md`
- `docs/expression-values.md`
- `python/clang_toolkit/cli/grammar.lark`
- `~/workspace/wiki/pages/planning/clang-toolkit-console-design.md`
- `~/workspace/wiki/pages/planning/clang-toolkit-projection-filtering-grouping.md` (draft)
