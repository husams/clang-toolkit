---
name: ctk-cpp-reasoning
description: Reason about C++ code through the installed clang-toolkit Python SDK, using typed matcher queries and native AST analyses.
---

# Reason about C++ with clang-toolkit

Use this skill when an agent needs source-backed structural facts about C++ in a project. Query the code through the public `clang_toolkit` Python API. Do not inspect the SDK installation, environment/configuration files, or target C++ source to discover facts or APIs. The user supplies the code target; the server must be able to access it.

Run Python through the helper in this loaded skill directory. Use the absolute
directory supplied by the skill catalog; do not search for it. The helper uses the
skill's preinstalled SDK project by default. A missing or empty `CTK_SDK_PROJECT`
selects that project; a nonempty value overrides it with another installed uv
project. Keep the selected path opaque:

```sh
bash "/absolute/path/to/loaded-skill-directory/scripts/python.sh" - <<'PY'
# Python SDK query goes here.
PY
```

`Client()` uses the SDK's configured endpoint. Assume the selected project already has the SDK installed; do not run setup, bootstrap the project, install packages, or search for SDK source at runtime unless the user asks for setup. Do not print or inspect `CTK_SDK_PROJECT`, read configuration files, or use shell tools to examine target source. Use the installed public API as described in the bundled references; do not guess methods or fields. Typed matchers are composed with `Matcher` and the matcher factories. Clients accept a `Matcher` directly.

Separate observed facts from interpretation. A matcher result is a shallow semantic projection: check field availability before treating a missing child as absent, and query child nodes through a follow-up matcher. Report when a query fails, is bounded, or leaves coverage unresolved. Static call edges do not establish runtime targets, especially for virtual or indirect calls.

Read only the reference needed for the question:

- [Launch and public API](references/launch-and-api.md) for client setup, compilation databases, and result ownership.
- [Typed matchers and semantic values](references/matchers-and-values.md) for composition, safe field access, and retained results.
- [Reasoning recipes](references/recipes.md) for symbol inventory, child/parent relations, callers, type/base/template inspection, CFG, and call graphs.
- [Limits and reporting](references/limits-and-reporting.md) for budgets, completeness, and static-analysis boundaries.
