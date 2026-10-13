# Node traversal and streaming

User request: traverse paths, parsed trees and any retained node; emit visits incrementally.

- [x] Contract and native visitor: arbitrary DynTypedNode roots, preorder streaming, cancellation/backpressure.
- [x] Owned retained-target resolution without reparsing or mutating source cursors.
- [x] Streaming RPC, Python streaming API, console streaming output.
- [x] Native, Python and BDD coverage; full C++ and Python suites.
- [x] Update proposal Page and wiki with implementation and verified limitations.

Unary Traverse remains a compatibility collector. StreamTraverse is the incremental transport.

Verified: 343 native tests; 1,134 Python unit tests; 121 other acceptance cases from the full run, plus all three corrected/new traversal acceptance cases on rerun (124 distinct cases). The initial full-run failures were a fixture using cxxBaseSpecifier as a top-level matcher; it now captures the base inside hasAnyBase.

The standalone Clang 22.1.8 probe in /private/tmp/ctk-all-node-probe.cpp covers all 17 DynTypedNode families; every root streams with valid parent/ordinal structure. All assertions pass.

Optional dev-noclang build remains blocked at linking in existing native-script/resource helpers (missing Clang-layer factories/profile/snapshot-scope functions). This delivery does not claim a passing disabled-Clang or RHEL gate.

Proposal: https://chatgpt.com/space/page_b01ffe1c9588819180a63c3a7a4f3416
Wiki mirror: /Users/husam/workspace/wiki/pages/planning/clang-toolkit-ast-navigation-and-traverse.md

The shared server has not been restarted; verification uses isolated native server processes. Parent and inheritance navigation remain proposals.
