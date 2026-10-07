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
        ("match MATCHER [in TARGET]", "let rows = match MATCHER [in TARGET]"),
        (
            'MATCHER: root matcher call or $matcher; .bind("name") names a selected node.',
            "TARGET: quoted file path, File, file list, parsed tree, match value or binding selection.",
            "Without in: use the enclosing block tree, otherwise configured files (default []).",
            "Rows use zero-based indices: $rows[0].binding; $rows.binding selects that binding across rows.",
            "Uses extra_args (default []) and traversal (default AsIs); server validates matcher types.",
        ),
        (
            'match functionDecl().bind("f") in "examples/parse_match.cc"',
            'let rows = match functionDecl().bind("f") in "examples/parse_match.cc"',
            "match callExpr() in $rows.f",
        ),
    ),
    CommandHelp(
        "let",
        "Bind a typed expression without printing it.",
        ("let NAME = VALUE",),
        (
            "NAME: identifier without $. References use $name, fields and zero-based [index].",
            "VALUE: matcher, literal, list, reference, glob, parse, match, foreach or scoped block.",
            "Matcher construction is local; parse/match require a server. Failed evaluation preserves the prior binding.",
        ),
        (
            'let predicate = hasName("main")',
            "let matcher = functionDecl($predicate)",
            'let files = glob("examples/*.cc")',
            "let rows = match $matcher in $files",
        ),
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
        ("print VALUE", "$reference", "QUOTED_STRING"),
        (
            "VALUE: any value expression. Output defaults to stdout; let is silent.",
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
        "Map a list expression using a scoped iterator.",
        (
            "foreach $NAME in LIST do VALUE [done]",
            "let results = foreach $NAME in LIST do VALUE done",
        ),
        (
            "LIST must evaluate to a list (at most 10000 elements); the body is one value expression.",
            "The iterator shadows outer names only during the body. A multiline do requires done.",
            "Returns a list; let captures it silently. Errors report the element index.",
        ),
        (
            'let files = glob("examples/*.cc")',
            'foreach $file in $files do "${file.basename}" done',
        ),
    ),
    CommandHelp(
        "glob",
        "Create sorted File and Directory values from a relative pattern.",
        ("let files = glob(QUOTED_PATTERN)",),
        (
            "Patterns are relative to the session directory; ** recurses. Absolute patterns are rejected.",
            "No matches returns []; maximum 10000 entries. File/Directory metadata is a snapshot.",
            "Properties: size, modified, basename, dirname, absolute, parts. Match rejects directories.",
        ),
        ('let files = glob("examples/*.cc")', "match varDecl() in $files"),
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
            "set [user] output to PATH_OR_STDOUT [mode replace]",
        ),
        (
            "Default scope: ./.clang_tools.yaml; user scope: ~/.clang_tools.yaml.",
            "Precedence: project > user > /etc/clang_tools/config.yaml > built-in defaults.",
            "traversal: AsIs (default) or IgnoreUnlessSpelledInSource. extra_args: [] by default.",
            "cache_dir: quoted directory, default null. files: list of paths/Files, default [].",
            "output: quoted file or stdout (default). Files append; mode replace truncates.",
            "cache_dir is a persisted console setting; these console operations do not forward it as an RPC option.",
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
        "Persist an evaluated variable as detached data.",
        ("save $REFERENCE to PATH [as FORMAT]",),
        (
            "PATH: quoted output file, relative to the session directory.",
            "FORMAT: yaml, json or csv; inferred from suffix, yaml when no suffix (adds .yaml).",
            "YAML/JSON preserve typed values. CSV supports flat primitive/record lists.",
            "Exported native rows are detached and cannot be reused as live match targets.",
        ),
        (
            "let values = [1, 2, 3]",
            'save $values to "values"',
            'save $values to "values.json" as json',
        ),
    ),
    CommandHelp(
        "load",
        "Load persisted data into a simple variable.",
        ("load PATH into $NAME",),
        (
            "PATH: quoted existing file; formats .yaml/.yml, .json and .csv.",
            "Without suffix: probe those extensions and require a unique match.",
            "NAME must be a simple variable. Failed loading preserves its prior value.",
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
        "Clear the local persisted command history.",
        ("history clear",),
        ("No arguments or options; history must be enabled.",),
        ("history clear",),
    ),
    CommandHelp(
        "session",
        "Label local history or control an opted-in legacy bidirectional query.",
        (
            "session label STRING",
            "session start QUERY_STRING",
            "session add PATH",
            "session match",
            "session pause",
            "session resume",
            "session close",
        ),
        (
            "label is local. All other operations require launching ctk --session.",
            "See help session <subcommand>. Use parse/match/in/yield for declarative analysis.",
        ),
        ('session label "study functions"',),
    ),
    CommandHelp(
        "session label",
        "Set the local history label without changing its UUID.",
        ("session label STRING",),
        ("STRING: quoted label; default is no label. Does not require --session.",),
        ('session label "study functions"',),
    ),
    CommandHelp(
        "session start",
        "Define the legacy bidirectional session query.",
        ("session start QUERY_STRING",),
        (
            "Requires ctk --session. QUERY_STRING is a quoted matcher expression, not a path.",
            "Uses configured extra_args and the session working directory.",
        ),
        ('session start "functionDecl()"',),
    ),
    CommandHelp(
        "session add",
        "Add a source file to a legacy bidirectional session.",
        ("session add PATH",),
        (
            "Requires ctk --session. PATH: quoted file path; uses configured extra_args and the session directory.",
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
        ("Requires ctk --session and a started query; no arguments or options.",),
        (
            'session start "functionDecl()"',
            'session add "examples/parse_match.cc"',
            "session match",
        ),
    ),
    CommandHelp(
        "session pause",
        "Pause legacy bidirectional query feedback.",
        ("session pause",),
        ("Requires ctk --session; no arguments or options.",),
        ("session pause",),
    ),
    CommandHelp(
        "session resume",
        "Resume legacy bidirectional query feedback.",
        ("session resume",),
        ("Requires ctk --session; no arguments or options.",),
        ("session resume",),
    ),
    CommandHelp(
        "session close",
        "Close the legacy bidirectional query session.",
        ("session close",),
        ("Requires ctk --session; no arguments or options. The console remains open.",),
        ("session close",),
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
        "Visit a file's AST and display typed semantic nodes.",
        (
            "traverse PATH [depth NUMBER] [nodes NUMBER] [implicit BOOL] [instantiations BOOL]",
        ),
        (
            "PATH: quoted source file or path/File reference. BOOL: true or false.",
            "depth: 0..256, default 64. nodes: 1..100000, default 10000.",
            "implicit/instantiations: false by default. Each option may occur once.",
            "Uses configured extra_args and the session directory.",
        ),
        ('traverse "examples/parse_match.cc" depth 12 nodes 10000',),
    ),
    CommandHelp(
        "cfg",
        "Build control-flow graphs for an exact qualified function name in a file.",
        (
            "cfg FUNCTION in PATH [option NAME BOOL] [functions NUMBER] [blocks NUMBER] [elements NUMBER]",
        ),
        (
            "FUNCTION: bare, qualified or quoted exact name. PATH: quoted file or path/File reference.",
            "option NAME BOOL: a CfgOptions boolean field. prune_trivially_false_edges defaults to true; others to false.",
            "Option names: " + ", ".join(CfgOptions.DESCRIPTOR.fields_by_name),
            "functions: 1..1000 (default 100); blocks: 1..100000 (default 10000); elements: 1..1000000 (default 100000).",
            "Options may occur once. Uses configured extra_args. Legacy cfg FUNCTION is recognized but reports a local error requiring in PATH.",
        ),
        (
            'cfg one in "examples/parse_match.cc" option add_implicit_dtors true blocks 10000',
        ),
    ),
    CommandHelp(
        "callgraph",
        "Build the native AST call graph for a file.",
        (
            "callgraph PATH [nodes NUMBER] [edges NUMBER] [implicit BOOL] [instantiations BOOL]",
        ),
        (
            "PATH: quoted file or path/File reference. nodes: 1..100000 (default 10000).",
            "edges: 1..1000000 (default 100000). Options may occur once.",
            "Omitted implicit/instantiations use Clang CallGraph defaults (both true).",
            "Uses configured extra_args. Bare legacy callgraph is recognized but reports a local error requiring a path.",
        ),
        ('callgraph "examples/parse_match.cc" nodes 10000 edges 100000',),
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
        "place of `CURSOR_ID`; session controls require `ctk --session`.",
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
