#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output="$repo_root/python/clang_toolkit/_generated"
mkdir -p "$output"
touch "$output/__init__.py"
uv run python -m grpc_tools.protoc \
  -I "$repo_root/api" \
  --python_out="$output" \
  --grpc_python_out="$output" \
  "$repo_root/api/query/v1/query.proto"
for package in query query/v1; do
  mkdir -p "$output/$package"
  touch "$output/$package/__init__.py"
done
# grpcio-tools emits a source-root import; make it package-relative.
sed -i.bak 's/^from query\.v1 import query_pb2 as/from . import query_pb2 as/' \
  "$output/query/v1/query_pb2_grpc.py"
# grpcio-tools emits an unused compatibility import in current releases.
sed -i.bak '/^import warnings$/d' "$output/query/v1/query_pb2_grpc.py"
rm -f "$output/query/v1/query_pb2_grpc.py.bak"
