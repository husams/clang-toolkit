# Runtime comparison measured on 12 October 2026

Python 3.14.0rc2; macOS-26.1-arm64-arm-64bit-Mach-O. Seven samples per case; milliseconds are medians.

| Iterations | Workload | Tree execution | Compiled execution | Execution ratio | Fresh tree total | Fresh compiled total |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1000 | arithmetic | 3.24 | 1.94 | 1.67x | 12.98 | 12.16 |
| 1000 | conditional | 6.06 | 3.35 | 1.81x | 17.83 | 17.35 |
| 1000 | structured | 8.21 | 4.56 | 1.80x | 27.59 | 23.67 |
| 1000 | registered_host | 2.66 | 1.51 | 1.76x | 13.01 | 12.42 |
| 10000 | arithmetic | 34.67 | 19.67 | 1.76x | 43.42 | 32.66 |
| 10000 | conditional | 58.18 | 33.02 | 1.76x | 71.36 | 45.87 |
| 10000 | structured | 78.84 | 47.70 | 1.65x | 112.97 | 72.85 |
| 10000 | registered_host | 28.63 | 16.28 | 1.76x | 49.05 | 35.59 |

Compiled execution was 1.65–1.81 times faster in these guarded workloads. Fresh totals include parsing and, for the compiled engine, compilation; parser construction and process startup are already warm. First execution and independent parse/compile timings are available in the raw JSON.

Each repetition uses fresh bindings and output. Both engines share value operations and budget checks; the harness asserts identical values, bindings, output and execution-step counts before timing.

The registered_host case invokes a local Python callback. These results do not establish a native-server or end-to-end Clang speedup.

Reproduce from the worktree:

```sh
PYTHONPATH=python /Users/husam/workspace/clang-toolkit/.venv/bin/python scripts/benchmark_runtime_prototype.py --items 1000 10000 --repeats 7 --output docs/runtime-prototype/benchmark-results.json
```
