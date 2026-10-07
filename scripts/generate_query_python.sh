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
schema_directory="$(mktemp -d "${TMPDIR:-/tmp}/ctk-python-schema.XXXXXX")"
trap 'rm -rf "$schema_directory"' EXIT
"${python_command[@]}" "$repo_root/api/assemble_ast.py" --output "$schema_directory"
"${python_command[@]}" -m grpc_tools.protoc \
  -I "$schema_directory" \
  --python_out="$output" \
  --pyi_out="$output" \
  "$schema_directory/match/v1/"*.proto \
  "$schema_directory/analysis/v1"/*.proto \
  "$schema_directory/ast/v1"/*.proto \
  "$schema_directory/query/v1/commands.proto" \
  "$schema_directory/query/v1/errors.proto" \
  "$schema_directory/query/v1/events.proto" \
  "$schema_directory/query/v1/query.proto"
"${python_command[@]}" -m grpc_tools.protoc \
  -I "$schema_directory" \
  --grpc_python_out="$output" \
  "$schema_directory/match/v1/match_service.proto" \
  "$schema_directory/analysis/v1/analysis_service.proto" \
  "$schema_directory/query/v1/query.proto"
for package in ast ast/v1 match match/v1 query query/v1 analysis analysis/v1; do
  mkdir -p "$output/$package"
  touch "$output/$package/__init__.py"
done
# Imported AST and match modules need paths relative to their generated package.
for module in "$output/ast/v1/"*_pb2.py "$output/ast/v1/"*_pb2.pyi; do
  sed -i.bak \
    -e 's/^from ast\.v1 import /from . import /' \
    -e 's/^from ast\.v1\./from ./' \
    -e '/^from \. import .* as /s/$/  # noqa: E402, F401/' \
    -e '/^from \..* import \*$/s/$/  # noqa: E402, F403/' \
    "$module"
  rm -f "$module.bak"
done
for module in "$output/match/v1/"*_pb2*.py "$output/match/v1/"*_pb2.pyi; do
  sed -i.bak \
    -e 's/^from ast\.v1 import /from ...ast.v1 import /' \
    -e 's/^from ast\.v1\./from ...ast.v1./' \
    -e 's/^from match\.v1 import /from . import /' \
    -e 's/^from match\.v1\./from ./' \
    -e '/^import warnings$/d' "$module"
  rm -f "$module.bak"
done
# grpcio-tools emits source-root imports; make every module package-relative.
for module in "$output/query/v1/"*_pb2*.py "$output/query/v1/"*_pb2.pyi; do
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
  "$output/query/v1/events_pb2.py" "$output/query/v1/events_pb2.pyi"
rm -f "$output/query/v1/events_pb2.py.bak" "$output/query/v1/events_pb2.pyi.bak"

for module in "$output/analysis/v1/"*_pb2*.py "$output/analysis/v1/"*_pb2.pyi; do
  sed -i.bak \
    -e 's/^from ast\.v1 import /from ...ast.v1 import /' \
    -e 's/^from ast\.v1\./from ...ast.v1./' \
    -e 's/^from analysis\.v1 import /from . import /' \
    -e 's/^from analysis\.v1\./from ./' \
    -e 's/^from match\.v1 import /from ...match.v1 import /' \
    -e 's/^from match\.v1\./from ...match.v1./' \
    -e '/^import warnings$/d' "$module"
  rm -f "$module.bak"
done
