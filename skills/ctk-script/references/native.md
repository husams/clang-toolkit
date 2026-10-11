# Native server scripts

## Invoke deliberately

```text
script "emit 7;"
script "emit count(match(\"functionDecl(isDefinition())\"));" in "/project/src/widget.cpp"
script 'let functions = match functionDecl(isDefinition()).bind("f"); emit count(functions);' in "/project/src/widget.cpp"
```

This submits ANTLR server source; `--script FILE` executes the console DSL. Build inner source before escaping its outer string; escape native `$` references as `\$` inside the outer double-quoted console string to prevent console interpolation. Avoid multiple shell quoting layers.

Prefer native expression-form matchers inside a single-quoted outer console string, as in the third example, when possible. The outer string still decodes escape sequences: single quotes suppress interpolation but do not remove the need to escape nested matcher-string quotes correctly.

Substantial native source is clearer in its own code block:

```text
let functions = match("functionDecl(isDefinition()).bind(\"f\")");
emit count(functions);
foreach function in functions {
    emit continue(function, "f", "parmVarDecl().bind(\"p\")");
}
```

This requires a request target. Public SDK execution is `client.run_script(source, path="/project/src/widget.cpp", max_steps=100)`; use it when the user chooses SDK execution. Console `script` passes working directory and configured compiler flags. Returned typed ScriptResponse emissions are detached from native handles when the request ends.

## Language rules

- Assignments, emissions, and expression statements end with `;`. Comments use `//`.
- Strings are double-quoted with JSON escapes. Console interpolation and single quotes are not native string syntax.
- `let` declares immutable lexical bindings. Duplicate names in one scope fail; inner shadowing is allowed.
- References accept identifiers or `$name`. Lists, objects, member/index access and grouped expressions are supported.
- Legacy loops: `foreach item in items { emit item; }`. Value loops: `foreach item in $items do { $item; }`, with a semicolon when used as an expression statement.
- Use `emit` to return values. Final expressions are not automatically emitted by ordinary requests. `collect_final` explicitly adds the detached final value as `__final__`.
- Member syntax does not guarantee console semantic conveniences or methods. Verify native field support separately; `count`, `row`, and `continue` are established row operations.

```text
let settings = {answer: 42, labels: ["first", "second"]};
let labels = foreach label in $settings.labels do { $label; };
emit $settings.answer;
emit $labels[1];
```

Native expressions also accept `parse "PATH"`, `match functionDecl().bind("f") in TARGET`, and `in TREE { ... yield VALUE; }`. This does not make all console commands available on the server.

| Function | Role |
| --- | --- |
| `match("MATCHER")` | Match default target; optional traversal `"as_is"`/`"spelled"`. |
| `continue(rows, "binding", "MATCHER")` | Captured-binding continuation; optional scope `"subtree"`/`"root"`. |
| `restart(rows, "MATCHER")` | Match whole pinned AST. |
| `row(rows, index)` | Select zero-based original row. |
| `count(value)` | Count supported rows/lists/files/traversal/graph data. |
| `traverse(max_depth=2)` | TraverseRequest options except file. |
| `cfg("exact::function", ...)` | Exact qualified function with CfgOptions. |
| `callgraph(...)` | Per-translation-unit static graph; request options except file. |

Console `flatten` concatenates **one level**; checked native code recursively flattens nested collections. Verify the installed version before relying on this difference (`emit flatten([[1, [2]], [3]]);` yields `[1, 2, 3]` in the checked native test).

## Bounds and exports

Syntax is checked before evaluation. Default budget is 100 steps including calls/statements/iterations; `max_steps` accepts 1..10,000. Bounds include 1 MiB source, 100,000 tokens, nesting 64 and 16 MiB retained values. Collection has a separate 10,000-item/1-MiB run bound; response and native snapshot budgets also apply. Ordinary script errors/cancellation/limits return no partial emissions; durable batch partial-success reports are separate.

`save VALUE to PATH as json|proto;` publishes a typed ScriptValue envelope on the **serving machine** through atomic replacement. Console JSON contains ordinary records and console proto uses SavedValue instead. Use requested destinations. The DSL exposes no shell, network, or dynamic code execution functions.

## Sources

- `docs/server-scripting.md`
- `docs/parse-match-expressions.md` (Native block execution)
- `server/src/script/grammar/CtkScript.g4`
- `server/tests/test_script_engine.cpp`
