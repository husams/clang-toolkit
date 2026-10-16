# Callgraph refinement implementation

Specification: [Clang Toolkit callgraph usability and retained input proposal](https://chatgpt.com/space/page_97441a03020481919a9361964dc17ff6).

Baseline: `169a1a1b6128eb83a79e787474374a4b5ee66982`. Implementation branch: `codex/callgraph-refinement`.

## Stories

- [x] Add additive retained-target, compact call-site and streaming contracts.
- [x] Resolve filenames, parsed sessions, native file handles and exact matched callable or call-expression nodes without hidden reparsing.
- [x] Add bounded incoming, outgoing and bidirectional focus with accurate static coverage and unresolved calls.
- [x] Support shallow-default SDK and console queries, callback and async-iterator streams, and explicit collectors.
- [x] Add reusable graph navigation, shortest routes and recursive components without synthetic-root relationships.
- [x] Add runnable examples and acceptance coverage for source removal, stale selectors, limits, cancellation and both transports.
- [x] Complete native, Python, E2E and schema checks; independently review the final implementation.

## Scope

Implement the Page's three planned deliveries. A built-in viewer, graph-image export, project-wide graph merge and dynamic dispatch resolution remain the Page's later extensions.

## Acceptance

The practical workflow parses once, matches an exact function, requests its callers and callees, selects an individual call site, continues with match or CFG, and exports a shallow graph. Repeated calls and recursion remain visible; unresolved indirect calls never become invented edges. Retained inputs continue after source removal and fail explicitly after closure or revision expiry.

## Verification

- API contracts are additive and retain existing field numbers.
- The new retained-input acceptance scenarios failed on both Unix and TCP against the baseline: the old client converted a ParsedTree to a filename. This establishes the behavior the implementation must replace.
- Native build configured in `/private/tmp/ctk-callgraph-native-build` using the existing local dependency sources.
- Native regression suite: 402 tests passed. Focused CallGraph and ScriptNative coverage passed 30 tests; the final declaration-only seed refresh passed all 12 CallGraph tests.
- Python regression suite: 2,266 tests passed, followed by focused coverage for JSON export, graph-node identity, stream scope checks and named-argument validation. The final console callgraph module passed 19 tests.
- Five final callgraph acceptance scenarios passed over Unix sockets and TCP, including descriptors, unused declaration-only seeds, source edits/removal, JSON export, a compact report and a 4 KiB per-event limit with a larger aggregate graph.
- TypeScript checking passed; 52 tests passed and 24 optional integration tests were skipped.
- API gate passed for 256 schemas; serializer coverage checked 251 concrete serializers and 923 extraction paths.
- The exact compiled terminal example passed: eight nodes, six call sites, three incoming edges, two route steps, six groups, one unresolved site and one CFG. Its JSON export contains five nodes, three edges and three sites.
- End-to-end regression: 169 of 171 scenarios passed in the full run. The two earlier failures (CallGraph JSON export and a legacy library startup timeout during concurrent builds) both passed on final recheck, 2/2. All 171 scenarios were therefore verified; the five callgraph scenarios also passed together against the final binary.
- Independent review approved the final implementation with no remaining blockers. Ruff and staged whitespace checks passed.

## Implementation decisions

Retained target validation reuses MatchController's native ownership and revision checks. Graph queries leave existing match cursors unchanged. The Python collector retains its protobuf return type; reusable graph methods use a separate CallGraph helper and console value.

Graph visualization, image exports, project-wide merging and dynamic target resolution remain explicitly outside this delivery. Native topology caching must not retain unaccounted snapshot memory; repeated operations on a collected graph use its local topology and indexes.
