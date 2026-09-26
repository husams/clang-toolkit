# API contract

Single, versioned interface shared by the server, the interactive CLI and the Python API.
Transport is TBD (gRPC vs REST); the contract lives here either way
(`clang_toolkit.proto` for gRPC, or `openapi.yaml` for REST).

Initial operations: `open_project`, `match` (AST matchers), `traverse`, `cfg`, `callgraph`, `run_script`, `cache_stats`.
