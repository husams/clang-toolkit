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

`ctk` (including `uv run ctk`) defaults to the compiled console engine. `python -m clang_toolkit.cli.app` and `scripts/manual_console.sh` retain the legacy default; add `--script-engine compiled` there to use the syntax in this reference. `--script-engine tree` selects the reference evaluator, and `--script-engine legacy` selects the previous parser. Compiled and tree share the language semantics described below. The server-side `script "SOURCE"`, SDK `run_script`, and server batch bodies use a separate native language; these console features do not add arithmetic, conditions, mutation, or value predicates to that language.

Endpoint/database paths above are examples; use supplied or configured values. `--script` executes console commands and exits; nonterminal stdin also runs as a script. Compiled and tree submissions stop at the first error. `--continue-on-error` is a legacy-engine batch option only. Relative analysis paths use the session directory. Imports use the importing library's directory; top-level imports use the script source directory.

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

## Compiled expressions, conditions, and predicates

The compiled console accepts checked arithmetic and comparisons, strict Boolean logic, value-producing branches, mutation, and five value-predicate families. Use these in expressions, conditions, collection entries, and `print`; the same parser runs interactive submissions, `--script`, `--execute`, and piped scripts.

| Form | Syntax | Behavior |
| --- | --- | --- |
| Arithmetic | `+ - * / %`, unary `+ -` | Integer `+`, `-`, `*` use checked signed 64-bit values; `/` returns finite floating point; `%` requires integers and truncates the quotient toward zero. Mixed integer/float operations require lossless conversion. |
| Comparison | `== != < <= > >=` | Scalar equality; booleans are distinct from numbers. Order numbers or two strings. Unsupported container/native-handle equality is an error. |
| Boolean logic | `not`, `and`, `or` | Requires Boolean operands and short-circuits. |
| Value selection | `if CONDITION then BODY else BODY`; `unless CONDITION do BODY [else BODY]`; `CONDITION ? VALUE : VALUE` | Branches are lazy. `if` and `unless` return the selected body's final value; an omitted `else` returns `null`. `then` and `do` introduce a one-statement body; braces group multiple statements. |
| Mutation | `$name = VALUE`, `$name += VALUE` (also `-= *= /= %=`) | Updates an existing binding or an owned list/dictionary entry; failure leaves its previous value intact. |
| Field presence | `$record has key`; `$record does not have key` | Bare, quoted, and grouped dynamic string keys are accepted. A present key whose value is `null` is still present. |
| List membership | `$value in $items`; `$value not in $items` | Searches a plain list using strict scalar equality; `true` and `1` are different. Search stops on the first match. |
| Exact node kind | `$row.item is CXXRecord`; `$row.item is not CXXRecordDecl` | Tests one selected semantic node's serialized kind. `CXXRecord` aliases `CXXRecordDecl`; other kinds match exactly. |
| Binding defined | `$name is defined`; `$name is not defined` | Accepts a root variable only and checks lookup without reading a missing name. |
| Binding set | `$name is set`; `$name is not set` | Also accepts only a root variable. Non-null values count as set, including `false`, `0`, and empty strings or containers. |

The example uses a source file containing a `Sample` record. Create it where the CTK server can read it, launch the compiled console, and submit the script:

```sh
cat > /tmp/ctk-script-predicates.cc <<'EOF'
struct Sample {};
EOF
uv run ctk
```

```text
let record = {a: null, enabled: false}
let key = "a"
let present = $record has a
let absent_key = $record does not have "missing"
let dynamic_key = $record has ($key)
let member = 2 in [1, 2, 3]
let not_member = 4 not in [1, 2, 3]
let missing_binding = $missing is not defined and $missing is not set
let null_value = $record.a
let null_state = $null_value is defined and $null_value is not set
let enabled = $record.enabled
let enabled_state = $enabled is set
let records = match cxxRecordDecl(hasName("Sample")).bind("item") in "/tmp/ctk-script-predicates.cc"
let node_kind = $records[0].item is CXXRecord and $records[0].item is CXXRecordDecl
let branch_value = if $present and $member then {
    let weighted = 3 * 7
    $weighted
} else 0
let mode = unless $enabled is set then "unset" else "set"
let label = $branch_value == 21 ? "present" : "absent"
print $present
print $absent_key
print $dynamic_key
print $member
print $not_member
print $missing_binding
print $null_state
print $enabled_state
print $node_kind
print $branch_value
print $mode
print $label
```

The outputs are nine `true` values, then `21`, `set`, and `present`. `is defined` and `is set` reject member/index expressions: bind a field to a root variable before testing it. A missing root binding makes both predicates false; a null binding is defined but unset. They follow the REPL's name-lookup precedence, including environment/configuration and lexical shadowing. `has` on semantic fields preserves existing unrequested/unavailable diagnostics; inspect `fieldState` when field availability matters. Membership checks consume execution budget as they inspect items and diagnose an unsupported or invalid numeric value only if reached, so an earlier match can safely stop before a bad tail. `is` requires one selected node with supported AST metadata, performs its kind check locally, and errors on unknown kinds or unsupported/missing payloads. `help predicates` shows the local plain or workspace Markdown reference.

Top-level newlines and semicolons separate statements; newlines inside parenthesised groups, lists, and dictionary literals are expression whitespace. Newlines separate statements inside brace blocks. The nearest unmatched `if` or `unless` claims `else`. From highest to lowest, expression precedence is member/index access, unary signs, `* / %`, `+ -`, comparisons and predicates, `not`, `and`, `or`, and conditional `?:` (right-associative). Chained comparisons/predicates are rejected; write `$low < $value and $value < $high`.

Use braces or one-statement bodies with compiled loops: `foreach row in $rows do { print $row.f.decl_name }` or `foreach row in $rows do $row.f.decl_name`. The legacy `do ... done` terminator and `--continue-on-error` are available only with `--script-engine legacy`.

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

Assigned operations are silent. Assigned brace `foreach` collects the last value of each iteration; a `let` contributes its assigned value. Explicit file writes still occur. The compiled engine accepts an unbraced one-statement loop body or a brace block; `do ... done` is legacy-only.

```text
let labels = ["first", "second"]
let pushed = $labels.push("third")
let final = $labels.pop()
let settings = {answer: 42, labels: $labels}
$settings["answer"] = 43
let parts = split "a/b" by "/"
let text = join $parts with ","
print $final
print $settings.answer
print $text
```

Mutations affect local collections, not native rows or source files. `.unique("f.symbol_identity")` keeps first occurrences, `.sort("f.decl_name")` sorts, and `.filter("f.decl_name", "demo::run")` uses equality. These methods do not imply SQL-style predicates or proposed foreach header clauses.

The collection example prints `third`, `43`, and `a,b` on separate lines. The method results are assigned so they do not also appear as unconsumed console values.

## Read text and CSV

`read PATH [as FORMAT]` reads files on the client computer. Formats are `json`, `yaml`, `text`, and `csv`; `.txt`/`.text` infer text and `.csv` infers CSV. Use `as text` for logs or extensionless files. Relative input paths use the session directory.

Text is a list of UTF-8 lines with line endings removed; spaces and blank lines remain. `.strip()` removes surrounding whitespace, and `.strip(chars)` removes the specified characters at either end. CSV is a list of dictionaries keyed by the header row; every cell remains a string, including `002`. Headers with spaces need string-key indexing. Quotes, embedded commas/newlines, and UTF-8 BOMs work; duplicate/empty headers and uneven rows fail. Use `read` for ordinary input; `load` also understands CTK's saved-value formats.

For a names file and a CSV with `name,count` columns, the complete `inputs.ctk` is:

```text
let lines = read $arg.names as text
let names = foreach line in $lines do {
    $line.strip()
}
print $names.joinWith("|")
let people = read $arg.people as csv
foreach person in $people do {
    print $person.name.strip()
    print $person.count
}
```

Run it with `ctk inputs.ctk names=names.txt people=people.csv`. Supply files matching that header schema; use `.keys` or the actual headers when adapting it to another CSV. For example, `names.txt` can contain ` Alice ` and ` Bob ` on separate lines, and `people.csv` can contain `name,count` followed by ` Alice ,002` and ` Bob ,3`. With those inputs, it prints `Alice|Bob`, then each name and its count (`002` stays a string). The text loop returns each line after explicitly removing surrounding whitespace; without `.strip()` the original spaces and blank lines remain. The brace bodies are the compiled form; legacy scripts may also use `do ... done`.

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

- `python/clang_toolkit/cli/app.py` (script arguments, `prototype_main` compiled default, and engine overrides)
- `python/clang_toolkit/cli/runtime/persistence.py` (text and CSV reads)
- `python/clang_toolkit/cli/runtime/prototype/grammar.lark` (compiled console syntax)
- `python/clang_toolkit/cli/runtime/prototype/repl_language.py` (combined console/native command parser)
- `python/clang_toolkit/cli/runtime/prototype/semantics.py` (checked expressions, limits, mutation, and predicates)
- `python/clang_toolkit/cli/runtime/prototype/native_predicates.py` (native presence and exact node-kind checks)
- `python/clang_toolkit/cli/runtime/prototype/help.py` (`help predicates` output)
- `tests/unit/test_prototype_predicates.py`
- `tests/e2e/test_prototype_repl_steps.py`
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
