# Parse C++ snippets

Use `parse cpp` followed by a backtick literal to create a retained native tree
from temporary C++ code. The raw literal preserves C++ quotes, braces,
backslashes and newlines without CTK string interpolation. Escape an embedded
backtick as `` \` ``; other C++ escapes remain unchanged:

```text
let tree = parse cpp`
    int value = 7;
    value += 2;
`
let variables = match varDecl(hasName("value")).bind("variable") in tree
print variables.length
```

This is the complete [snippet_statements.ctk](../scripts/snippet_statements.ctk)
example. It prints `1`. CTK writes a real temporary `.cpp` file on the server
and places statements inside a generated function. No extra mode keyword is
required. Parsing checks C++ semantics without executing the code.

## Borrow compilation settings

Use a server-accessible source file as the donor when it has the compilation
settings required by the probe:

```text
let tree = parse cpp`
    int value = 7;
` using "src/example.cpp"
```

This borrows the file's compiler flags, include paths, defines, language standard
and command working directory. It does not include the source file or make its
declarations visible. Omit `using` to select the first compilation database entry
in database order. Select the current database with `--compile-commands` or
`set compile_commands`; automatic discovery is also supported. Prefer an explicit
donor when the project's files require different settings.

Use an options object when headers or compiler overrides are needed. Every
field is optional, and the object may be stored in a variable:

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

`includes` inserts headers before the generated function. Supply template/type
definitions through those headers or complete C++ source. A call instantiates
the specialization needed for that use; it does not force every unused member
body to instantiate. Compiler overrides append to the borrowed flags.

Supported options are `file`, `includes`, `compile_arguments`,
`working_directory`, `compilation_database` and `translation_unit`. Paths and
headers are interpreted on the server. If no database is found, explicit
flags/default C++ parsing apply. A found or selected invalid/empty database is
an error.

## Complete source

Set `translation_unit: true` to parse the literal without a generated function:

```text
let tree = parse cpp`
    template <class T> T identity(T value) { return value; }
    int probe() { return identity<int>(7); }
` using {translation_unit: true}
let calls = match callExpr().bind("call") in tree
print calls.length
```

Use this mode for top-level templates/functions and source containing its own
`#include` directives. Do not place a header defining namespaces or templates
inside the default statement wrapper; use `includes` instead.

## Run the template example

[snippet_template.ctk](../scripts/snippet_template.ctk) accepts `file` and
`header` as named arguments. Use the loaded skill's absolute directory, a known
project source file for borrowing, and the supplied fixture header:

```sh
ctk --script /absolute/skill/scripts/snippet_template.ctk \
    file=/project/src/example.cpp \
    header=/absolute/skill/assets/snippet_fixture.hpp
```

The server must see both paths. The fixture defines `TemplateType<T>` and
`MyTest`; the script prints one member call. Choose the user's configured
endpoint or an explicit `--server` as usual.

## Native server scripts and lifetime

The native server DSL supports the same `parse cpp` expression and `using`
forms. End statements with `;` and use `emit` to return results:

```text
let tree = parse cpp`int value = 7;`;
let variables = match varDecl(hasName("value")).bind("variable") in tree;
emit count(variables);
```

In the console, retain `tree` or its independent match results for further
matching, traversal, CFG or call-graph analysis. The server retains temporary
source with its snapshot and any cache retention, deleting the file only after
the final snapshot owner releases it; do not delete it yourself. Returned
native-script emissions remain detached data when the request ends. Source
locations distinguish generated source from included project headers. Compiler
diagnostics use snippet-relative lines; match ranges use physical generated-file
lines/offsets for navigation. Borrowing settings does not make the donor the
snippet's source file.
