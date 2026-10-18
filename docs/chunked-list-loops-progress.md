# Chunked plain list loops

Branch: `codex/chunked-list-loops`; implementation base main: `2126bd7`.

- [x] Add failing checks for plain bounded inner loops (six failed before implementation).
- [x] Move observer writes and source accounting outside per-item loops.
- [x] Verify chunk-boundary values, aliases, budgets, cancellation and restoration.
- [x] Complete independent review (no blockers).
- [x] Complete full regression runs and record limitations (not all green).
- [x] Measure paired old/new execution and capture the real console example.

A persistent iterator over the existing shallow snapshot feeds `islice` chunks
of at most 128 elements. The inner loop only evaluates the proven scalar
expression/predicate and appends. No chunk slices or repeated tail copies are
allocated. Filter derives accepted counts from the output-length delta and keeps
the last predicate value for observer settlement. Reverse retains its logical
pending-work item limit and settles unwind depth in batches.

Standard Event cancellation is cooperative at chunk boundaries, including the
proof scan. Completed chunks settle steps and observer state before cancellation
is reported. Detected cancellation still raises without a second poll. Custom
hooks, unsupported values and insufficient complete-step budgets retain guarded
execution and its original diagnostics and partial output behavior.

## Validation

- Focused unit regressions: **281 passed** (`/tmp/ctk-chunked-focused.log`).
- New coverage includes both engines, 127/128/129 and 255/256/257 boundaries,
  aliased input/output, exact source counts and budget failures, cancellation
  after each of three chunks, observer state and scope/depth restoration.
- Generated AST checks require two nested loops and no context, observer,
  cancellation or plan access in the inner transform/append body.
- Full Python unit run: **3,212 passed, 4 UI timeouts** in 1,262.52s
  (`/tmp/ctk-chunked-unit.log`). The interactive-pipeline timeout passed on a
  separate 26-test rerun (`/tmp/ctk-chunked-interactive-rerun.log`).
- The three remaining UI timeouts repeated on the branch and on an archived,
  unchanged main `2126bd7` under the same environment and original deadlines
  (`/tmp/ctk-chunked-unit-ui-rerun.log`,
  `/tmp/ctk-chunked-baseline-unit-ui.log`). No UI code or test timeouts changed.
- All **209 distinct E2E scenarios** completed in four isolated-storage groups:
  **193 passed, 16 failed** (13 CLI deadlines and three terminal/UI assertions).
  Both compiled/tree real terminal list-pattern scenarios passed.
  Evidence: `/tmp/ctk-chunked-e2e-6xgrapzq/summary.json` and each group's JUnit/log.
- Three initially failing E2E cases passed serial retry with their original
  assertions and deadlines: workspace cancellation, TCP numeric analysis and
  multiline batch execution (`/tmp/ctk-chunked-e2e-retry.log`). Console export
  continued to exceed its 30-second deadline. Unchanged main passed that case in
  28.13s and the parameterized-matcher case in 32.97s total, so these checks have
  little timing margin here; a successful unchanged-main run does not prove
  every branch timeout unrelated. Further serial retry results are recorded below.
  Main evidence: `/tmp/ctk-chunked-baseline-network.log` and
  `/tmp/ctk-chunked-baseline-parameterized.log`.
- Native source/build configuration is unchanged. The inherited native baseline
  exercised 440 IDs: 439 passed and one known stale-binary shared-header index
  assertion failed (`/tmp/ctk-compact-native-summary.json`), as recorded in
  `docs/plain-list-loops-progress.md`. That baseline was not rerun for this
  Python-only change; a fully green native suite is not claimed.

## Paired timing

Median milliseconds over 15 warmed alternating runs in one process, comparing
main `2126bd7`'s preparation/compiler with the chunked implementation through the
same actual runtime dispatcher. Output values and unchanged inputs were checked.
These are local measurements, not portable performance guarantees.

| Items | Function | Previous | Chunked |
| ---: | --- | ---: | ---: |
| 1,000 | map | 0.967 | 0.498 |
| 1,000 | filter | 0.946 | 0.813 |
| 1,000 | reverse | 0.574 | 0.402 |
| 10,000 | map | 7.349 | 5.340 |
| 10,000 | filter | 9.236 | 7.235 |
| 10,000 | reverse | 6.142 | 2.399 |

Evidence: `/tmp/ctk-chunked-benchmark.log`.

## Real console

Ran the exact final `examples/recursive_lists.ctk` as one bracketed paste in a
TTY-backed compiled console, connected to a separate native server and isolated
storage, history and empty library directory. History was compared byte-for-byte
with the example. Six actual native selections were captured (map/filter/reverse
for 5 and 1,000 inputs) using local `sys.monitoring` return events on
`prepare_plain`; no tick, cancellation, observer or callback hooks were changed.
The three small-call sources are checked in under `docs/generated-list-loops/`.

Artifacts: `/tmp/ctk-chunked-demo.iSIBwE/` (`example.ctk`, `transcript.txt`,
`actual-output.txt`, `generated/records.jsonl` and six generated Python files).

Actual output:

```text
[10,20,30,40,50]
[2,4]
[5,4,3,2,1]
[1,2,3,4,5]
Large counts: 1000, 500, 1000
```

## Final serial retries

The follow-up run retried nine cases serially with unchanged assertions/deadlines:
**six passed, three still timed out** in 339.89s. Evidence:
`/tmp/ctk-chunked-followup.log` and
`/tmp/ctk-chunked-followup-6zojxumt/results.xml`.

Combining the original run and the two serial retry runs yields **202 of 209
distinct E2E cases passing**, with seven unresolved failures. Four of those seven
were not retried after the complete run. This is not an all-green regression
result; the feature-specific tests and exact real-console demo pass.
Aggregate: `/tmp/ctk-chunked-e2e-final-summary.json`.

Unresolved cases:

- `tests/e2e/test_network_steps.py::test_console_file_output_preserves_match_snapshots_and_supports_text_append`
- `tests/e2e/test_reasoning_values_steps.py::test_parameterized_matchers_expand_through_the_console_and_python_sdks`
- `tests/e2e/test_reasoning_facts_steps.py::test_a_selected_lambda_operator_keeps_its_body_calls_and_caller_identity`
- `tests/e2e/test_workspace_console_steps.py::test_paste_whole_scripts_browse_files_and_expand_native_analysis_in_the_workspace`
- `tests/e2e/test_ctk_skill_helpers_steps.py::test_structured_class_information_and_complete_or_bounded_inheritance_trees`
- `tests/e2e/test_variable_flow_steps.py::test_track_the_page_example_through_the_native_server_and_console[tcp]`
- `tests/e2e/test_console_editor_updates_steps.py::test_edit_earlier_matcher_lines_and_inspect_saved_functions_in_the_workspace`
