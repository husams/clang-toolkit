# Use ready-made CTK scripts

Choose a bundled script before rebuilding an analysis from scratch. Resolve this
skill's directory from the active `SKILL.md` location; scripts and imports are
client-side files and need not be in the target project or current directory.

| Question | Resource | How to use it |
| --- | --- | --- |
| What calls are reachable from a function, keeping project headers and excluding system/vendor/generated calls? | [callgraph_project.ctk](../scripts/callgraph_project.ctk) | Run with `path`, `function`, `output`; see [callgraphs.md](callgraphs.md) for filename/retained inputs, scope, optional strict filtering and completeness. |
| What blocks and branches form a function's CFG? | [cfg_stream.ctk](../scripts/cfg_stream.ctk) | Run with `path`, `function`; emits individual graph events. |
| Where is a local read/written, initialized, live or overwritten? | [local_usage.ctk](../scripts/local_usage.ctk) | Run with `path`, `function`, `variable`, `output`; prints usage facts and exports the full report. |
| What inclusive integer bounds reach each usage? | [value_ranges.ctk](../scripts/value_ranges.ctk) | Same arguments; adds interval facts, branch refinement and loop convergence. |
| What are a class's members, template facts or ancestors? | [ctk_helpers.ctk](../scripts/ctk_helpers.ctk) | Import definitions, then call helpers with a live parsed target; see [utilities.md](utilities.md). |
| How do I use pipes, tuple callbacks and formatting? | [pipe_report.ctk](../scripts/pipe_report.ctk) | Run without arguments; local-data demonstration, without native queries. |

Analysis scripts execute immediately through `--script`; they are not import-only
libraries. Do not put them in the console's startup-library directory. Imports of
`ctk_helpers.ctk` define dormant helpers and do not themselves run analysis.

## Run the bundled loop example

Set `ctk_skill_dir` to the resolved absolute skill directory, then use the
configured server or add the endpoint supplied for the task with `--server`.
The following commands assume a local server that can read the bundled fixture:

```sh
ctk_skill_dir=/absolute/path/to/ctk-script
ctk --script-engine compiled --script "$ctk_skill_dir/scripts/value_ranges.ctk" \
  "path=$ctk_skill_dir/assets/flow_fixture.cc" "function=score" \
  "variable=total" "output=/tmp/score-values.json"
```

The numeric recipe prints:

```text
Variable: total
Domain: INTERVAL
Line 2 INITIALIZE: before=UNINITIALIZED, after=[0, 0]
Line 5 READ_WRITE: before=[0, 10], after=[2, 12]
Line 7 READ_WRITE: before=[0, 10], after=[1, 11]
Line 9 READ: before=[1, 12], after=[1, 12]
Line 10 WRITE: before=[11, 12], after=[10, 10]
Line 13 READ: before=[0, 10], after=[0, 10]
Findings: 0
Complete: true
```

The same source supports the other two recipes:

```sh
ctk --script-engine compiled --script "$ctk_skill_dir/scripts/cfg_stream.ctk" \
  "path=$ctk_skill_dir/assets/flow_fixture.cc" "function=score"
ctk --script-engine compiled --script "$ctk_skill_dir/scripts/local_usage.ctk" \
  "path=$ctk_skill_dir/assets/flow_fixture.cc" "function=score" \
  "variable=total" "output=/tmp/score-usages.json"
```

These recipes use the compiled console. The tree evaluator supports the same
scripts; use `--script-engine tree` when specifically testing that evaluator.
Use a client/server build containing CFG streaming/reuse (PR #31), variable flow
(PR #32) and, for numeric ranges, interval analysis (PR #34). Client-side syntax
help alone does not prove the connected server supports the requested analysis.

## Apply a recipe to the user's target

Pass the supplied source, concrete function/method and local-variable names.
Prefer qualified function names. Named arguments are literal strings; quote the
entire `name=value` argument when it contains spaces or shell punctuation.
The scripts require exactly one function definition and one local declaration
for variable analysis. Missing names, overloads and shadowed locals cause an
explicit selection error instead of silently selecting the first match. To
disambiguate, copy the script and refine its matcher for the requested definition
or declaration. Dependent templates need a concrete instantiation; parameters,
globals and static locals are outside the local-flow model.

For a project build, pass its compilation database and endpoint explicitly:

```sh
ctk --server unix:///tmp/ctk.sock --script-engine compiled \
  --compile-commands /project/build/compile_commands.json \
  --script "$ctk_skill_dir/scripts/value_ranges.ctk" \
  "path=/project/src/score.cpp" "function=demo::score" \
  "variable=total" "output=/tmp/project-score-values.json"
```

The source and compilation database must be accessible to the server; no source
upload is implied. The script and exported JSON live on the client. Supply an
existing output directory and a fresh output filename when recording evidence.
Read the export only after that invocation succeeds, so an older file cannot
stand in for a failed run. The full report contains `analysis`, `usages`, `facts`,
`findings` and `completed`; join facts to usages by `usage_id`, rather than array
position or source order. Protobuf JSON can omit empty/default fields.

Use the bundled scripts unchanged when they fit the task. Native limits,
cancellation and selection failures propagate. Keep errors visible; avoid a
blanket `on error` fallback that turns failed analysis into empty findings.
Honor existing authorization: these recipes do not require installing packages,
changing settings or restarting the user's service.

## Reuse parsed trees and matched nodes in one session

Each recipe parses once and continues from retained bindings. Separate CLI
invocations create separate sessions; they do not share those live handles.
For several analyses of the same target, keep them in one script or interactive
session:

```ctk
let tree = parse "/project/src/score.cpp"
let functions = match functionDecl(isDefinition(), hasName("demo::score")).bind("f") in tree
let function_row = functions.one("demo::score definition")
let function_node = function_row.f
let variables = match varDecl(hasLocalStorage(), unless(parmVarDecl()), hasName("total")).bind("v") in function_node
let variable_row = variables.one("total declaration")
cfg in function_node
let usages = variableflow variable_row.v in function_node
let ranges = variableflow variable_row.v in function_node values interval
print usages.completed.is_complete
print ranges.completed.is_complete
```

These operations reuse the same native AST and declaration identities. A CFG may
be rebuilt for each analysis; this is not a persistent CFG cache. Finish a stream
before issuing another query against its snapshot. Keep live inputs until all
queries finish. Exported JSON is detached data and cannot replace a retained
binding for native continuation.

## Interpret results before reporting them

- `cfg_stream.ctk` prints `graph_started`, `block`, `graph_completed` and final
  `completed` events. Require successful process exit and terminal completion;
  earlier records are provisional on failure. Per-graph semantic completeness
  and payload availability are separate from successful stream completion.
- The variable recipes explicitly collect a bounded report in client memory,
  save it, then print readable rows. For larger incremental usage/fact output,
  use standalone `variableflow variable_row.v in function_node`, optionally with
  `values interval`, in the retained session instead of assigning its result.
  Streaming does not remove the native CFG or convergence work.
- Require `completed.is_complete = true` for complete coverage of the requested
  model. A zero exit status with `Complete: false` reports an unsupported model,
  not a clean analysis. Inspect findings and do not infer safety from absence.
- Reaching assignments identify possible source definitions, not numerical
  values. Initialization warnings remain separate from numeric intervals.
  `UNINITIALIZED` never means zero; `UNKNOWN` never means unreachable.
- Numeric facts describe conservative inclusive bounds across all visits to a
  usage, not a per-iteration trace or exact value set. The first numeric domain
  covers signed integer locals up to 128 bits. Unknown guards explore both
  edges; relationships among other locals, aliases and callees are not tracked.
  Unsupported effects, conversions/input types and possible signed overflow
  produce explicit unknown/incomplete results. Read enum names through `.name`
  when comparing them in CTK, and keep decimal bounds as exact strings in JSON.

When returning evidence, identify the script, endpoint/target, named arguments,
completion and any findings; include the observed output when requested. The
bundled fixture's output demonstrates the recipe, not a result for the user's
different source.

## Maintained sources

- `docs/cfg-streaming.md` and `docs/local-variable-flow.md`
- `api/analysis/v1/variable_flow.proto`
- `examples/value_ranges.ctk` and `examples/value_ranges.output.txt`
- `tests/e2e/test_ctk_flow_scripts_steps.py`
