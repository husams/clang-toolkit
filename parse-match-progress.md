# Parse/match implementation and review handoff

Historical implementation handoff: edits and validation were complete. **All edit ownership was
released to the independent review chat.** The findings below describe the
validated pre-review snapshot; all twelve independently confirmed repairs are
now resolved, with final integration evidence in `sdk-review-progress.md`.

The implementation baseline was `706740f6f86bf1a62c7e8ab6ccd6153daeed33c8`.
Extensive preexisting dirty/untracked changes were preserved. No commits,
pushes, resets or reverts were performed.

## Completed approved scope

- [x] API-first Parse RPC and preserved-source match contract.
- [x] Native pinned trees, immutable result forks, all-row/indexed selections,
  shared snapshot accounting, expiry/error behavior and ownership cleanup.
- [x] ANTLR native and Lark console parse/match expressions, lexical default
  trees, shadowing, terminal yield and continuation after block cleanup.
- [x] Python retained values, typed semantic rows, expression execution,
  selection matching and synchronous/asynchronous result/tree contexts.
- [x] Packaged TypeScript SDK with generated gRPC/semantic types, retained
  values, structured errors, scopes, disposal, examples and package consumers.
- [x] Automatic shared YAML loading in ordinary SDK/API/console construction,
  optional explicit path, recursive layered merge, strict per-file validation,
  null handling, winning provenance, origin-relative sockets and gRPC tuning.
- [x] Shared 25-case native/Python/TypeScript configuration fixture and real
  no-address/context/receive-limit/deadline checks.
- [x] Required macOS and Rocky 9 validation, plus Clang-disabled/Clang-only gates.

Earlier results remain usable after continuation; independent children retain
native ownership after their parent's context exits. Aliases share ownership.
Native script emissions are detached, while yielded native values remain live
inside the same script. Existing mutable cursor/query commands remain usable.

## Final verification

| Gate | Result | Evidence |
| --- | --- | --- |
| macOS full native suite | 245/245 passed | `/tmp/ctk-expression-native-final.log` |
| macOS Python + live E2E | 251/251 passed: 218 unit + 33 E2E | `/tmp/ctk-expression-python-final.log` |
| Rocky 9 full CTest | 245/245 passed | `/tmp/ctk-expression-rhel-tests-final.log` |
| Rocky 9 Python + live E2E | 251/251 passed | same Rocky log |
| Clang-disabled build/CTest | 108/108 passed | `/private/tmp/ctk-native-noclang-tests-final.log` |
| Clang-disabled real server | Parse FAILED_PRECONDITION; pure script emitted 7; clean shutdown | `/private/tmp/ctk-native-noclang-probe-final.log` |
| Clang-only expression build | 150/150 passed; completed before network configuration changes | `/tmp/ctk-expression-clangonly-tests.log` |
| TypeScript checks | strict source/tests/examples and Biome passed | package validation manifest |
| TypeScript tests | 39 unit + 18 real Unix/TCP integration passed | package validation manifest |
| Packaged TypeScript consumer | offline type/runtime checks: calls 2, references 2, script emissions 1, discovery and explicit YAML true | package validation manifest |
| Native serializer/schema gates | 251 serializers, 923 extraction paths, schema check passed | `/tmp/ctk-expression-serializer.log`, `/tmp/ctk-expression-schema.log` |
| Clang include boundary | 120 production headers/sources checked; no forbidden includes | `/private/tmp/ctk-native-include-boundary-final.log` |
| Whitespace | git diff --check passed | final workspace check |

The real console used YAML without an address argument. Sync/async public SDK
contexts, exception cleanup, closed aliases and surviving children passed over
Unix/TCP. Configured 16-byte receive limits rejected actual native Parse replies.
A real gRPC service delaying Parse for one second hit a configured 25 ms deadline
in 33 ms with DEADLINE_EXCEEDED and confirmed receipt of the request.
The configured Python and JavaScript examples passed without address arguments.

Native tests requiring Unix sockets ran with approved access outside the file
sandbox. The first Rocky run was disrupted by rebuilding its test binary during
CTest; the final run completed its build before testing. Its missing Python
environment was restored from the frozen dependency lock. These earlier setup
runs are superseded by the successful final gates above.

## Validation snapshots

Source parity verified 1,460 implementation/build/test files against the
workspace snapshot and all 1,486 copied files inside Rocky, with zero differences.
Manifest: `/private/tmp/ctk-expression-rhel-context/source-manifest.json`.
Rocky source parity log: `/tmp/ctk-expression-rhel-source-parity.log`.
The retained local validation container is `ctk-expressions-validation` on
Podman's `podman-machine-default-root` connection; it is available for review
revalidation. Its source and binaries reflect this pre-review snapshot.

TypeScript artifacts are under `/private/tmp/ctk-typescript-validated/`:

- `source-manifest.json`: 773 source hashes, shared fixture hash and validation.
- `typescript-source.tar.gz`: frozen source archive.
- `clang-toolkit-sdk-0.1.0.tgz`: validated local package; never published.

TypeScript source-tree SHA256:
`7614b1b3d1b96d37f507c4d7bf279e40b683a86bdcc58c0be648e799b73e0610`.
Source archive SHA256:
`11e0c1e5f8d7aa30f8d7cb018ac1ad5d894572384e9b57cecf4ac6c6ac936600`.
Package SHA256:
`2db16f86db79b599f2d82ba794b95624df3e10c2c9768b26b657b905cfc3d8aa`.
All source/artifact hashes matched at handoff. Later review edits require
fresh builds, tests, package verification and snapshot hashes.
Node 25.9 was exercised; Node 22 compatibility used Node 22 types rather than
that runtime. Native TLS and browser/gRPC-Web support are not claimed.
The temporary SDK example server was stopped after validation.

## Reserved independent review work

The review chat explicitly owns follow-up fixes after this handoff:

- Settled TypeScript TreeScope failures can be removed before finish observes
  them; retain and propagate failures even when they settle before callback exit.
- YAML directive/timestamp scalar typing parity needs further review fixes.
- Python cancellation, cleanup, loop and shutdown findings are reserved for
  review; confirm configuration lifetime after the caching change in this pass.
- Native script compiler-profile propagation must work without a redundant
  options.file.

These findings were reported by the independent review chat and intentionally
left to its owner. Passing current gates does not resolve these additional cases.
Implementation agents and root have released source ownership and will make no
further edits unless requested.

## Documentation and consulted guidance

[Syntax and SDK semantics](docs/parse-match-expressions.md),
[Python example](examples/parse_match.py), [TypeScript SDK](typescript/README.md),
[shared configuration cases](tests/fixtures/network_configuration.json).

Directly read the approved [shared network design Page](https://chatgpt.com/space/page_561b779557cc8191a5aace9bf6273191),
wiki instructions/index and [[pages/planning/clang-toolkit-network-yaml-configuration]],
[[pages/planning/clang-toolkit-result-cursors]],
[[pages/planning/clang-toolkit-match-service-sessions]], and
[[pages/planning/clang-toolkit-interactive-runtime]]. Some wiki future-work
language is stale relative to the live implementation; the code and current
validation are authoritative. No wiki files were modified.

## Accepted integration snapshot

The approved implementation and twelve review repairs are integrated with the
serializer baseline through a clean, scoped candidate. Native suites pass 219
tests on both macOS and Rocky 9; full Python/BDD passes 230 on each. No-Clang
passes 108, Clang-only passes 138, and TypeScript passes 41 unit plus 20 live
Unix/TCP tests, strict checking, lint and build. The Python wheel matches all
635 packaged files and passes strict typed-consumer validation.

The required matching/cursor/script/configuration dependencies are included.
Separate standalone analysis, project and enhanced cache work remains in the
shared working tree. See `sdk-review-progress.md` for the exact scope, source
preservation, publication audit, platform limits and local evidence paths.
