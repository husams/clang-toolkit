# Analyze temporary C++ snippets

Use `parse_cpp` to ask a structural question about new C++ code, including how a
template specializes for a concrete type. Use the public SDK through the loaded
skill's Python launcher, as described in [launch-and-api.md](launch-and-api.md).
Keep source/configuration discovery on the server; do not inspect project files
to discover compilation settings.

## Statement blocks

`parse_cpp` creates a real temporary `.cpp` file on the server and inserts the
source into a generated function. It performs parsing and semantic analysis;
it does not execute the statements.

```python
from clang_toolkit import Client
from clang_toolkit.matchers import varDecl, hasName

with Client() as client:
    with client.parse_cpp("int value = 7; value += 2;") as tree:
        with tree.match(varDecl(hasName("value")).bind("variable")) as variables:
            assert len(variables) == 1
            print(variables[0].binding("variable").decl_type)
```

`file` and `includes` are optional. If `file` is omitted, CTK uses the first
entry in the selected or automatically discovered compilation database, in
database order. If no database is found, explicit flags/default parsing apply;
a found or selected invalid/empty database is an error. Do not claim a snippet
used project settings unless a project
database or donor was selected. Prefer an explicit donor when files have
different flags.

## Concrete template probes

Borrow the known source file's compilation settings with `file=source`.
Borrowing transfers flags, defines, include paths, language standard, and the
command's working directory. It does not import the file's declarations or
change that file. Template definitions and argument types must be visible in
headers supplied through `includes` or in complete translation-unit source.

For a project exposing `TemplateType<T>` and `MyTest` in the named headers:

```python
from clang_toolkit import Client
from clang_toolkit.matchers import cxxMemberCallExpr

with Client() as client:
    with client.parse_cpp(
        "TemplateType<MyTest> test; test.add(MyTest{});",
        file=source,
        includes=["template_type.hpp", "my_test.hpp"],
    ) as tree:
        with tree.match(cxxMemberCallExpr().bind("call")) as calls:
            print("member calls:", len(calls))
```

The call causes Clang to analyze the specialization required by this use. An
unused member body need not be instantiated. Continue from the returned call
bindings or match declarations in the same tree when the requested question
needs overload, type, or method-body evidence. Keep template instantiations in
the selected traversal when inspecting generated specialization nodes.

`working_directory`, `compilation_database`, and `compile_arguments` are also
accepted; additional compiler arguments append overrides to the borrowed
command. These paths and headers refer to the serving machine.

## Complete C++ source

Use `translation_unit=True` when the source contains top-level template
definitions, function definitions, or its own header directives. No function
wrapper is added:

```python
from clang_toolkit import Client
from clang_toolkit.matchers import cxxMemberCallExpr

code = r"""
struct MyTest { int value; };
template <class T> struct TemplateType {
    T saved{};
    void add(T value) { saved = value; }
};
void probe() {
    TemplateType<MyTest> test;
    test.add(MyTest{7});
}
"""

with Client() as client:
    with client.parse_cpp(code, translation_unit=True) as tree:
        with tree.match(cxxMemberCallExpr().bind("call")) as calls:
            assert len(calls) == 1
            print("member calls:", len(calls))
```

An `#include` inside a default statement block is inside its generated function;
headers declaring namespaces/templates usually cannot be included there. Use
`includes=[...]` to put such headers before the wrapper, or use complete source.

## Ownership and interpretation

The parsed tree is reusable with the existing matching and native analysis
operations. Independent child results retain their captured tree when their
parent closes. Use context managers and close retained values promptly; the
temporary source is owned by the server's native snapshot, including cache
retention. It is removed when the final snapshot owner releases it, which can be
later than closing a value. Do not remove its temporary file manually.

The borrowed file is configuration provenance, not the snippet's source path.
Compiler diagnostics use snippet-relative lines; match ranges use the generated
file's physical lines/offsets for source navigation. Report these as
temporary-source evidence and distinguish them from declarations originating
in included project headers.
Check diagnostics before interpreting empty results. Async clients expose the
same arguments as `await client.parse_cpp(...)`, with `async with` cleanup.
