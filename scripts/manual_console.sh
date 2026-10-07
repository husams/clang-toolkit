#!/usr/bin/env bash
set -euo pipefail

# Run a private local server and the real interactive Python console.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
server_binary="$repo_root/build/dev/server/ctk-server"
python_binary="$repo_root/.venv/bin/python"

if [[ ! -x "$server_binary" ]]; then
  printf 'Build the server first: cmake --preset dev && cmake --build --preset dev\n' >&2
  exit 1
fi
if [[ ! -x "$python_binary" ]]; then
  printf 'Install the Python environment first: uv sync\n' >&2
  exit 1
fi

scratch="$(mktemp -d /tmp/ctk-console.XXXXXX)"
server_pid=""
cleanup() {
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  rm -rf -- "$scratch"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

config="$scratch/server.yaml"
socket_path="$scratch/server.sock"
endpoint="unix://$socket_path"
source_path="$scratch/main.cc"
cat > "$config" <<YAML
network:
  transport: unix
  unix:
    socket_path: $socket_path
YAML
printf 'int main(){return 7;}\n' > "$source_path"

CTK_STORAGE_ROOT="$scratch/storage" TMPDIR="$scratch" \
  "$server_binary" -c "$config" > "$scratch/server.log" 2>&1 &
server_pid=$!

if ! "$python_binary" - "$endpoint" <<'PY'
import sys
import grpc

with grpc.insecure_channel(sys.argv[1]) as channel:
    try:
        grpc.channel_ready_future(channel).result(timeout=15)
    except grpc.FutureTimeoutError:
        print("The local server did not become ready.", file=sys.stderr)
        raise SystemExit(1)
PY
then
  cat "$scratch/server.log" >&2
  exit 1
fi

printf '\nServer ready. Enter these commands at ctk>:\n\n'
printf '  script "emit 7;"\n'
printf '  cursor open "%s" integerLiteral().bind("n")\n' "$source_path"
printf '  quit\n\nBoth requests should return 7. Exiting stops the private server.\n\n'

cd "$repo_root"
XDG_STATE_HOME="$scratch/state" "$python_binary" -m clang_toolkit.cli.app \
  --server "$endpoint" -c "$config"
