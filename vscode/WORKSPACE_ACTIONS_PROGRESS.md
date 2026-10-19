# VS Code workspace action experiment

- Worktree: `/Users/husam/.claude/worktrees/clang-toolkit/vscode-workspace-actions`
- Branch: `codex/vscode-workspace-actions`; original base: `058acfc`; feature commit: `a189c48`.
- Index alias dependency: upstream `7d572fd`, cherry-picked as `8d24419`.
- The extension retains its two tabs, existing panels, result grouping, inspector, and Options sections.

| Slice | State | Evidence |
| --- | --- | --- |
| Directory/workspace action scopes | Implemented | Deterministic capped discovery, source-first per folder, header-only fallback, generated-folder exclusions, dirty-header protection |
| Server batch resource management | Implemented | Foreground compiled batches with one-file scopes, cleanup acknowledgement, detached results, per-file failures, cancellation, lazy native inspection |
| Workspace compiler profiles | Implemented | Original workspace resource URIs select settings; canonical inputs retain frozen per-file profiles |
| Indexed symbol search | Implemented | Project/global scope, explicit project selector, Aliases kind, server-side kind/deduplication before limiting, stale/partial/error feedback |
| Independent review | Passed | No production blockers; explicit project selection is intentionally sticky across editor switches |
| Broad regressions and editor workflow | Complete | All cases have passing evidence; timing-related retries are disclosed below |

## Use

Open **Actions → Options** and choose **Directory** or **Workspace folders**. Explorer folders also expose **CTK → Select Action…**. Completed batch results use the existing match list; select a binding to inspect its AST or run a follow-up action. Refresh/Close releases analysis resources; the existing running status/cancel action controls execution.

Open **Symbol Search → Options** and choose **Project** or **Global**, then the symbol kinds, including **Aliases**. The server must already have a project index. The selected project stays fixed when switching editors. Existing file/workspace AST searches remain available.

## Verification

All native integration checks use this worktree's compiled server, not a server from the primary checkout. The full native suite used a separate storage directory per case during parallel execution.

| Check | Result | Log |
| --- | --- | --- |
| Native worktree build | Passed | `/private/tmp/ctk-workspace-actions-native-build.log` |
| Python unit suite | 3421 passed | `/private/tmp/ctk-workspace-actions-python-unit.log` |
| VS Code unit suite | 151 passed, 31 integration cases skipped | `/private/tmp/ctk-workspace-actions-vscode-unit-final.log` |
| Native extension integration | 30 passed, 1 existing case skipped | `/private/tmp/ctk-workspace-actions-vscode-live.log` |
| Console adapter regressions | 28 passed | `/private/tmp/ctk-workspace-actions-console.log` |
| Indexed-symbol Python adapter | 5 passed | `/private/tmp/ctk-workspace-actions-index-adapter-final.log` |
| Extracted VSIX index bridge | Passed outside the checkout against the experimental server | `PACKAGED_INDEX_BRIDGE_PASS` |
| TypeScript check | Passed | `/private/tmp/ctk-workspace-actions-types-final.log` |
| Lint | Passed; one existing informational suggestion | `/private/tmp/ctk-workspace-actions-lint-final.log` |
| Complete native suite | 525 cases covered; 524 passed initially, one existing watcher timing case passed on serial rerun | `/private/tmp/ctk-workspace-actions-native-parallel.log`; `/private/tmp/ctk-workspace-actions-native-rerun.log` |
| Complete Python E2E suite | 215 verified: 210 initial passes and 5 unchanged isolated retries passing; zero unresolved | `/private/tmp/ctk-wa-e2e-shards/outcomes.json`; `/private/tmp/ctk-wa-e2e-shards/retry-outcomes.json` |
| Real VS Code extension host | Passed: full workflow, batch inspection/follow-up, existing layout, saved ASTs and 1001-declaration tree | `/private/tmp/ctk-workspace-actions-host-complete.log` |

Native batch fixtures cover five inputs against a four-cursor limit, two workspace compiler profiles and headers, a failed file with successful continuation, explicit zero-resource counters after cleanup, result truncation, lazy second-root inspection, and cancellation. Index fixtures cover two persisted projects, project/global lookup, alias filtering and deduplication before a one-result limit, and lazy AST inspection.

## Timing-related retries

The initial parallel native run passed 524/525 cases. The directory-inventory watcher case passed unchanged on serial rerun and a verbose confirmation (`/private/tmp/ctk-workspace-actions-native-watcher-verbose.log`). The six E2E groups initially passed 210/215 cases; four existing console subprocesses exceeded 45/60-second deadlines and one workspace console missed its 15-second startup display deadline. Every failed case passed unchanged in an isolated retry. No source changes or longer test deadlines were used to obtain these passes.

## Isolation

The primary checkout and the installed extension are unchanged by this experiment. The matching experimental server is `build/dev/server/ctk-server` in this worktree. [Download the experimental VSIX](/Users/husam/.claude/worktrees/clang-toolkit/vscode-workspace-actions/vscode/artifacts/clang-toolkit-workspace-actions-experiment.vsix). It has not been installed into the existing editor profile.

## Real-checkout warning follow-up — 2026-10-19

The original real-checkout batch was still running when checked and had not
published a report. It was cancelled to reload the warning fixes; its status is
preserved in `artifacts/workspace-actions-preview/original-long-batch-status.json`.
The same unfiltered function-definition action was rerun with a 25-match result
cap against all 449 discovered inputs. The bounded run finished with 25 matches,
two parsed translation units and one per-file error, and explicitly reports
`truncated=true`. This is not a completed analysis of all 449 inputs. The error
is the documentation benchmark's missing `ctk/platform/file_watch.hpp` under its
current compilation profile. Included-header function matches remain part of the
unchanged action.

Actions now ignore unrelated implementation-file events in excluded build and
metadata directories, while retaining source edits in the active scope,
explicitly selected build files/directories, and conservative header invalidation
(including generated headers). Create, change and delete events use the same
policy. The original triggering event URI was not captured, so no particular
background writer is identified.

Indexed searches now carry the fetched per-project lifecycle and coverage state
through the private bridge. A fully covered index in CHECKING is described as a
freshness check with checked/reused/updated counters; it no longer instructs the
user to reindex merely because foreground work delays that check. Failed,
incomplete and otherwise stale indexes retain their warning. Completed counts
already include reused inputs and are not added to skipped counts.

The real isolated extension host verifies that editing/saving an unrelated
generated C++ artifact leaves the report current, editing a generated header
marks it stale, and Refresh followed by the same capped rerun clears it. The
final Actions view has 25 rendered rows and no source-change warning. Global
Aliases search for `ctk::script::` returns five real project aliases in four
rendered file groups, without truncation. The report and the existing Actions
view are open in the private window; the installed extension and primary checkout
remain unchanged.

Live evidence and the displayed report are under
`artifacts/workspace-actions-preview/real-followup-evidence.json` and
`artifacts/workspace-actions-preview/Workspace Batch Results.md`. The experimental
VSIX was rebuilt. TypeScript build/check, 159 extension tests (31 optional cases
skipped), six bridge tests and all 3,427 combined Python checks pass. All 525
native cases pass: 234 completed serially, then the remaining 291 completed with
four workers and separate storage per case. The interrupted in-flight case was
rerun, not omitted. There are no unresolved failures. Native evidence is in
`/private/tmp/ctk-warning-fix-native-WIQGI2/summary.json`.
