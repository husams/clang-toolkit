# Interactive REPL input

Run `uv run ctk`. Enter submits a balanced command; an unmatched `(`, `[` or
`{` starts a continuation line, shown as `...> `. Delimiters must close in
nesting order. Delimiters inside single- or double-quoted strings are ignored,
including escaped quotes and backslashes. An unfinished string also continues
input. A mismatched closing delimiter is shown as an error that can be edited.
Ctrl+C cancels the current input and returns to a fresh prompt; Ctrl+D exits.
Bracketed paste preserves a multiline command for editing before submission.

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
- After `$`, it uses supplied reference names; after a reference's dot, supplied
  fields. It does not invent names or scalar values.
- Ordinary command targets, assignment names, strings, and `.bind` string
  arguments do not receive unrelated matcher suggestions.

The grammar declares root and nested matcher-name roles separately from ordinary
identifiers. Candidate providers select the appropriate catalog from those
roles; the prompt_toolkit adapter only renders and inserts the resulting
suggestions. Cursor handling and parser context are separate small modules.
The catalog follows the [Clang matcher categories](https://clang.llvm.org/docs/LibASTMatchersReference.html#node-matchers).
It is an extensible offline subset, not a complete Clang overload/type checker;
manual matcher spellings remain available for the server to validate.

The shared language definitions are in `python/clang_toolkit/cli/grammar.lark`.
The editor token rule recognizes incomplete strings, invalid characters, and
all three delimiter pairs. Lists are executable values; braces are currently
reserved. A multiline `foreach ... do` continues until `done`.
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
ctk> foreach $file in $files do "${file.basename}: ${file.size} bytes"
ctk> match $f in $files
ctk> let values = [1, 2, 3]
ctk> let lines = foreach $x in $values do "value=${x}" done
ctk> $lines
```

A bare `$name`, `print $name`, or a template string displays a value. `foreach`
may be single-line or `do`/`done` multiline; assignments capture its list
without printing. `glob` resolves relative patterns against the session's
working directory and returns sorted `File` and `Directory` values. Printing
one shows its relative path. Both expose `.size`, `.modified`, `.basename`,
`.dirname`, `.absolute`, and `.parts`; `.size` and `.modified` are snapshots
from the glob call, and directory size is its filesystem entry size rather
than a recursive sum. The list exposes `.length`, `.isEmpty`, and
`.joinWith(", ")`. Matching accepts files and rejects directories.
Runtime names take precedence over environment and config-variable mappings;
`$env.NAME` and `$config.NAME` select a source explicitly.

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
ctk> load "lines" into $restored
ctk> set output to "results.txt"
ctk> set output to "results.txt" mode replace
ctk> set output to stdout
ctk> session label "pointer study"
ctk> history save "commands.jsonl"
```

The first save writes `lines.yaml`; the first output setting appends. JSON and
YAML preserve typed values, while CSV accepts flat lists of primitive values
or records. Relative paths use the session's working directory; format is
detected from the extension (or a unique matching extension if omitted).
History is saved automatically to `$XDG_STATE_HOME/clang_tools/history.jsonl`
(or `~/.local/state/clang_tools/history.jsonl`) with a session UUID.

The existing server transport remains a stub, so a real `match`, `cfg`, or
`callgraph` still cannot execute until the API and C++ server are connected.
The request/session protocol and automatic server cleanup remain the next
implementation slice; see
`~/workspace/wiki/pages/planning/clang-toolkit-interactive-runtime.md`.
