#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output="$repo_root/python/clang_toolkit/_generated"
mkdir -p "$output"
touch "$output/__init__.py"
# An explicit interpreter allows generation in an already prepared environment.
if [[ -n "${CTK_PYTHON:-}" ]]; then
  python_command=("$CTK_PYTHON")
else
  python_command=(uv run python)
fi
"${python_command[@]}" -m grpc_tools.protoc \
  -I "$repo_root/api" \
  --python_out="$output" \
  "$repo_root/api/match/v1/match_result.proto" \
  "$repo_root/api/ast/v1"/*.proto \
  "$repo_root/api/query/v1/commands.proto" \
  "$repo_root/api/query/v1/errors.proto" \
  "$repo_root/api/query/v1/events.proto" \
  "$repo_root/api/query/v1/query.proto"
"${python_command[@]}" -m grpc_tools.protoc \
  -I "$repo_root/api" \
  --grpc_python_out="$output" \
  "$repo_root/api/query/v1/query.proto"
for package in ast ast/v1 match match/v1 query query/v1; do
  mkdir -p "$output/$package"
  touch "$output/$package/__init__.py"
done
# Imported AST and match modules need paths relative to their generated package.
for module in "$output/ast/v1/"*_pb2.py; do
  sed -i.bak \
    -e 's/^from ast\.v1 import /from . import /' \
    -e 's/^from ast\.v1\./from ./' \
    -e '/^from \. import .* as /s/$/  # noqa: E402, F401/' \
    "$module"
  rm -f "$module.bak"
done
sed -i.bak \
  -e 's/^from ast\.v1 import /from ...ast.v1 import /' \
  "$output/match/v1/match_result_pb2.py"
rm -f "$output/match/v1/match_result_pb2.py.bak"
# grpcio-tools emits source-root imports; make every module package-relative.
for module in "$output/query/v1/"*_pb2*.py; do
  sed -i.bak \
    -e 's/^from query\.v1 import /from . import /' \
    -e 's/^from query\.v1\./from ./' \
    -e '/^from \. import .* as /s/$/  # noqa: E402, F401/' \
    -e '/^from \..* import \*$/s/$/  # noqa: E402, F403/' \
    -e '/^import warnings$/d' \
    "$module"
  rm -f "$module.bak"
done
sed -i.bak \
  -e 's/^from match\.v1 import /from ...match.v1 import /' \
  "$output/query/v1/events_pb2.py"
rm -f "$output/query/v1/events_pb2.py.bak"
