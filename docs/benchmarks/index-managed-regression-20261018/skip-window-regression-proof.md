# Non-head stale skip regression proof

Observed during pre-merge review on 2026-10-18 by the isolated implementation worker. This is an excerpt from its test-tool transcript, not a full test log. The fixture destroys the initial indexing adapter before starting the measured controller. Both the head and sixteenth TU mutation cases require nineteen skips, five revision increments, and a maximum of four live extraction workers.

## Previous catch, corrected fixture

Only the old unconditional `item.plan.unchanged = false` catch behavior was restored for the negative check. The late-member case re-extracted one unchanged head: eighteen skips and six revision increments instead of nineteen skips and five.

```text
server/tests/test_project_index_service.cpp:1407: Failure
Expected equality of these values:
  status.translation_units_skipped()
    Which is: 18
  translation_units - 5
    Which is: 19
server/tests/test_project_index_service.cpp:1408: Failure
Expected equality of these values:
  status.revision()
    Which is: 30
  initial_revision + 5
    Which is: 29
[  FAILED  ] ProjectIndexServiceTest.SkipWindowRevalidatesAfterAdmissionWaitWithFourWorkersLive (39100 ms)
[  FAILED  ] 1 FAILED TEST
```

## Final catch restored

The unchanged head is retried without advancing the queue. A freshly validated clean prefix can then commit before extracting the stale member. Both fixture scenarios passed:

```text
[       OK ] ProjectIndexServiceTest.SkipWindowRevalidatesAfterAdmissionWaitWithFourWorkersLive (36652 ms)
[  PASSED  ] 1 test.
```
