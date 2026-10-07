# Console command reference

Use `help COMMAND` or `COMMAND?` in the console. Multiword topics work too:
`help cursor open` and `cursor open?` are equivalent. Help is local and remains
visible when command output is redirected. Bare `help` lists all forms.

Uppercase words are placeholders; brackets denote optional syntax. Examples
use the checked-in `examples/parse_match.cc` fixture. Run them from the repository
root with a native server for analysis operations. Use returned cursor IDs in
place of `CURSOR_ID`; session controls require `ctk --session`.

## help

Explain console syntax locally; no server is required.

```text
help [command [subcommand]]
command [subcommand]?
```

- No topic: list commands. A topic: purpose, usage, arguments and examples.
- Help and errors always appear in the console, regardless of output routing.

```text
help match
parse?
help cursor open
cursor open?
```

## parse

Parse a file and retain its native tree as a value.

```text
parse PATH
let tree = parse PATH
```

- PATH: quoted file path or a reference to a path/File; relative to the session directory.
- Uses configured extra_args (default []) and requires the native server.
- Use the result with match ... in $tree or a scoped in $tree block.

```text
parse "examples/parse_match.cc"
let tree = parse "examples/parse_match.cc"
```

## match

Match native nodes and optionally retain the resulting rows.

```text
match MATCHER [in TARGET]
let rows = match MATCHER [in TARGET]
```

- MATCHER: root matcher call or $matcher; .bind("name") names a selected node.
- TARGET: quoted file path, File, file list, parsed tree, match value or binding selection.
- Without in: use the enclosing block tree, otherwise configured files (default []).
- Rows use zero-based indices: $rows[0].binding; $rows.binding selects that binding across rows.
- Uses extra_args (default []) and traversal (default AsIs); server validates matcher types.

```text
match functionDecl().bind("f") in "examples/parse_match.cc"
let rows = match functionDecl().bind("f") in "examples/parse_match.cc"
match callExpr() in $rows.f
```

## let

Bind a typed expression without printing it.

```text
let NAME = VALUE
```

- NAME: identifier without $. References use $name, fields and zero-based [index].
- VALUE: matcher, literal, list, reference, glob, parse, match, foreach or scoped block.
- Matcher construction is local; parse/match require a server. Failed evaluation preserves the prior binding.

```text
let predicate = hasName("main")
let matcher = functionDecl($predicate)
let files = glob("examples/*.cc")
let rows = match $matcher in $files
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
print VALUE
$reference
QUOTED_STRING
```

- VALUE: any value expression. Output defaults to stdout; let is silent.
- Double quotes interpolate $name/${reference}; single quotes are literal.
- Escape a dollar as \$ in double quotes. Lists expose length, isEmpty and joinWith(separator).

```text
let values = [1, 2, 3]
print $values
$values.length
"count=${values.length}"
```

## foreach

Map a list expression using a scoped iterator.

```text
foreach $NAME in LIST do VALUE [done]
let results = foreach $NAME in LIST do VALUE done
```

- LIST must evaluate to a list (at most 10000 elements); the body is one value expression.
- The iterator shadows outer names only during the body. A multiline do requires done.
- Returns a list; let captures it silently. Errors report the element index.

```text
let files = glob("examples/*.cc")
foreach $file in $files do "${file.basename}" done
```

## glob

Create sorted File and Directory values from a relative pattern.

```text
let files = glob(QUOTED_PATTERN)
```

- Patterns are relative to the session directory; ** recurses. Absolute patterns are rejected.
- No matches returns []; maximum 10000 entries. File/Directory metadata is a snapshot.
- Properties: size, modified, basename, dirname, absolute, parts. Match rejects directories.

```text
let files = glob("examples/*.cc")
match varDecl() in $files
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
set [user] cache_dir to DIRECTORY
set [user] files to FILE_LIST
set [user] output to PATH_OR_STDOUT [mode replace]
```

- Default scope: ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.
- Precedence: project > user > /etc/clang_tools/config.yaml > built-in defaults.
- traversal: AsIs (default) or IgnoreUnlessSpelledInSource. extra_args: [] by default.
- cache_dir: quoted directory, default null. files: list of paths/Files, default [].
- output: quoted file or stdout (default). Files append; mode replace truncates.
- cache_dir is a persisted console setting; these console operations do not forward it as an RPC option.

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

- KEY: traversal, extra_args, cache_dir, files, output or vars.
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

Persist an evaluated variable as detached data.

```text
save $REFERENCE to PATH [as FORMAT]
```

- PATH: quoted output file, relative to the session directory.
- FORMAT: yaml, json or csv; inferred from suffix, yaml when no suffix (adds .yaml).
- YAML/JSON preserve typed values. CSV supports flat primitive/record lists.
- Exported native rows are detached and cannot be reused as live match targets.

```text
let values = [1, 2, 3]
save $values to "values"
save $values to "values.json" as json
```

## load

Load persisted data into a simple variable.

```text
load PATH into $NAME
```

- PATH: quoted existing file; formats .yaml/.yml, .json and .csv.
- Without suffix: probe those extensions and require a unique match.
- NAME must be a simple variable. Failed loading preserves its prior value.

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

Clear the local persisted command history.

```text
history clear
```

- No arguments or options; history must be enabled.

```text
history clear
```

## session

Label local history or control an opted-in legacy bidirectional query.

```text
session label STRING
session start QUERY_STRING
session add PATH
session match
session pause
session resume
session close
```

- label is local. All other operations require launching ctk --session.
- See help session <subcommand>. Use parse/match/in/yield for declarative analysis.

```text
session label "study functions"
```

## session label

Set the local history label without changing its UUID.

```text
session label STRING
```

- STRING: quoted label; default is no label. Does not require --session.

```text
session label "study functions"
```

## session start

Define the legacy bidirectional session query.

```text
session start QUERY_STRING
```

- Requires ctk --session. QUERY_STRING is a quoted matcher expression, not a path.
- Uses configured extra_args and the session working directory.

```text
session start "functionDecl()"
```

## session add

Add a source file to a legacy bidirectional session.

```text
session add PATH
```

- Requires ctk --session. PATH: quoted file path; uses configured extra_args and the session directory.

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

- Requires ctk --session and a started query; no arguments or options.

```text
session start "functionDecl()"
session add "examples/parse_match.cc"
session match
```

## session pause

Pause legacy bidirectional query feedback.

```text
session pause
```

- Requires ctk --session; no arguments or options.

```text
session pause
```

## session resume

Resume legacy bidirectional query feedback.

```text
session resume
```

- Requires ctk --session; no arguments or options.

```text
session resume
```

## session close

Close the legacy bidirectional query session.

```text
session close
```

- Requires ctk --session; no arguments or options. The console remains open.

```text
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
- row: zero-based unsigned index; omitted selects all rows. scope: subtree (default) or root_only.
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

Inspect the legacy AST traversal command's current implementation boundary.

```text
traverse PATH
```

- PATH: quoted source file or reference. The grammar accepts this form, but execution is not implemented in this build.
- Native visitor options and execution require the native analysis extension.

```text
traverse "examples/parse_match.cc"
```

## cfg

Inspect the legacy control-flow command's current implementation boundary.

```text
cfg FUNCTION
```

- FUNCTION: bare or qualified name. The legacy client hook is not implemented in this build.
- Native file selection and build options require the native analysis extension; no usable graph is returned here.

```text
cfg one
```

## callgraph

Inspect the legacy call-graph command's current implementation boundary.

```text
callgraph [PATH]
```

- The legacy call-graph client hook is not implemented in this build.
- File selection parses, but the runtime rejects it until the native analysis extension is available.

```text
callgraph
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

- KEY: traversal, extra_args, cache_dir, files, output or vars.
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
set user cache_dir to DIRECTORY
set user files to FILE_LIST
set user output to PATH_OR_STDOUT [mode replace]
```

- Writes ~/.clang_tools.yaml; project overrides still take precedence.
- Precedence: project > user > /etc/clang_tools/config.yaml > built-in defaults.
- traversal: AsIs (default) or IgnoreUnlessSpelledInSource. extra_args: [] by default.
- cache_dir: quoted directory, default null. files: list of paths/Files, default [].
- output: quoted file or stdout (default). Files append; mode replace truncates.
- cache_dir is a persisted console setting; these console operations do not forward it as an RPC option.

```text
set user extra_args ["-std=c++20"]
set user files to glob("examples/*.cc")
set user output to "results.txt"
set user output to stdout
```
