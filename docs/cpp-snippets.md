# Parse temporary C++ snippets

Use a raw C++ literal when analysis needs new code rather than an existing file:

```text
let tree = parse cpp`
    int value = 7;
    value += 2;
`
let variables = match varDecl(hasName("value")).bind("variable") in tree
print variables.length
```

The default input is a statement block. The server creates a real temporary
`.cpp` file and inserts the block into a generated function:

```cpp
inline void ctk_snippet() {
    int value = 7;
    value += 2;
}
```

The literal preserves C++ quotes, backslashes, braces and newlines without CTK
interpolation. Escape an embedded backtick delimiter as `` \` ``; other C++
escapes remain unchanged. C++ parsing performs semantic analysis; it does not execute the
statements. The returned value is the same reusable parsed-tree type as
`parse "file.cpp"`, so matching and subsequent native analyses use the captured
tree. The temporary file is on the serving machine.

## Borrow an existing file's settings

`using` accepts a source path:

```text
let tree = parse cpp`
    TemplateType<MyTest> test;
    test.add(MyTest{});
` using "src/example.cpp"
```

The server borrows that file's compile command: language standard, target,
defines, include paths and working directory. It substitutes the temporary
`.cpp` as the input and strips source/output/dependency-generation operands.
The existing file is not modified or automatically included. Template/type
definitions still need to be visible to the snippet.

If `using` is omitted, the server selects the first compilation database entry
in database order. It uses the current explicit database or discovers one from
the working directory. If no database is found, explicit-flags/default parsing
applies. A found or explicitly selected database that is invalid or empty is an
error.
Select a donor explicitly when the project contains different compiler settings.

## Optional headers and overrides

An options object may be supplied directly or through a variable:

```text
let options = {
    file: "src/example.cpp",
    includes: ["template_type.hpp", "my_test.hpp"],
    compile_arguments: ["-DMY_TEST_MODE"]
}
let tree = parse cpp`
    TemplateType<MyTest> test;
    test.add(MyTest{});
` using options
let calls = match cxxMemberCallExpr().bind("call") in tree
print calls.length
```

All fields are optional:

| Field | Meaning |
| --- | --- |
| `file` | Existing source file whose compile command is borrowed. Omission selects the first database entry. |
| `includes` | Header names inserted before the generated function or complete source. |
| `compile_arguments` | Additional compiler options appended after borrowed flags. |
| `working_directory` | Working directory for resolving the request's paths and discovering settings. |
| `compilation_database` | Explicit `compile_commands.json` file or its directory. |
| `translation_unit` | `true` parses complete source without a function wrapper; default `false`. |

Headers, flags and paths refer to the server's filesystem. `includes` is not
required when the snippet is self-contained or existing compiler options already
provide declarations. Borrowing `-I` paths alone does not include a header.

Clang instantiates template specializations needed by the code, resolves
overloads, and checks types. An unused member body is not necessarily
instantiated. A successful probe establishes behavior for its concrete source,
type arguments and compile settings.

## Complete translation units

Use `translation_unit: true` for top-level definitions and source with its own
header directives:

```text
let tree = parse cpp`
    #include <type_traits>
    template <class T> int category(T value) {
        if constexpr (std::is_integral_v<T>) return value + 1;
        else return 0;
    }
    int probe() { return category<int>(7); }
` using {translation_unit: true, compile_arguments: ["-std=c++20"]}
let calls = match callExpr().bind("call") in tree
print calls.length
```

An `#include` in the default statement block appears inside its generated
function. For headers defining namespaces or templates, use the `includes`
option or complete translation-unit mode.

## Python API

Both `Client` and `AsyncClient` expose `parse_cpp`:

```python
from clang_toolkit import Client
from clang_toolkit.matchers import cxxMemberCallExpr

with Client(compilation_database="/project/build") as client:
    with client.parse_cpp(
        "TemplateType<MyTest> test; test.add(MyTest{});",
        file="src/example.cpp",
        working_directory="/project",
        includes=["template_type.hpp", "my_test.hpp"],
    ) as tree:
        with tree.match(cxxMemberCallExpr().bind("call")) as calls:
            print(len(calls))
```

`file`, `working_directory`, `compile_arguments`, `compilation_database`,
`includes`, `translation_unit` and `scope` are keyword arguments. The async
equivalent is `async with await client.parse_cpp(...) as tree`.

The server retains temporary source with its native snapshot, including derived
values and cache retention. Independent child results remain usable after
closing their parent tree. The file is removed when its final snapshot owner is
released, which can be later than closing a client value. Close retained values
normally and do not remove their temporary files manually.

Compiler diagnostics use snippet-relative line numbers. Match ranges use the
physical generated file's lines and offsets so source navigation opens the right
text, including any headers and function wrapper. Locations refer to temporary
source or included headers, not to the donor file as though its contents had
changed.

## Native scripts and wire API

The ANTLR server language accepts the same expression and options. Its statements
require semicolons and returned data uses `emit`:

```text
let tree = parse cpp`int value = 7;`;
let variables = match varDecl(hasName("value")).bind("variable") in tree;
emit count(variables);
```

`MatchService.Parse` accepts `ParseRequest.cpp_snippet` with `code`,
`settings_file`, optional `includes`, and `translation_unit`. Compilation
context and override fields remain on `ParseRequest`. `ParseResponse.source_file`
reports the server's parsed source path. Existing file requests remain supported.
Native-script emissions are detached semantic data when the request completes.
