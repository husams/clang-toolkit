#!/usr/bin/env bash
# Build static dependencies against the selected SDK. Git sources use HTTPS.
set -euo pipefail

root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
: "${CTK_SDK_ROOT:?Set CTK_SDK_ROOT to the GCC SDK path}"
: "${CTK_DEPENDENCY_PREFIX:?Set CTK_DEPENDENCY_PREFIX to an absolute install path}"
: "${CTK_DEPENDENCY_BUILD_DIR:?Set CTK_DEPENDENCY_BUILD_DIR to a dedicated build path}"
sdk=$CTK_SDK_ROOT
prefix=$CTK_DEPENDENCY_PREFIX
work=$CTK_DEPENDENCY_BUILD_DIR
target=${CTK_SDK_TARGET:-x86_64-1a-linux-gnu}
sysroot=${CTK_SYSROOT:-$sdk/$target/sysroot}
loader=${CTK_SDK_LOADER:-$sysroot/lib64/ld-linux-x86-64.so.2}
jobs=${JOBS:-4}
for path in "$sdk" "$prefix" "$work" "$sysroot" "$loader"; do
  [[ "$path" == /* ]] || { echo "SDK paths must be absolute: $path" >&2; exit 2; }
done
[[ "$jobs" =~ ^[1-9][0-9]*$ && -x "$sdk/bin/gcc" && -x "$loader" ]]
mkdir -p "$work/sources" "$prefix"
profile="$work/sdk-profile.txt"
if [[ -f "$profile" ]] && ! cmp -s "$profile" <(printf '%s\n' "$sdk" "$sysroot" "$loader" "$prefix" "$target"); then
  echo "SDK profile changed. Set CTK_DEPENDENCY_BUILD_DIR to a fresh directory." >&2
  exit 2
fi
printf '%s\n' "$sdk" "$sysroot" "$loader" "$prefix" "$target" > "$profile"
export PKG_CONFIG_LIBDIR="$prefix/lib/pkgconfig:$prefix/lib64/pkgconfig:$prefix/share/pkgconfig"

checkout() {
  local name=$1 url=$2 tag=$3 revision=$4 dest="$work/sources/$1"
  if [[ ! -d "$dest/.git" ]]; then
    git clone --depth 1 --branch "$tag" "$url" "$dest"
  fi
  [[ "$(git -C "$dest" rev-parse HEAD)" == "$revision" ]] ||
    { echo "$name checkout must match $revision" >&2; exit 1; }
}

options=(
  -G Ninja "-DCMAKE_TOOLCHAIN_FILE=$root/cmake/toolchains/gcc85-sdk.cmake"
  "-DCTK_SDK_ROOT=$sdk" "-DCTK_SDK_TARGET=$target" "-DCMAKE_SYSROOT=$sysroot"
  "-DCTK_SDK_LOADER=$loader" "-DCTK_DEPENDENCY_PREFIX=$prefix"
  "-DCMAKE_INSTALL_PREFIX=$prefix" -DCMAKE_INSTALL_LIBDIR=lib
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON
  -DBUILD_SHARED_LIBS=OFF
)

build_cmake() {
  local name=$1
  shift
  cmake -S "$work/sources/$name" -B "$work/$name" "${options[@]}" "$@"
  cmake --build "$work/$name" --parallel "$jobs"
  cmake --install "$work/$name"
}

case "${1:-all}" in all|jit) ;; *) echo 'Expected all or jit' >&2; exit 2;; esac

if [[ "${1:-all}" == all ]]; then
  checkout openssl https://github.com/openssl/openssl.git openssl-3.0.18 c10e643222ce5a185f2980d7352d545afacb0fed
  mkdir -p "$work/openssl"
  (
    cd "$work/openssl"
    if [[ ! -f Makefile ]]; then
      CC="$sdk/bin/gcc" AR="$sdk/bin/ar" RANLIB="$sdk/bin/ranlib" \
        "$work/sources/openssl/Configure" linux-x86_64 no-shared no-tests no-module \
        "--prefix=$prefix" --libdir=lib "--sysroot=$sysroot" -fPIC
    fi
    make -j "$jobs"
    make install_sw
  )

  checkout libyaml https://github.com/yaml/libyaml.git 0.2.5 2c891fc7a770e8ba2fec34fc6b545c672beb37e6
  build_cmake libyaml -DYAML_BUILD_SHARED_LIBS=OFF

  checkout grpc https://github.com/grpc/grpc.git v1.46.7 02384e39185f109bd299eb8482306229967dc970
  grpc_source="$work/sources/grpc"
  git -C "$grpc_source" -c protocol.ssh.allow=never -c protocol.git.allow=never submodule update \
    --init --depth 1 --jobs "$jobs" third_party/abseil-cpp third_party/cares/cares \
    third_party/protobuf third_party/re2 third_party/zlib
  build_cmake grpc \
    -DgRPC_INSTALL=ON -DgRPC_BUILD_TESTS=OFF -DgRPC_BUILD_CSHARP_EXT=OFF -DgRPC_SSL_PROVIDER=package \
    "-DOPENSSL_ROOT_DIR=$prefix" -DOPENSSL_USE_STATIC_LIBS=ON \
    -DABSL_PROPAGATE_CXX_STD=ON -DCMAKE_CXX_STANDARD=17 \
    -DgRPC_BUILD_GRPC_CSHARP_PLUGIN=OFF -DgRPC_BUILD_GRPC_NODE_PLUGIN=OFF \
    -DgRPC_BUILD_GRPC_OBJECTIVE_C_PLUGIN=OFF -DgRPC_BUILD_GRPC_PHP_PLUGIN=OFF \
    -DgRPC_BUILD_GRPC_PYTHON_PLUGIN=OFF -DgRPC_BUILD_GRPC_RUBY_PLUGIN=OFF \
    -Dprotobuf_BUILD_TESTS=OFF -Dprotobuf_BUILD_SHARED_LIBS=OFF
fi

if [[ "${CTK_SDK_JIT:-0}" == 1 || "${1:-all}" == jit ]]; then
  checkout pcre2 https://github.com/PCRE2Project/pcre2.git pcre2-10.44 6ae58beca071f13ccfed31d03b3f479ab520639b
  build_cmake pcre2 -DPCRE2_BUILD_TESTS=OFF -DPCRE2_BUILD_PCRE2GREP=OFF

  checkout icu https://github.com/unicode-org/icu.git release-74-2 2d029329c82c7792b985024b2bdab5fc7278fbc8
  mkdir -p "$work/icu"
  (
    cd "$work/icu"
    runtime="$prefix/lib:$sdk/$target/lib64:$sysroot/lib64"
    if [[ ! -f Makefile ]]; then
      CC="$sdk/bin/gcc" CXX="$sdk/bin/g++" AR="$sdk/bin/ar" RANLIB="$sdk/bin/ranlib" \
        CFLAGS="--sysroot=$sysroot" CXXFLAGS="--sysroot=$sysroot -std=c++17" \
        LDFLAGS="-Wl,--dynamic-linker=$loader,--disable-new-dtags,-rpath,$runtime" \
        "$work/sources/icu/icu4c/source/configure" "--prefix=$prefix" \
        --enable-shared --disable-static --disable-tests --disable-samples
    fi
    make -j "$jobs"
    make install
  )
fi
