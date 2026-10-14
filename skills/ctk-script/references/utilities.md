# Bundled CTK utilities

Import [ctk_helpers.ctk](../scripts/ctk_helpers.ctk) into the **compiled console**.
Resolve its absolute path from the active skill directory; this installation uses:

```ctk
import "/Users/husam/.codex/skills/ctk-script/scripts/ctk_helpers.ctk"
let tree = parse "/project/src/widget.cpp"
let info = classInfo(tree, "demo::Leaf")
let hierarchy = ancestors(tree, "demo::Leaf")
print info
print hierarchy
```

These are imported executable functions and matcher definitions, not built-in
commands. Imports define dormant values; analysis starts when a helper is called.
Use a single parsed translation unit with correct compiler flags, keep it live
until the calls finish, and prefer fully qualified names. `target` accepts that
parsed tree or another ordinary match target; parsing once avoids repeated work.
Native query errors propagate: do not wrap every helper in an empty fallback.

## Live class lookup

`classByName(target, className)` returns a live class binding. `target` accepts
a parsed tree, live node, or source filename. Prefer a parsed tree for repeated
queries. Missing or ambiguous definitions raise an error with the matching count;
duplicate matches with the same symbol identity collapse to one definition.

```ctk
let node = classByName(tree, "demo::Leaf")
print classMethods(node)
print classFields(node)
print directBases(node)
let fromFile = classByName("/project/src/widget.cpp", "demo::Leaf")
```

`classMethods(node, includeImplicit = false)` takes a live node and an optional
Boolean. To select by name, use `classMethods(classByName(tree, "demo::Leaf"))`
or `classInfo(tree, "demo::Leaf").methods`. Keep the binding's native session live
while using it; saving a node as JSON does not preserve its navigation handle.

## Class information

`classInfo(target, className, includeImplicit = false)` returns a dictionary:

| Key | Meaning |
| --- | --- |
| `status` | `"ok"`, `"not_found"`, or `"ambiguous"`. Check this before reading other fields. |
| `class` | `{name, display_name, id, file, line, kind, template}`. Names are qualified where available, `id` is symbol identity and `kind` is a `TAG_KIND_*` string. `display_name` includes all specialization arguments; `template` is null for ordinary classes. |
| `fields` | Direct non-static fields: identity/location, type, `access`, `mutable`, `bit_field`, `anonymous_record`. |
| `static_fields` | Direct static data members: identity/location, type, `access`, `constexpr`. |
| `methods` | Direct methods, member templates, constructors, destructors and conversions. Overloads retain separate entries and identities. |
| `bases` | Immediate inheritance edges, including alias spelling, resolved class identity, visibility and virtualness. |
| `nested_classes` | Direct nested class definitions, separately from their containing class's members. |

`access` is `"public"`, `"protected"`, `"private"`, or `"none"`; it includes C++
default access. Methods report `kind`, function `type`, `return_type` (null for
constructors/destructors), `static`, `virtual`, `pure`, `override_written`, `const`,
`volatile`, `ref_qualifier`, `implicit`, `constexpr`, `variadic`, and `parameters`.
`override_written` means an explicit override attribute; it is not a full override
graph. `ref_qualifier` is a `REF_QUALIFIER_*` string.

Each parameter reports identity/location, name, type, zero-based `index`, and
`has_default`. Defaults are queried from the AST, not inferred from an unrequested
serialized expression. Parameter queries exclude parameters of nested lambdas.
Neither default-expression text nor method bodies are expanded.

Only members declared in the selected class are included. Inherited members and
members of nested classes stay separate. Implicit methods are excluded unless
requested; even then the result contains only declarations Clang has materialized
in this AST. Missing/ambiguous lookups return `candidates` instead of an invented
empty class. Repeated matches of the same class identity are collapsed; use one
translation unit rather than merging differing definitions across files.

```ctk
let info = classInfo(tree, "demo::Leaf")
if info.status == "ok" then {
    foreach field in info.fields do print "{field.access}: {field.type} {field.name}"
    foreach method in info.methods do print "{method.access}: {method.type} {method.name}"
    save info to "/absolute/output/class-info.json" as json
} else print info
```

For a live class binding, use the smaller helpers directly:

```ctk
let rows = match definedClass("demo::Leaf").bind("cls") in tree
if rows.length == 1 then {
    let node = rows[0].cls
    print classFields(node)
    print classStaticFields(node)
    print classMethods(node)
    print directBases(node)
}
```

## Class templates and specializations

`classTemplateInfo(target, className)` returns `{status, class, template,
specializations}` for a template, `not_template` for an ordinary class, or
`not_found`/`ambiguous` with candidates. A bare template name selects its primary
class definition. An exact specialization `display_name` selects that concrete
class; include every argument, including defaults, using Clang's displayed
spacing. Specializations retain distinct symbol identities even though their
`name` is the same bare qualified template name.

```ctk
let templates = classTemplateInfo(tree, "demo::Box")
foreach variant in templates.specializations do print variant.display_name
let concrete = classByName(tree, "demo::Box<int, 3>")
print classFields(concrete)
```

Each `template` contains `kind` (`primary`, `partial_specialization`, or
`specialization`), the qualified `primary` name, `parameters`, `arguments`, and
`specialization_kind` (null on the primary). The latter distinguishes explicit
specializations from implicit or explicit instantiations using Clang's
`DECL_TEMPLATE_SPECIALIZATION_KIND_*` values. Parameter descriptions report
`kind`, `name`, optional `type`, `pack`, and nested `parameters` for template
template parameters. Argument descriptions report `kind`, semantic `spelling`,
optional `type`, and pack `elements`. These are semantic descriptions, not source
text; dependent parameter types may use Clang's `type-parameter-*` spelling.
Default-expression text and constraints are not included.

`specializations` includes definitions visible in the supplied target, including
partial patterns and materialized instantiations. It does not instantiate unused
templates or search other translation units. A specialization's `parameters`
describes its own partial pattern, if any; query the primary for its parameters.
The server supplies bounded scalar template facts on shallow bindings, without
expanding member bodies or full AST argument trees. Native limits still apply;
unavailable facts raise errors. Use the matching updated server and client.

## Inheritance tree and levels

`ancestors(target, className, maxDepth = 32)` returns `{status, tree, levels,
complete}` on success. `tree` includes the selected class at depth zero and a
recursive `bases` list. Each node has identity/location/kind, its incoming `edge`
(null at the root), and `truncated`, `unresolved`, and `cycle` flags.

Every edge has `{type, access, virtual, pack_expansion, resolved, class}`. `type`
keeps the spelling of an alias; `class` identifies the desugared declaration or
is null for an unresolved dependent base. Edge access describes that one direct
inheritance relation; it does not calculate a member's effective access through
an entire path.

`levels[0]` contains the direct bases; `levels[1]` their bases; later lists contain
successive ancestor levels. The selected class is excluded from `levels`; a class
without bases returns an empty list. The selected class remains the `tree` root
as traversal context. Every level entry has `name`, `id`, `via` (parent name) and
`edge`, plus `display_name` and `template` for specialization identity. A diamond preserves both paths to the same class, including virtual
edges. This is a path tree, not a deduplicated object layout or ancestor set.

For the bundled fixture, the names and incoming access follow:

```text
demo::Leaf
  public demo::Left (written LeftAlias)
    public virtual demo::Root
  private demo::Right
    protected demo::Root
```

The routine uses an iterative queue and resolves definitions before continuing,
so forward declarations do not silently become leaves. Supply a non-negative
integer depth. At the depth boundary it marks nodes with further bases as
`truncated` and sets `complete=false`; a negative depth returns `invalid_depth`.
Unresolved bases and a repeated identity on the same path also set
`complete=false`. Missing or ambiguous roots return the same lookup statuses and
candidate list as `classInfo`. Ordinary native limits/cancellation raise errors
instead of returning a completed partial tree. Default execution/item budgets
still bound very large or exponentially branching inheritance trees.

```ctk
let hierarchy = ancestors(tree, "demo::Leaf", 64)
if hierarchy.status == "ok" then {
    print hierarchy.complete
    foreach level in hierarchy.levels do print level
    save hierarchy to "/absolute/output/inheritance.json" as json
} else print hierarchy
```

All helper summaries except the live `classByName` binding contain plain dictionaries/lists/scalars. They can be
saved and loaded; they do not retain navigation handles. `peek parents` means
AST containment and is distinct from this inheritance walk.

## Other utilities and inline callbacks

| Function | Result |
| --- | --- |
| `functionInfo(target, name)` | List of matching function definitions, preserving overloads; identity/location, signature, return type, constexpr/variadic flags and parameters. Empty when no definitions match. |
| `callSites(target, calleeName)` | List of statically resolved calls with file/line, caller/callee names and identities, and `CALL_DISPATCH_*` kind. Missing caller information is null. |
| `mapValues(items, operation)` | List of callback results in input order. Callback receives one item. |
| `filterValues(items, predicate)` | Original items whose callback returns Boolean true, in input order. |

```ctk
print functionInfo(tree, "demo::work")
print callSites(tree, "demo::sink")
let doubled = mapValues([1, 2, 3], (value) = value * 2)
let selected = filterValues(doubled, (value) = value > 2)
print selected
let safe = mapValues([2, 0, 5], (value) = {
    on error 0
    10 / value
})
print safe
```

`selected` holds `[4, 6]` and `safe` holds `[5.0, 0, 2.0]`; `print` renders
list items on separate lines. Named runnable callbacks work too.
`callSites` does not resolve indirect calls or dynamic virtual dispatch to runtime
targets. Keep live native operations within the lifetime of their input handles;
plain-value callback helpers need no native target.

## Ready-made matchers

These definitions return composable native matchers. Bind the **routine call**
inside `match`; assigning a matcher value alone does not run a query.

| Matcher | Selects |
| --- | --- |
| `definedClass(name)` | Named class/struct definitions, excluding implicit injected declarations. |
| `definedFunction(name)` | Named function definitions, excluding implicit declarations. |
| `methodsOfClass(name)` | Direct methods of the named class, excluding implicit declarations; constructors/destructors are included. |
| `publicMethodsOfClass(name)` | The public subset of those direct methods. |
| `fieldsOfClass(name)` | Non-static fields declared in that class. |
| `derivedFrom(name)` | Class definitions transitively derived from the named base. |
| `callsTo(name)` | Call expressions with that statically known callee. |

```ctk
let classes = match definedClass("demo::Leaf").bind("cls") in tree
let methods = match publicMethodsOfClass("demo::Leaf").bind("method") in tree
let fields = match fieldsOfClass("demo::Root").bind("field") in tree
let derived = match derivedFrom("demo::Root").bind("cls") in tree
let calls = match callsTo("demo::sink").bind("call") in tree
print classes.length
print methods.length
print fields.length
print derived.length
print calls.length
```

For [utility_fixture.cc](../assets/utility_fixture.cc), the counts are
`1`, `7`, `3`, `3`, `1`. Matchers include headers and use Clang's normal qualified
name matching. Add verified native constraints in a new matcher definition when
needed; the helpers do not assume main-file-only analysis or deduplicate overloads.

## Verification and maintained sources

The fixtures cover class templates, partial/full specializations, concrete
instantiations, nested template parameters, variadic packs, forward declarations,
alias bases, a diamond, virtual/public/
protected/private inheritance, overloads, static/mutable/bit fields, member
visibility, constructors/destructors, a member template, nested classes/lambda
parameters, a default argument, unresolved template bases, ambiguous names and
plain callbacks. The BDD acceptance scenarios run the actual CLI against
an isolated native server: `uv run python -m pytest tests/e2e/test_ctk_skill_helpers_steps.py -m e2e -q`.

Maintain this library against `api/ast/v1/semantic_types.proto`, declaration
serializers under `server/src/clang/serialization/decl/`, native navigation and
binding-field availability. Test executable bodies against the sources listed in
[runnables.md](runnables.md). Do not replace unrequested semantic fields with empty
collections or add blanket `on error` fallbacks to claim complete results.
