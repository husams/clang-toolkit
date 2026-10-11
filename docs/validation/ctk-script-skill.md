# CTK scripting skill console validation

Validated on 2026-10-11 against private local native servers on macOS.
An independent agent read only `skills/ctk-script/SKILL.md` and its bundled
references. It discovered and analyzed the targets through real TTY-backed CTK
console sessions without reading target C++, implementation, configuration, or
environment files, and without Python SDK or runtime/parser API calls.

## Controlled fixture

The evaluator prepared these two translation units before dispatch; the agent
received their paths and the task, not their contents or expected results.

`engine.cpp`:

```cpp
namespace trial {
int adjust(int value) { return value + 7; }
long accumulate(long first, long second) { return first + second; }
int process(int input) { return adjust(input); }
struct Meter { int read(int sample) const { return adjust(sample); } };
}
```

`extra.cpp`:

```cpp
namespace trial {
bool ready(bool flag) { return flag; }
int zero() { return 0; }
}
```

## Observed behavior

| Check | Result |
| --- | --- |
| Serving-side `files` discovery | Two files, empty diagnostics, no truncation. |
| Definition inventory | Six definitions: `trial::adjust`, `trial::accumulate`, `trial::process`, `trial::Meter::read`, `trial::ready`, `trial::zero`. Return spellings: int, long, int, int, bool, int. |
| Parameter continuation | Six parameter rows: value, first, second, input, sample, flag; correct parents through retained per-file matches. |
| Call continuation | Two direct calls: process and Meter::read both call adjust. |
| Intentional field error | Unknown field reported; previous inventory still had length six. |
| Size-one foreground batch | Completed, results complete, two completed files, zero failed groups, acknowledged cleanup. |
| Collected scalar results | Six names extracted while bindings were live, then flattened after group cleanup. |
| Native script through console | Four engine definitions and parameter-count emissions `[4, 1, 2, 1, 1]`; 21 execution steps. |
| Exports | Inventory, parameters, calls and names JSON written with CTK `save`. |
| Reusable script | `analysis.ctk` created entirely with CTK `print ... to` replace/append commands. |
| Saved-script execution | Fresh private-server CLI runner reproduced the results and exited zero. |

## Corrections and fresh checks

The agent's first run exposed wording gaps, which the skill now explains:

- Interactive submissions accept one top-level command. Semicolons separate
  statements inside blocks and top-level commands in `--script`/`--execute`.
- A multi-file continuation's `source_match_index` is local to the originating
  file's retained result. The extra file's flag parameter had index zero, which
  points to ready in its own parent collection, not adjust in the combined one.
  Reported macOS paths used `/private/tmp` for `/tmp` targets.
- Console `server status` did not expose the connection endpoint. The known
  private launcher can pass its own endpoint when rerunning a saved script.
- Native expression-form matchers inside a single-quoted outer console string
  avoid nested matcher-string quoting; outer strings still decode escapes.

A fresh agent check of the revised guidance returned two extra-file definitions,
one parameter (flag, index zero, parent trial::ready), and a native count emission
of two. The interactive session exited zero. A second saved-script rerun also
exited zero and reproduced the complete results above.

Real console sessions were launched with `bash scripts/manual_console.sh --ui
prompt`; saved scripts ran through `bash scripts/manual_console.sh --script
PATH`. Each launcher provisioned and cleaned its own private server. Endpoint
and build readiness remain environment prerequisites; this test did not exercise
remote servers, durable recovery, RHEL packaging, or every CTK language feature.

## Publication regression checks

The development build and serializer source gate passed. The full native
GoogleTest binary passed all 336 tests in one process with a fresh storage root;
all 972 Python unit tests passed.

An earlier per-test CTest run failed
`BatchRegistry.ManifestLimitRejectionDoesNotPoisonLaterRuns` and
`BatchRegistry.PostRenameJournalFailureFailsClosedUntilRestart`; a separate
post-rename test invocation also failed its five-second polling expectation.
Both cases passed in the complete 336-test native run. No application code or
test deadlines were changed for this skill publication.
