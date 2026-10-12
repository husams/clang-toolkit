# Batch stalls and live progress

Validated on linux-dev against Clang on 2026-10-11.

The subsequent [server snapshot optimization](server-snapshot-performance.md)
includes new before/after measurements and the latest complete test results.

## Fix

After a successful cursor commit, resource registration can reject the actual
native/result memory estimate. Matching previously called `CursorRegistry::close`
while holding that cursor's nonrecursive operation mutex. Closing acquires the
same mutex, so the worker waited indefinitely. Fresh, streamed, and forked cursor
failure paths now release that lock before closing. The native regression checks
that rejected cursors disappear, the source cursor survives a rejected fork,
and later requests still succeed.

Parallel matching observes failures in completion order, cancels the scope
before joining sibling workers, and preserves manifest order for successful
results. Oversized groups still return resource-exhaustion errors; the server's
memory limit is preserved.

Foreground progress defaults to on, including `let`. Running updates print
elapsed time, completed/failed/in-flight file counts, and the current phase every
second through admission, work, and cleanup. The workspace refreshes its progress
display in place; other modes print on stdout independently
of output destinations and the bounded body-output budget. `progress off` remains
quiet. Assigned body display and automatic final report output remain suppressed.

Both interactive presentations route foreground batch statements, including
assignments, through cooperative cancellation and runner joining. The basic
prompt now returns after Ctrl-C; following batches clear the cancellation state.
The interrupted assignment preserves any existing binding.

## Measurements

Cold CTK caches, three native executor workers, eight-vCPU linux-dev with about
15GiB RAM, Clang 21.1.8, and a 2GiB admission limit. OS page caches were retained;
each configuration has one sample. All completed Basic cases return 870 main-file
function definitions from the same 46 sources.

| Batch size | Jobs | Seconds | Result |
|---:|---:|---:|---|
| 1 | 1 | 73.05 | 46/46 completed |
| 4 | 1 | 71.05 | 46/46 completed |
| 4 | 2 | 46.63 | 46/46 completed |
| 4 | 4 | 35.82 | 46/46 completed |
| 16 | 4 | 29.96 | 46/46 completed |
| 16 | 8 | 28.77 | 46/46 completed |
| 32 | 4 | 17.37 | Memory-limit error; cleanup acknowledged |
| 32 | 8 | 16.95 | Memory-limit error; cleanup acknowledged |

The old 32/8 case stalled for at least 127 seconds and failed to recover on
interruption. All new progress-on cases have gaps at most 1.002s. Concurrent
status probes have zero failures and a maximum reply time of 0.146s, including
connection setup. All 16 valid terminal reports acknowledge cleanup and have
zero external pins and unknown file outcomes.

On four heavy CodeGen inputs, size 1/jobs 1 completes in 48.15s and size 2/jobs 2
in 30.03s, with the same 259 function definitions. Size 4/jobs 4 or 8 exceeds the
memory limit and returns after 29.35s or 28.60s with acknowledged cleanup.

The exact 1,003-input manifest was verified before execution. Size 32/jobs 8
returns a memory-limit error after 25.89s with cleanup acknowledged; this stops
at its first failed group and is not a full-dataset throughput measurement.
Ctrl-C in an assigned Basic batch returns the prompt 1.29s after interruption,
with a cancelled report and acknowledged cleanup. A subsequent batch succeeds.

## Validation and evidence

- 1,022 Python unit tests and 116 acceptance tests pass.
- All 337 Linux native tests pass in a complete serial CTest run with isolated
  storage. Concurrent shared-storage cache-reuse failures pass serially.
- All 337 macOS native cases pass with individually isolated storage and two
  corrected cold-publication timeout reruns. Those existing five-second waits
  now allow 30 seconds for durable snapshot filesystem syncs.
- A real prompt_toolkit workspace test verifies assigned-batch progress appears
  while the command remains blocked and busy. Linux measurements use a real
  pseudo-terminal with `--ui prompt`.

The repeated server optimization comparison, with sample triplets and individual
measurements, is recorded in [server snapshot performance](server-snapshot-performance.md).
Full timestamped console evidence and test logs are retained locally.

The patch is in the local checkout and an isolated Linux build. The ordinary
remote checkout and a separate cloud VM were not deployed. Accounted snapshot
bytes are an estimate; the admission limit is not an operating-system RSS cap.
