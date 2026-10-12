# Console scripts

## Launch and syntax

```sh
ctk
ctk --server unix:///tmp/ctk.sock
ctk --server unix:///tmp/ctk.sock --compile-commands /project/build/compile_commands.json
ctk --script /absolute/path/analysis.ctk
ctk /absolute/path/analysis.ctk x=gggg 'message=hello world'
ctk --execute 'let xs = [1, 2]; print $xs.length'
ctk --execute 'print $arg.x' x=gggg
```

Endpoint/database paths above are examples; use supplied or configured values. `--script` executes console commands and exits; nonterminal stdin also runs as a script. Execution stops at the first failure by default. Use `--continue-on-error` only when later commands are independent. Relative analysis paths use the session directory. Imports use the importing library's directory; top-level imports use the script source directory.

`ctk SCRIPT KEY=VALUE ...` also runs the file and exits. Script, inline, and piped runs expose a dictionary named `arg`: use `$arg.x` or `$arg["x"]`. Values are literal strings, including empty values, spaces inside a quoted argument, and any `=` after the first separator. Names are trimmed; missing/empty names and duplicate names are errors before execution. With no parameters, `$arg` is `{}`. Imported libraries share the same arguments.

The complete `analysis.ctk` for the named-argument command above is:

```text
print $arg.x
print $arg.message
```

It prints `gggg` and `hello world`. For piped input, `printf '%s\n' 'print $arg.x' | ctk x=gggg` prints `gggg`. Use `--script FILE` when a filename itself contains `=`. Script arguments populate batch runs; interactive sessions do not receive this dictionary automatically.

For console-only interaction, allocate a TTY (`exec_command` with `tty: true`). The repository's `scripts/manual_console.sh` can start a private disposable server for validation; exit stops that server.

In `--script`/`--execute` and interactive submissions, newlines or semicolons separate top-level commands. In the workspace, paste a complete script and use Ctrl+Enter or Ctrl+J to execute it; Alt+Enter or Shift+Enter adds another line while typing. The console validates the whole submission before execution, runs statements in order with shared bindings, stops at the first error or exit, and records one history entry. Prefer semicolons inside blocks. Comments use `#`. Declare names without `$`; references use `$name`. Double-quoted strings interpolate `$name` and `${path.to.field}`; single quotes are literal. Escape a dollar in double quotes when literal text is intended.

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

## Read text and CSV

`read PATH [as FORMAT]` reads files on the client computer. Formats are `json`, `yaml`, `text`, and `csv`; `.txt`/`.text` infer text and `.csv` infers CSV. Use `as text` for logs or extensionless files. Relative input paths use the session directory.

Text is a list of UTF-8 lines with line endings removed; spaces and blank lines remain. `.strip()` removes surrounding whitespace, and `.strip(chars)` removes the specified characters at either end. CSV is a list of dictionaries keyed by the header row; every cell remains a string, including `002`. Headers with spaces need string-key indexing. Quotes, embedded commas/newlines, and UTF-8 BOMs work; duplicate/empty headers and uneven rows fail. Use `read` for ordinary input; `load` also understands CTK's saved-value formats.

For a names file and a CSV with `name,count` columns, the complete `inputs.ctk` is:

```text
let lines = read $arg.names as text
let names = foreach line in $lines do $line.strip() done
print $names.joinWith("|")
let people = read $arg.people as csv
foreach person in $people do {
    print $person.name.strip();
    print $person.count;
}
```

Run it with `ctk inputs.ctk names=names.txt people=people.csv`. Supply files matching that header schema; use `.keys` or the actual headers when adapting it to another CSV.

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

- `python/clang_toolkit/cli/app.py` (script arguments and execution modes)
- `python/clang_toolkit/cli/runtime/persistence.py` (text and CSV reads)
- `tests/unit/test_script_arguments.py`
- `tests/e2e/test_script_arguments_steps.py`
- `tests/e2e/test_console_collections_imports_steps.py`
- `tests/e2e/test_workspace_console_steps.py`
- `docs/console-command-reference.md`
- `docs/parse-match-expressions.md`
- `docs/expression-values.md`
- `python/clang_toolkit/cli/grammar.lark`
- `~/workspace/wiki/pages/planning/clang-toolkit-console-design.md`
- `~/workspace/wiki/pages/planning/clang-toolkit-projection-filtering-grouping.md` (draft)
