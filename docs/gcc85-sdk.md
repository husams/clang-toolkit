# Build against the GCC 8.5 SDK

On an x86-64 Linux build host, install Git, CMake, Ninja, Make, Perl with its
core modules, and uv. Point the build at an SDK containing GCC 8.5, Clang/LLVM
21 and the target C library.

```sh
export CTK_SDK_ROOT=/absolute/path/to/sdk
export CTK_SDK_WORK=/absolute/path/to/build-work
JOBS=6 scripts/build-sdk.sh
```

The script fetches pinned dependency sources through Git over HTTPS and
builds them with the SDK. It uses matching SDK-built Protobuf and gRPC code
generators on the x86-64 build host. The server links to SDK LLVM and uses the
SDK dynamic loader. After the test suites pass, it stages the server under
`$CTK_SDK_WORK/install`. Set `CTK_SDK_JIT=1` to build and test the optional JIT
runner, available at `$CTK_SDK_WORK/app/ctk-jit-runner`.

- Override the target filesystem and loader with `CTK_SYSROOT` and
  `CTK_SDK_LOADER`. The default sysroot is
  `$CTK_SDK_ROOT/x86_64-1a-linux-gnu/sysroot`. The embedded Clang parser and
  the external test compiler use the selected SDK and sysroot.
- To use ABI-compatible prebuilt dependencies, set `CTK_BUILD_SDK_DEPS=0` and
  `CTK_DEPENDENCY_PREFIX` to their install prefix. You can also pass
  `-DCTK_EXTRA_DEPENDENCY_ROOTS=/another/prefix`, `-DCMAKE_INCLUDE_PATH=...`,
  and `-DCMAKE_LIBRARY_PATH=...` as script arguments. Discovery is confined
  to the SDK, sysroot and the configured dependency roots. An imported
  package selects its own include directories, so set its package directory
  explicitly if it is not in one of those prefixes.
- Use a fresh work directory when changing the SDK, sysroot, or dependency
  versions. Set `SKIP_TESTS=1` for a build-only run.
- For an existing build profile managed outside this script, invoke CMake
  with `-DCMAKE_TOOLCHAIN_FILE=...` and your package paths. The RHEL 9 wrapper
  also forwards CMake arguments with `SKIP_DEPS=1`.
