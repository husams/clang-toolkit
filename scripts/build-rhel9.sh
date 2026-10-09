#!/usr/bin/env bash
# Install RHEL 9 dependencies, build clang-toolkit, and run its test suites.
# DEPS_ONLY=1 installs host tools; SKIP_DEPS=1 reuses installed dependencies.
# SKIP_TESTS=1 omits tests; PACKAGE=1 builds an RPM; INSTALL=1 installs it with DNF.
# BUILD_DIR, JOBS, INSTALL_PREFIX, and SQLITE_SOURCE_DIR override their defaults.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${BUILD_DIR:-$repo_root/build/rhel9}"
jobs="${JOBS:-$(nproc 2>/dev/null || echo 4)}"
install_prefix="${INSTALL_PREFIX:-/usr}"
sqlite_source_dir="${SQLITE_SOURCE_DIR:-}"

fail() { printf 'error: %s\n' "$*" >&2; exit 1; }
[[ "$(uname -s)" == Linux && -r /etc/os-release ]] || fail 'RHEL 9 or a compatible Linux distribution is required'
# shellcheck disable=SC1091
source /etc/os-release
[[ "${VERSION_ID%%.*}" == 9 && " ${ID:-} ${ID_LIKE:-} " =~ [[:space:]](rhel|rocky|almalinux|centos)[[:space:]] ]] \
  || fail 'RHEL 9, Rocky Linux 9, AlmaLinux 9, or CentOS Stream 9 is required'
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || fail 'JOBS must be a positive integer'
build_dir="$(realpath -m "$build_dir")"
install_prefix="$(realpath -m "$install_prefix")"
if [[ -n "$sqlite_source_dir" ]]; then
  sqlite_source_dir="$(realpath -m "$sqlite_source_dir")"
fi

privilege=()
if [[ "$(id -u)" != 0 ]]; then
  if [[ "${SKIP_DEPS:-0}" != 1 || "${INSTALL:-0}" == 1 ]]; then
    command -v sudo >/dev/null || fail 'sudo is required to install dependencies or the server'
    privilege=(sudo)
  fi
fi

if [[ "${SKIP_DEPS:-0}" != 1 ]]; then
  "${privilege[@]}" dnf -y install dnf-plugins-core
  if [[ "$ID" == rhel ]]; then
    # UBI containers and RHUI hosts already configure repositories and may not
    # provide subscription-manager. Preserve RHSM management on registered hosts.
    builder_repo="$("${privilege[@]}" dnf -q repolist --all | awk '
      $1 == "ubi-9-codeready-builder-rpms" ||
      ($1 ~ /^codeready-builder-for-rhel-9-/ && $1 ~ /-rpms$/ &&
       $1 !~ /-(debug|source)-rpms$/) { if (!repo) repo = $1 }
      END { print repo }
    ')"
    if [[ "$builder_repo" == ubi-* || "$builder_repo" == *rhui* ]]; then
      "${privilege[@]}" dnf config-manager --set-enabled "$builder_repo"
    elif command -v subscription-manager >/dev/null; then
      "${privilege[@]}" subscription-manager repos \
        --enable "codeready-builder-for-rhel-9-$(arch)-rpms"
    elif [[ -n "$builder_repo" ]]; then
      "${privilege[@]}" dnf config-manager --set-enabled "$builder_repo"
    else
      printf 'No CodeReady Builder repository configured; using existing repositories.\n'
    fi
  else
    "${privilege[@]}" dnf config-manager --set-enabled crb
  fi
  if ! rpm -q epel-release >/dev/null 2>&1; then
    "${privilege[@]}" dnf -y install \
      https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
  fi
  # Minimal RHEL images already provide curl-minimal, which conflicts with curl.
  curl_package=()
  command -v curl >/dev/null || curl_package=(curl)
  "${privilege[@]}" dnf -y install \
    clang clang-devel llvm-devel cmake ninja-build make git tar unzip rpm-build \
    gcc-toolset-15-gcc-c++ gcc-toolset-15-libstdc++-devel \
    grpc-devel protobuf-devel protobuf-compiler libyaml-devel openssl-devel \
    zlib-devel libzstd-devel libxml2-devel ncurses-devel libffi-devel python3 \
    "${curl_package[@]}" \
    || fail 'Dependency installation failed; full RHEL 9 AppStream/CodeReady repositories are required. UBI repositories alone lack some packages; alternatively use packaging/rhel9.Containerfile.'
fi

export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null; then
  [[ "${SKIP_DEPS:-0}" != 1 ]] || fail 'uv is missing; run without SKIP_DEPS'
  scratch="$(mktemp -d)"
  trap 'rm -rf -- "$scratch"' EXIT
  curl --fail --show-error --location https://astral.sh/uv/install.sh \
    --output "$scratch/uv-install.sh"
  UV_NO_MODIFY_PATH=1 UV_INSTALL_DIR="$HOME/.local/bin" sh "$scratch/uv-install.sh"
  rm -rf -- "$scratch"
  trap - EXIT
fi
uv python install 3.14
[[ "${DEPS_ONLY:-0}" != 1 ]] || exit 0

cd "$repo_root"
uv sync --project "$repo_root" --reinstall-package clang-toolkit
python_binary="$(uv run --project "$repo_root" python -c 'import sys; print(sys.executable)')"
sqlite_args=()
if [[ -n "$sqlite_source_dir" ]]; then
  sqlite_args=(-DCTK_SQLITE_SOURCE_DIR="$sqlite_source_dir")
fi

cmake -S "$repo_root" -B "$build_dir" -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_INSTALL_PREFIX="$install_prefix" \
  -DPython3_EXECUTABLE="$python_binary" -DCTK_SYSTEM_SQLITE=OFF \
  -DFETCHCONTENT_BASE_DIR="$repo_root/.deps" \
  -DCTK_BUILD_TESTS="$([[ "${SKIP_TESTS:-0}" == 1 ]] && echo OFF || echo ON)" \
  "${sqlite_args[@]}"
cmake --build "$build_dir" --parallel "$jobs"

server_binary="$build_dir/server/ctk-server"
linkage="$(ldd "$server_binary")"
if [[ "$linkage" == *libsqlite3* ]]; then
  fail 'the native server has a shared SQLite dependency'
fi
printf 'SQLite is statically linked: %s\n' "$server_binary"

if [[ "${SKIP_TESTS:-0}" != 1 ]]; then
  # One process avoids repeated LLVM startup and shared cache-root contention.
  "$build_dir/server/tests/ctk_tests"
  uv run --project "$repo_root" python -m pytest "$repo_root/tests/unit"
  CTK_TEST_CLANG="$(cat "$build_dir/ctk-clang-tool-path.txt")" \
    CTK_SERVER="$server_binary" uv run --project "$repo_root" python -m pytest \
    "$repo_root/tests/e2e" -m e2e
fi
if [[ "${PACKAGE:-0}" == 1 || "${INSTALL:-0}" == 1 ]]; then
  command -v rpmbuild >/dev/null || fail 'rpmbuild is missing; install rpm-build or run without SKIP_DEPS'
  package_dir="$build_dir/packages"
  cpack --config "$build_dir/CPackConfig.cmake" -G RPM -B "$package_dir"
  rpm_file="$package_dir/$(cat "$build_dir/ctk-rpm-filename.txt")"
  [[ -f "$rpm_file" ]] || fail 'CPack did not produce the expected server RPM'
  printf 'Built RPM: %s\n' "$rpm_file"
  if [[ "${INSTALL:-0}" == 1 ]]; then
    rpm_nevra="$(rpm -qp --qf '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}' "$rpm_file")"
    if rpm -q "$rpm_nevra" >/dev/null 2>&1; then
      "${privilege[@]}" dnf -y reinstall "$rpm_file"
    else
      "${privilege[@]}" dnf -y install "$rpm_file"
    fi
  fi
fi
printf 'Built clang-toolkit: %s\n' "$server_binary"
