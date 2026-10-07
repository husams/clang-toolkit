# SQLite 3.53.4

`sqlite-amalgamation-3530400.zip` is the unmodified official source archive,
included so CMake can build SQLite statically without network access.

- Source: https://www.sqlite.org/2026/sqlite-amalgamation-3530400.zip
- SHA-256: `1e71ddf93849c6a6ecf58b827c0692073d2dd7ee40196158068f7b29f422e87d`
- License: [SQLite public-domain dedication](https://www.sqlite.org/copyright.html).

CMake verifies this hash before extraction. To update SQLite, replace the archive
and update the filename and hash in `cmake/SQLite.cmake` and this document together.

An isolated static build and `INSERT ... RETURNING` smoke test can run without
the server's other dependencies or network access:

```sh
cmake -S tests/cmake/sqlite-offline -B build/sqlite-offline
cmake --build build/sqlite-offline
ctest --test-dir build/sqlite-offline --output-on-failure
```
