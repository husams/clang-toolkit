# Interactive REPL input

Run `uv run ctk`. Enter submits a balanced command; an unmatched `(`, `[` or
`{` starts a continuation line, shown as `...> `. Delimiters must close in
nesting order. Delimiters inside single- or double-quoted strings are ignored,
including escaped quotes and backslashes. An unfinished string also continues
input. A mismatched closing delimiter is shown as an error that can be edited.
Ctrl+C cancels the current input and returns to a fresh prompt; Ctrl+D exits.
Bracketed paste preserves a multiline command for editing before submission.
Enter on an empty or whitespace-only line returns to a fresh prompt without
output or a history entry; type `help` to display help.

`help` lists commands and expression forms with their purpose. `help match` and
`match?` show equivalent local usage, arguments, defaults and examples, without
a running server. Multiword forms also work: `help cursor open` / `cursor open?`.
Unknown help topics and commands produce local errors. Help remains on the
console even when values are redirected to a file. The complete
[command reference](console-command-reference.md) includes declarative
`parse`/`match`/`let`/`in`/`yield` and the supported legacy controls.

Syntax errors for every command explain what input is expected and mark the
failure with a source line and caret. Missing closing quotes and delimiters
identify the required character; unknown commands suggest `help` and nearby
command names when available. For example:

```text
ctk> parse
syntax error at line 1, column 6: unexpected end of input. Expected a quoted path, a variable reference such as `$name`, a name, or a number.
parse
     ^
```

The prompt's validation line names invalid characters, mismatched closers and
missing quotes, delimiters or `done`, while its cursor marks the editable
location. Invalid `${...}` references show expected syntax and a caret within
the interpolation; missing `}` and invalid string escapes also name the
required correction and location.

```text
ctk> match functionDecl(
...>     hasName("Service::run")
...> ).bind("function")
```

Strings, numbers, matcher names, references, keywords, and punctuation have
separate styles. Highlighting uses the whole document, so strings and matcher
calls retain their categories across line breaks.

Tab completion follows the Lark parser's expected token roles at the cursor:

- At the prompt, it offers command keywords.
- After `match`, it offers root node matchers such as `functionDecl`,
  `cxxRecordDecl`, and `callExpr`; predicates and combinators are excluded.
- After `let name =`, it offers root and nested matcher constructors, including
  `hasType` and `pointerType`, alongside the new value forms.
- Inside a matcher argument list, it offers nested matcher expressions,
  including narrowing and traversal matchers.
- After `$`, it uses supplied reference names; after a reference's dot, it asks
  the live runtime for fields on the complete reference prefix. This supports
  nested properties and indexed rows such as `$functions[0].f.value.node.`.
  Completion descriptions distinguish fields from methods and label the active
  node payload, such as `cxx_method_decl`, with a hint to continue using `.`.
  Function nodes also offer concrete and inherited declaration fields directly,
  including `name`, `qualified_name` and `return_type`.
  `name` is typed: use `name.identifier` for ordinary names or `qualified_name`
  for the native qualified string. Exact schema paths remain available.
  Match values contain immediate node fields; child bodies and parameters are
  unrequested. Use a follow-up match to retrieve child nodes, and
  `return_type.description.spelling` to read a return type's text.
  `.joinWith(...)` joins list values; `.hasField(...)` checks field presence.
  These are methods. Completion does not invent names or scalar values.
  Inside `.hasField(`, Tab inserts quoted names of fields supporting presence,
  including inactive oneof branches. An empty argument explains the missing name.
- Ordinary command targets, assignment names, strings, and `.bind` string
  arguments do not receive unrelated matcher suggestions.
- In filesystem argument positions, Tab offers existing files and navigation
  directories. `set cache_dir to` offers directories only; `glob` accepts
  relative patterns and offers both files and directories. Source-file, load,
  save, history-save and output arguments offer files plus directory navigation.
  `session add`, `cursor open`, `script ... in`, `cfg ... in` and file-list
  arguments receive the same contextual completion.
- Relative paths use the session directory. Absolute paths are supported;
  `~/` expands to an absolute path on insertion. Spaces, quotes, backslashes
  and dollar signs in filenames are escaped for the console's string syntax.
  Completion closes unfinished quotes. Directory candidates end in `/`; press
  Tab again to list children, or type the next basename prefix and press Tab.
  A closing quote already to the right of the cursor is preserved. Missing or
  inaccessible directories produce no filesystem suggestions.
- Matcher strings, `.bind` names, script source, compiler arguments and ordinary
  string/list values receive no filesystem suggestions. Variable/field and
  matcher completion remain available in their own grammar roles.

The grammar declares root and nested matcher-name roles separately from ordinary
identifiers. Candidate providers select the appropriate catalog from those
roles; the prompt_toolkit adapter only renders and inserts the resulting
suggestions. Cursor handling and parser context are separate small modules.
The offline catalog is generated from LLVM 22.1.8's dynamic matcher registry:
209 concrete node constructors and 483 names reachable through its completion
contexts. Nested suggestions include `isExpansionInMainFile`,
`isExpansionInSystemHeader`, and `isExpansionInFileMatching`.
The server validates matcher availability and overloads against its own LLVM
build. To refresh the snapshot for a toolchain, run
`uv run python scripts/generate_matcher_catalog.py --llvm-config /path/to/llvm-config`.
Manual matcher spellings remain available.

The shared language definitions are in `python/clang_toolkit/cli/grammar.lark`.
The editor token rule recognizes incomplete strings, invalid characters, and
all three delimiter pairs. Lists and dictionaries are executable values;
braces also delimit scoped parsed-tree blocks with a terminal `yield`,
streamed match bodies and foreach statement bodies. See
[parse/match expressions](parse-match-expressions.md) for executable examples.
A multiline value-expression `foreach ... do` continues until `done`;
`foreach ... do { ... }` accepts statements separated by newlines or semicolons
and submits when its closing `}` is entered.
Retained match expressions collect rows through `StreamMatch` and spool large
collections to temporary storage. `let` publishes its reusable value only after
successful completion; failed or cancelled streams preserve earlier assignments.
Command dispatch now evaluates through modular `cli.runtime` modules. A session
keeps typed `let` bindings, composes matcher trees without textual substitution,
and expands references before calling the existing client API. Direct literal
matcher commands preserve their original multiline text.

```text
ctk> let m = hasType(pointerType())
ctk> let f = varDecl($m)
ctk> let r = match $f
ctk> $r
ctk> let files = glob("*.cpp")
ctk> $files.length
ctk> $files.isEmpty
ctk> $files.joinWith(", ")
ctk> foreach file in $files do "${file.basename}: ${file.size} bytes"
ctk> match $f in $files
ctk> let values = [1, 2, 3]
ctk> let lines = foreach x in $values do "value=${x}" done
ctk> $lines
ctk> foreach m in $r do {
...> print $m.root.decl_name
...> }
```

A bare `$name`, `print $name`, or a template string displays a value. `foreach`
may be single-line or `do`/`done` multiline; expression bodies return a list
that assignments capture without printing. Brace bodies execute statements
and produce only their explicit output. Declare the iterator with a plain name
and reference it with `$name` inside its body. Legacy `$name` declarations also
remain accepted. The iterator is scoped to its body. An empty `do {}` is a
statement block; `do {} done` evaluates an empty dictionary for each item.
For quoted field interpolation, use `${m.root.decl_name}`; short `$m` interpolation
includes only the variable name. `glob` resolves relative patterns against the session's
working directory and returns sorted `File` and `Directory` values. Printing
one shows its relative path. Both expose `.size`, `.modified`, `.basename`,
`.dirname`, `.absolute`, and `.parts`; `.size` and `.modified` are snapshots
from the glob call, and directory size is its filesystem entry size rather
than a recursive sum. The list exposes `.length`, `.isEmpty`, and
`.joinWith(", ")`. Matching accepts files and rejects directories.
Runtime names take precedence over environment and config-variable mappings;
`$env.NAME` and `$config.NAME` select a source explicitly.

For a selected match, `$lst[0].root.keys` lists readable AST fields, inherited
declaration fields and available conveniences such as `decl_name`. Read class
data with `$lst[0].root.record` or `$lst[0].root["record"]`, and its name with
`$lst[0].root.qualified_name` or `$lst[0].root.decl_name`. The list omits the
`node` carrier and serializer metadata, as well as absent or unrequested
fields. Explicit `.node`, `.value` and availability inspection remain usable.

Double-quoted strings interpolate `${name}` or the shorter `$name`, including
in matcher string arguments. Use `\$name` or `\${name}` to leave a dollar
reference literal. Single-quoted strings never interpolate, so `'$name'`
remains `$name`. Use `${file.basename}` for fields and
`${files.joinWith(', ')}` for list methods inside a template.

Settings are loaded from `/etc/clang_tools/config.yaml`, then
`~/.clang_tools.yaml`, then `./.clang_tools.yaml` (project wins). `set` and
`clear` save the project override automatically; `set user` / `clear user`
select the home file. Example commands:

```text
ctk> set traversal IgnoreUnlessSpelledInSource
ctk> set extra_args ["-std=c++23"]
ctk> add extra_arg "-Iinclude"
ctk> set cache_dir to "./.ctk-cache"
ctk> set files to glob("*.cpp")
ctk> clear traversal
ctk> save $lines to "lines"
ctk> save $lines to "lines.json" as json
ctk> let filename = "$HOME/lines.proto"
ctk> save $lines to $filename as proto
ctk> print "first line" to "lines.txt" mode replace
ctk> print "next line" to "lines.txt" mode append
ctk> load "lines" into $restored
ctk> set output to "results.txt"
ctk> set output to "results.txt" mode replace
ctk> set output to stdout
ctk> session label "pointer study"
ctk> history save "commands.jsonl"
```

The first save writes `lines.yaml`; the first output setting appends. JSON and
YAML and binary protobuf preserve typed values, while CSV accepts flat lists of primitive values
or records. Relative paths use the session's working directory; format is
detected from the extension (or a unique matching extension if omitted).
Destinations also accept string variables and double-quoted interpolation. See
[file output and resource management](file-output-resource-management.md) for
`server status`, `session list/attach/close`, `bindings`, and `cache status/prune`.
History is saved automatically to `$XDG_STATE_HOME/clang_tools/history.jsonl`
(or `~/.local/state/clang_tools/history.jsonl`) with a session UUID.
Up and Down recall earlier and later commands, including commands from previous
console runs. Ctrl+R searches backward through command history. Press Enter to
accept a search result, then Enter again to submit it. Multiline commands are
retained as one entry. Submitted syntax errors are also saved; cancelled edits
are not. `history clear` clears both saved history and interactive recall;
`history save PATH` exports the timestamped records.
The manual-console launcher uses the same persistent state location, rather
than storing history alongside its temporary server files.

Matching executes through the native server over Unix or TCP. Retained matching
uses the formal `cursor open`, `cursor continue`, `cursor restart` and
`cursor close` commands; see [result cursors](result-cursors.md) for revision,
selection, scope and cleanup semantics. Standalone traversal runs through
`traverse "file.cc" depth 12 nodes 10000`; see [AST traversal](ast-traversal.md).

Legacy `cfg FUNCTION` and bare `callgraph` are recognized but now report a local
missing-file error; supply the explicit file forms below.

`cfg ns::function in "file.cc" option add_implicit_dtors true blocks 10000`
returns typed native CFG graphs; see [CFG options](control-flow.md).

`callgraph "file.cc" nodes 10000 edges 100000 implicit true instantiations true`
returns the typed native AST call graph; see [native semantics](call-graphs.md).

`script "emit 7;"` runs the bounded server DSL. Add `in "file.cc"` for native query composition; see [server scripting](server-scripting.md).
