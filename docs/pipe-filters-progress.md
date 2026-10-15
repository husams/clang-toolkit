# Pipe filter delivery

Branch: `codex/pipe-filters`, based on `bb39c76`.

## Implemented

- Pipe expressions, named arguments, parameterized user filters, tuple values,
  nested tuple patterns, and the simplified callback syntax in both console
  engines.
- Collection, record, Unicode string, and structured-output filters with item,
  step, depth, and output limits. Saved builtin aliases use the current
  submission's limits.
- Callable preflight, callback dependency admission, native-result ownership,
  and rollback of mutable values nested in imported tuples.
- Offline `help pipes`, stage and parameter completion, runnable signature
  hints, and pipeline highlighting.
- A complete example and its expected output in `docs/pipe-filters.md` and
  `examples/pipe_filters.ctk`.

## Verification

- Complete Python unit suite: **2,207 passed**.
- Final zip budget and shortest-input refinements: filter suite **23 passed**,
  pipeline acceptance suite **18 passed**.
- Fresh native build and all **381 native tests passed**.
- The complete example produces `Widget: 5` and `Other: 2` in both engines;
  real terminal acceptance also passes.
- Independent review findings were fixed and retested, including callback
  admission before resource work and bounded formatter allocation.
- All **160 integration cases passed** across isolated runs, including
  retries for account-library leakage and server or terminal startup delays.

Tests isolate account startup libraries and use a private absolute
`CTK_STORAGE_ROOT` to avoid interference from other running servers.
