# Console collections and library imports

Requested on 2026-10-09. Implementation stays in the console's Lark language;
native `script` remains the separate server language.

| Story | Acceptance | Status |
| --- | --- | --- |
| Dictionary values | Empty/nested literals, identifier/string keys, string indexing, keys/values, updates and deletion | Verified |
| List operations | Empty/nested literals, push/pop, indexed updates/deletion, useful collection methods | Verified |
| String operations | `split TEXT by SEPARATOR`, `join LIST with SEPARATOR` | Verified |
| Library imports | Shared variables/matcher definitions, relative nested `.ctk` paths, cycle/error handling | Verified |
| Text display | Valid UTF-8 bytes display as text, invalid bytes retain a readable fallback | Verified |
| Semantic property discovery | `$lst[1].root.keys`, readable direct AST fields and conveniences, map and binding-map keys | Verified |
| Binding and field export | Indexed bindings, semantic fields/containers, byte and enum values in detached snapshots | Verified |
| Direct binding data | `[binding].[key]` navigation, ordinary JSON/YAML without runtime type/value wrappers | Verified |
| Binding display | Bare `$lst[0].class` and print display the copied semantic value without `.value` | Verified |
| AST property exports | JSON/YAML omit serializer availability, completeness, continuation scopes and row provenance | Verified |
| Foreach statement blocks | Multiline brace bodies execute statements, close at `}`, and restore iterators | Verified |
| Foreach declaration consistency | `foreach m in $l do ...`, with `$m` references and legacy declarations retained | Verified |
| Quiet empty prompts | Enter on blank/whitespace input produces no output or history record; explicit help works | Verified |
| Matcher completion coverage | Offline registry snapshot includes system-header predicates and additional node constructors | Verified |
| Verification and reference | Unit/BDD coverage, full Python/native checks, syntax documentation | Verified |

Existing `$name` references and native matcher/semantic-view behavior must remain
compatible. Mutable user containers must not permit mutation of read-only
semantic views or introduce recursive container cycles.

Verification: 735 Python unit tests, all 296 native C++ tests and the complete
92-scenario console/native BDD suite pass. Prompt scenarios verify individual
Enter-key submission, quiet blank lines, and system-header matcher completion
against native matches. Native tests
use a private storage root to avoid the running server's cache ownership lock.
`git diff --check` passes. The checked-in console reference matches generated help.
The runnable `examples/collections.ctk` imports a variable/matcher library and
demonstrates all requested literal and string forms. Import failures restore
existing collection contents in place, preserving aliases. Libraries accept
`let` definitions and nested imports; their variables and matchers are shared
with the importing console. Imports resolve relative to the importing file.

Follow-up on 2026-10-10: matched semantic values expose a read-only `.keys`
property listing readable immediate and inherited fields. Absent, inactive,
unavailable and unrequested fields are excluded, as are methods. The same
property lists actual names on semantic maps and binding maps. Completion
offers `keys` as a property. The exact second-row expression passed a native
CLI scenario; the complete native suite passed all 296 tests again.

Binding and field export follow-up on 2026-10-10: `save $lst[0].root to
"data.yaml" as yaml` exports the binding's semantic fields. Rows and semantic
messages, repeated fields, maps, bytes and enums also save directly. JSON/YAML
use ordinary records/lists/scalars with no runtime `type`/`value` envelopes;
scalar booleans stay booleans. Protobuf snapshots restore read-only semantic
views with exact typed values and inherited availability metadata; they carry
no live native cursor identity. Selected repeated/map exports include only
their field's data. Unreadable fields are omitted; availability records remain
in typed protobuf snapshots. Malformed snapshot types are rejected before replacing an existing
variable. The native CLI scenario verifies reloaded field reads, raw YAML/JSON
booleans and continued matching from the original live binding.

Direct binding correction on 2026-10-10: read `[binding].[key]`, such as
`$lst[0].root.node` or `$lst[0].root.is_complete`, without a `.value` step.
Direct `.keys`, presence methods, string-key indexing and completion use the
same copied semantic values. Existing `.value` paths and native continuation
remain available. Ordinary JSON/YAML reload as detached records/lists; legacy
typed envelopes remain recognized by `load`, while `read` always preserves
document keys as written. UTF-8 bytes export as text; other bytes use a
`base64:` representation. Known enums use names and unknown enums use numbers.

Indexed binding display correction on 2026-10-10: bare `$lst[0].class` and
`print $lst[0].class` render the copied semantic binding through the existing
bounded renderer. They match the optional `.value` display without changing
the native selection. Aggregate/tree selections keep their existing label
display. A native Widget scenario verifies bare/print display, direct name
access, field-declaration continuation and display of a retained selection
after its cursor closes. The change runs in the console process; restarting
the server alone does not reload it.

AST export correction on 2026-10-10: JSON/YAML save the selected AST payload
directly, omitting the MatchBinding `node` carrier, availability records,
serializer completeness flags, continuation scopes and row source/index
provenance. Rows retain named payloads under `bindings`; collections retain
row order. Genuine AST fields, source locations and user dictionary keys
remain intact. Protobuf snapshots and live semantic navigation retain their
availability metadata. A native class scenario checks all binding/node/row
export paths, safe dictionary keys, protobuf availability and continued matching.
Binding exports retain copied source coordinates, ranges, symbol identity,
documentation and call-site facts. Descriptor-specific filtering also removes
nested serializer completeness flags while retaining `is_complete_definition`.
Inherited availability is enforced before exporting selected or nested payloads,
including a whole payload marked unrequested.

Foreach block correction on 2026-10-10: `foreach m in $lst do { ... }`
accepts newline/semicolon-separated statements and nested loops. Closing `}`
submits the command in the interactive prompt; value-expression loops continue
to use `done` for multiline input. Statement loops produce only their explicit
body output. Match rows select their root binding with `$m.root`; read its name
with `print $m.root.decl_name` or `print "${m.root.decl_name}"`.
Legacy expression and dictionary bodies retain their result-list behavior;
multiline statement blocks print only explicit output. Comment/newline spacing
between `do` and `{` is accepted, and a following batch statement retains its
newline separator. Nested block matches preserve their matcher text when no
original source slice is available.

Iterator declaration correction on 2026-10-10: use a plain name in both
statement and expression bodies, such as `foreach m in $lst do { ... }` and
`let names = foreach m in $lst do $m.root.decl_name done`. The `do` keyword
remains required; body references retain `$m`. Legacy `$m` declarations remain
accepted. A plain-name inline empty `do {}` is a silent statement block;
`do {} done` returns an empty dictionary per item.
Both declaration forms preserve multiline expression bodies and comment lines
before `done`. Ordinary following statements retain their batch separator.
The editor expands the parser's combined newline/`done` token back into
whitespace, comment and keyword tokens, preserving positions and highlighting.

Prompt and completion correction on 2026-10-10: blank input is a successful
no-op before parsing, runtime creation and history recording. Explicit help
remains unchanged. Completion uses a reproducible LLVM 22.1.8 registry snapshot
with 209 concrete node constructors and 483 reachable completion names,
including `isExpansionInSystemHeader` and `isExpansionInFileMatching`.
The generator is `scripts/generate_matcher_catalog.py`; its native registry
probe stays outside the server build. Completion suggestions do not expand
local predicate rejection; registry-confirmed node constructors such as
`pointerType` reach the server. Prompt tests complete and execute the system
header predicate against a marked header and verify a native pointer-type root.
The snapshot regenerates byte-for-byte from the current LLVM toolchain.

AST key-discovery correction on 2026-10-10: `$lst[0].root.keys` unwraps the
binding carrier and discovers readable AST payload fields, declaration base
fields and available `decl_name`/type conveniences. Class bindings expose
`record`, `qualified_name` and inherited declaration facts directly by dot or
string-key indexing. `node`, availability, completeness and continuation
scopes are omitted from this direct list; explicit metadata access remains
compatible. Unrequested parent payloads and inherited fields remain hidden.
The native class scenario reads every advertised key, saves `root.record`
and compares it with the full exported class record. Unit coverage also checks
direct field completion and blocked payload/name availability.
The complete 92-scenario BDD suite passes. Native verification combined 174
sequential checks with the remaining 122 checks using separate temporary
storage roots. One streaming test exceeded its five-second first-row deadline
under parallel load; it passed in isolation in 3.8 seconds without code changes.
