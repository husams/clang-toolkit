# Normal VS Code alias search timeout validation

Verified on 2026-10-20 in the normal VS Code window
`SemaDecl.cpp — ctk-retained-verification-frSttJ`.

## Fix

Blank alias enumeration previously used `NOT INDEXED`, scanning unrelated
symbol rows and their overflow payloads on every page. The existing five-second
server read budget could expire under contention, returning `interrupted`.

Writers now create the partial covering index `symbol_alias_browse` for
`TypeAlias` and `Typedef`. Enumeration uses it when available and retains its
old readable fallback before an existing database is upgraded. The index
contains the kind predicate and all candidate/grouping columns, so candidate
selection reads no symbol-table payloads. Native query-plan inspection confirms
`SCAN symbol USING COVERING INDEX symbol_alias_browse`.

Deadlines, cancellation, deduplication, revision-pinned pagination, source-path
classification, public APIs, extension controls, and styles are unchanged.

## Real indexed data and normal-window checks

The name was blank and Aliases was the only selected symbol kind.

| Scope | Source files only | Declarations | Complete API enumeration |
|---|---|---:|---:|
| Project: clang-toolkit | On | 59 | 199 ms |
| Project: clang-toolkit | Off | 4,693 | 2,286 ms |
| Global | On | 88 | 22 ms |
| Global | Off | 4,722 | 639 ms |

Every declaration identity `(project, USR, path, line, column)` appears once.
Unfiltered clang-toolkit enumeration consumed all five pages; the final page
contained 693 declarations and no continuation. The largest individual page
in this final matrix took 931 ms. These are observations, not latency guarantees.

All four combinations also completed in the actual normal extension window.
Project mode displayed `59 indexed symbols found.` and `4693 indexed symbols
found.` Global source-only mode rendered 88 declarations; unfiltered global
mode rendered its grouped results without an interruption or incomplete-page
error. Global scope includes 27 ast-matchers-lab aliases and two ctk-lab aliases
in addition to clang-toolkit. Its existing stale-index notice remains because
the unrelated, idle `/tmp/ctk-index-console-demo` index is still registered;
that index returned no aliases. No index was deleted to suppress the notice.

The three active monitors ended COMPLETE with saved coverage 631/631, 20/20,
and 5/5. Their final passes reused every translation unit, with no extraction
or errors. clang-toolkit search pages pinned revision 8204. The normal profile
retains extension version 0.3.0 and its original settings. Installed sidebar
and inspector styles compare byte-for-byte with the merged extension source.
The isolated experimental window and its private server remain running.

## Regression and compatibility checks

- The new regression failed before the fix: 6,009 full-scan steps, exceeding
  its 100-step bound. It passes after the fix with both source-filter values,
  page size one, declaration uniqueness, stable revisions, old-store fallback,
  and automatic writer upgrade. A query-plan assertion guards covering reads.
- The complete 543-case native suite ran: 536 passed initially and seven
  filesystem-notification/artifact-reuse cases passed on an unchanged serial
  retry. After the final covering-index change, all 50 project-index tests
  passed; all four alias/schema regressions passed again after strengthening
  the regression's pagination guard and revision assertions.
- Python unit tests: 3,433 passed. The initial test invocation had a test-package
  import-path collection error; setting the checkout on PYTHONPATH resolved it.
- Extension tests: 163 passed, 33 integration tests skipped by the default run.
- Build and `git diff --check` passed. Code review found no API, layout,
  ownership, SQL-input, or pagination changes outside the intended fix.

## Installed normal backend

`/Users/husam/.local/state/ctk/bin/alias-search-timeout-20261020-v2/bin/ctk-server`

SHA-256: `99a32f100ee8bf2ea39b62150e984a1c2a3fb53872fa6f2e803c04e873607359`

The managed endpoint and storage root are unchanged. Preliminary local index
definitions were replaced transactionally with the final covering definition;
all three active project monitors were resumed afterward.
