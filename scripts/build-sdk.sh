#!/usr/bin/env bash
# Configure, build and test with a local GCC 8.5 SDK, without installing host RPMs.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ ${1:-} == --help ]]; then
  cat <<'HELP'
Set CTK_SDK_ROOT and CTK_SDK_WORK to absolute paths before running this script.
CTK_SYSROOT, CTK_SDK_LOADER and CTK_DEPENDENCY_PREFIX override SDK defaults.
CTK_BUILD_SDK_DEPS=0 uses a prebuilt prefix. CTK_SDK_JIT=1 enables the JIT.
Set JOBS to control build parallelism and SKIP_TESTS=1 for a build-only run.
Additional arguments are forwarded to CMake (e.g. -DCMAKE_INCLUDE_PATH=...).
Use a fresh CTK_SDK_WORK when changing compiler, sysroot or dependency versions.
HELP
  exit 0
fi
: "${CTK_SDK_ROOT:?Set CTK_SDK_ROOT to an absolute SDK path}"
: "${CTK_SDK_WORK:?Set CTK_SDK_WORK to a dedicated absolute directory}"
export CTK_DEPENDENCY_PREFIX=${CTK_DEPENDENCY_PREFIX:-$CTK_SDK_WORK/prefix}
export CTK_DEPENDENCY_BUILD_DIR=${CTK_DEPENDENCY_BUILD_DIR:-$CTK_SDK_WORK/dependencies}
target=${CTK_SDK_TARGET:-x86_64-1a-linux-gnu}
sysroot=${CTK_SYSROOT:-$CTK_SDK_ROOT/$target/sysroot}
loader=${CTK_SDK_LOADER:-$sysroot/lib64/ld-linux-x86-64.so.2}
jobs=${JOBS:-4}
for path in "$CTK_SDK_ROOT" "$CTK_SDK_WORK" "$CTK_DEPENDENCY_PREFIX" "$sysroot" "$loader"; do
  [[ "$path" == /* ]] || { echo "SDK paths must be absolute: $path" >&2; exit 2; }
done
[[ "$jobs" =~ ^[1-9][0-9]*$ && -x "$loader" ]]
[[ "$("$CTK_SDK_ROOT/bin/g++" -dumpfullversion)" == 8.5.0 ]] ||
  { echo 'Expected GCC 8.5.0 in CTK_SDK_ROOT/bin/g++' >&2; exit 2; }
mkdir -p "$CTK_SDK_WORK"
if [[ ${CTK_BUILD_SDK_DEPS:-1} == 1 ]]; then
  "$root/scripts/build-sdk-dependencies.sh"
fi
export PKG_CONFIG_LIBDIR="$CTK_DEPENDENCY_PREFIX/lib/pkgconfig:$CTK_DEPENDENCY_PREFIX/lib64/pkgconfig:$CTK_DEPENDENCY_PREFIX/share/pkgconfig"
build="$CTK_SDK_WORK/app"
test_clang="$CTK_SDK_WORK/ctk-test-clang++"
{
  printf '#!/usr/bin/env bash\n'
  printf 'exec %q %q %q "$@"\n' "$CTK_SDK_ROOT/bin/clang++"     "--sysroot=$sysroot" "--gcc-toolchain=$CTK_SDK_ROOT"
} > "$test_clang"
chmod +x "$test_clang"
tests=ON
[[ ${SKIP_TESTS:-0} != 1 ]] || tests=OFF
jit=OFF
[[ ${CTK_SDK_JIT:-0} != 1 ]] || jit=ON

export PATH="$HOME/.local/bin:$PATH"
export UV_PROJECT_ENVIRONMENT=${UV_PROJECT_ENVIRONMENT:-$CTK_SDK_WORK/venv}
uv sync --project "$root" --frozen
python="$UV_PROJECT_ENVIRONMENT/bin/python"
cmake -S "$root" -B "$build" -G Ninja \
  "-DCMAKE_TOOLCHAIN_FILE=$root/cmake/toolchains/gcc85-sdk.cmake" \
  "-DCTK_SDK_ROOT=$CTK_SDK_ROOT" "-DCTK_SDK_TARGET=$target" \
  "-DCTK_DEPENDENCY_PREFIX=$CTK_DEPENDENCY_PREFIX" \
  "-DCMAKE_SYSROOT=$sysroot" "-DCTK_SDK_LOADER=$loader" \
  "-DPython3_EXECUTABLE=$python" "-DOPENSSL_ROOT_DIR=$CTK_DEPENDENCY_PREFIX" \
  -DOPENSSL_USE_STATIC_LIBS=ON -DCMAKE_BUILD_TYPE=Release \
  "-DCTK_TEST_CLANG_TOOL=$test_clang" \
  "-DCTK_BUILD_TESTS=$tests" "-DCTK_BUILD_JIT=$jit" "$@"
cmake --build "$build" --parallel "$jobs"

server="$build/server/ctk-server"
"$loader" --list "$server"
"$server" --version
if [[ "$tests" == ON ]]; then
  scratch=$(mktemp -d "$CTK_SDK_WORK/test.XXXXXXXX")
  trap 'rm -rf -- "$scratch"' EXIT
  mkdir -p "$scratch/storage" "$scratch/tmp"
  failed=0
  (
    cd "$scratch"
    TMPDIR="$scratch/tmp" CTK_STORAGE_ROOT="$scratch/storage" "$build/server/tests/ctk_tests"
  ) || failed=1
  export CTK_SERVER="$server" CTK_TEST_CLANG
  CTK_TEST_CLANG=$test_clang
  if [[ "$jit" == ON ]]; then
    export CTK_TEST_JIT_RUNNER="$build/ctk-jit-runner"
  fi
  cd "$root"
  "$python" -m pytest tests/unit || failed=1
  "$python" -m pytest tests/e2e -m e2e || failed=1
  (( failed == 0 )) || exit "$failed"
fi
cmake --install "$build" --prefix "$CTK_SDK_WORK/install"
