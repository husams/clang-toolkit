# Typed matchers and semantic values

## Build matcher trees

```python
from clang_toolkit import Matcher
from clang_toolkit.matchers import (
    functionDecl, hasName, isDefinition, isExpansionInMainFile,
    unless, isImplicit, callExpr, callee, declRefExpr, to, cxxRecordDecl,
)

query = functionDecl(
    isDefinition(), isExpansionInMainFile(), unless(isImplicit())
).bind("fn")
```

`Matcher(name, *args)` is an immutable matcher call. `.bind("label")` returns a bound copy, `.to_query()` returns the DSL serialization, and `str(matcher)` is equivalent. Pass matcher objects directly to `match_in` or `ParsedTree.match`. The builder composes and serializes calls; the server remains the authority on matcher existence, arity, and AST-category compatibility. A local matcher-construction success is not proof the server accepted or matched it.

The native matcher parser preserves string contents literally. The builder
chooses a quote delimiter absent from the value, preserving backslashes,
Unicode and newlines. A string containing both single and double quotes has no
lossless native literal representation and raises `ValueError`. Do not apply
JSON escaping to native matcher arguments. The generated text follows the
native matcher grammar; console expression quoting is a separate grammar.

The matcher module follows Clang AST matcher spellings and exports common declarations, expressions, predicates, and combinators. Use names documented by this reference or supplied in the task. If the server rejects a matcher, report the diagnostic and reformulate using supported matchers; do not inspect SDK or target source files to discover a hidden API.

## Read binding values safely

```python
from clang_toolkit import Client
from clang_toolkit.matchers import functionDecl, isDefinition

with Client() as client:
    with client.match_in(functionDecl(isDefinition()).bind("fn"), source) as functions:
        for row in functions:
            fn = row.binding("fn")
            proto = row.bindings["fn"]
            print(fn.decl_name, fn.decl_type, proto.symbol_identity)
            value_kind = proto.WhichOneof("value")
            if value_kind == "node":
                payload_name = proto.node.WhichOneof("payload")
                print(payload_name)
                payload = getattr(proto.node, payload_name) if payload_name else None
                if payload is not None:
                    print([field.name for field, value in payload.ListFields()])
            elif value_kind == "qualified_type":
                print(proto.qualified_type.description.spelling,
                      proto.qualified_type.description.qualifiers)
            elif value_kind == "unsupported":
                print(proto.unsupported)
            elif value_kind == "base_specifier":
                print(proto.base_specifier)
```

`BindingSelection` offers scalar shortcuts `decl_name`, `decl_type`, `parameter_name`, `record_name`, and `type_name`. Its `.value` is a copied `MatchBinding` protobuf; when its `value` branch is `node`, the AST payload is `.value.node`. The object in `row.bindings["fn"]` is already the copied `MatchBinding` protobuf; when its `value` branch is `node`, the AST payload is `.node`, and its copied metadata fields are read directly from it. Use `row.to_dict()` for a copied plain mapping when that helps inspection, but this does not create additional evidence.

`MatchBinding` has a `value` oneof; check `proto.WhichOneof("value")` before reading a semantic value. The current branches are `node`, `qualified_type`, `unsupported`, and `base_specifier`. Only the `node` branch has the AST-node `payload` oneof, so only then call `proto.node.WhichOneof("payload")`. For `qualified_type`, read immediate type facts from `proto.qualified_type.description` (including `spelling` and `qualifiers`) and its `qualifiers`; do not read or compare `.node`. For `unsupported`, inspect `proto.unsupported` and the binding's coverage metadata. For `base_specifier`, inspect its typed value directly; it is not an `AstNode` payload or an independently matchable continuation root.

For unfamiliar node kinds, first check `WhichOneof("value")`; for the `node`
branch, use `WhichOneof("payload")`, `ListFields()`, and `row.to_dict()` to
inspect the returned SDK value without reading source or SDK files. Follow the
returned payload's fields and availability metadata. Optional message presence
uses `HasField`; repeated fields use `len`. The `unsupported` branch is explicit:
inspect its payload and coverage metadata rather than assuming the node does not
exist.

Match bindings carry immediate facts. Bodies, parameter lists, operands, initializers, and other child AST nodes are commonly marked `FIELD_STATE_UNREQUESTED`; an absent protobuf field alone does not prove the C++ construct lacks that field. Inspect the binding's `availability` entries (`field_path`, `state`, and optional `reason`) and check protobuf presence with `HasField("field")` where applicable. Distinguish `PRESENT`, `SEMANTICALLY_ABSENT`, `UNREQUESTED`, `INAPPLICABLE`, `UNAVAILABLE`, and `TRUNCATED`. Query an unrequested child through a follow-up matcher instead of expanding assumptions from its parent.

Console-only helpers such as `fieldState(...)` and `fieldOr(...)` belong to the console's semantic view wrapper; they are not methods on the copied protobuf binding. In SDK code, use protobuf fields, `HasField`, and the binding's `availability` metadata.

For top-level function bindings, `FunctionDeclInfo.is_this_declaration_a_definition`
has explicit PRESENT metadata even when its optional boolean is false. The body
of a declaration that does not own one is SEMANTICALLY_ABSENT; an owning body is
UNREQUESTED in a shallow binding, and PRESENT when recursive expansion returns its
typed body value. PRESENT does not imply complete descendants: inspect
`is_complete` and descendant availability separately.
For a top-level non-alias `TemplateSpecializationType`, `aliased_type` is
INAPPLICABLE. These explicit states cover native producer facts, not every schema
field. Availability paths describe message fields rather than unique child
instances; query a child directly before assigning it a state from aggregate
parent metadata. Expansion failures remain TRUNCATED or UNAVAILABLE.

For a function declaration whose binding's `value` branch is `node`, the explicit protobuf paths are `node.function_decl.function.declarator.value.named.qualified_name` and `node.function_decl.function.return_type.description.spelling`. `named` carries named-declaration metadata; its `name` is a typed `DeclarationName` with different variants for identifiers, operators, constructors, and other special names. Other declaration kinds have different payload paths. Read field availability and protobuf presence before accessing optional branches. These schema paths are examples for the function-declaration payload; do not assume they apply to every bound node.

## Follow-up matches and row joins

```python
from clang_toolkit.matchers import functionDecl, isDefinition, parmVarDecl

with client.match_in(functionDecl(isDefinition()).bind("fn"), source) as functions:
    parent = functions[0]
    with parent.binding("fn").match(parmVarDecl().bind("param")) as params:
        for row in params:
            param = row.binding("param")
            print(param.decl_name, param.decl_type)
```

`BindingSelection.match(...)` queries the selected bound node using the selection's scope. `MatchValue.binding(...)` and `MatchRow.binding(...)` accept the public keyword `scope`, whose default is native subtree scope. Decl/Stmt bindings support inclusive subtree continuation. For native Type/QualType bindings, pass `scope=1` (`BINDING_MATCH_SCOPE_ROOT_ONLY`) explicitly; their advertised `supported_scopes` contains only root scope, and a default subtree continuation fails with `CursorError` / `FAILED_PRECONDITION`. Inspect the copied binding's `supported_scopes` before choosing a scope.

```python
from clang_toolkit import Client
from clang_toolkit.matchers import functionDecl, isDefinition, isExpansionInMainFile, hasType, qualType

with Client() as client:
    with client.match_in(
        functionDecl(
            isDefinition(), isExpansionInMainFile(),
            hasType(qualType().bind("ty")),
        ).bind("fn"), source,
    ) as functions:
        for row in functions:
            ty = row.bindings["ty"]
            assert ty.WhichOneof("value") == "qualified_type"
            assert ty.qualified_type.description.HasField("spelling")
            print(ty.qualified_type.description.spelling,
                  ty.qualified_type.description.qualifiers)
            assert 1 in ty.supported_scopes
            with row.binding("ty", scope=1).match(qualType().bind("same_type")) as types:
                assert len(types) == 1
```

Each continuation is independent and retains its source tree. Continuation rows have `source_match_index` when they came from a previous selection; it indexes the immediate input row in that per-file source result. It is not a flattened index across files. Preserve the original parent order for joins.

Overlapping roots and duplicate selections can produce repeated rows. Preserve multiplicity unless the question explicitly asks for deduplication. Empty results are valid results; a missing binding label is a query error, not evidence of no matching nodes.
