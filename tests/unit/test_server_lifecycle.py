"""Managed macOS restarts must replace the supervisor, not just its child."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest


@pytest.mark.parametrize("platform_name", ["Darwin", "Linux"])
def test_managed_restart_replaces_launch_job_and_preserves_build_settings(
    tmp_path: Path,
    platform_name: str,
) -> None:
    root = Path(__file__).resolve().parents[2]
    state = tmp_path / "state"
    state.mkdir()
    tools = tmp_path / "tools"
    tools.mkdir()
    server = tools / "ctk-server"
    server.write_text("""#!/usr/bin/env bash
if [[ "${1:-}" == --print-config ]]; then echo unix:///tmp/ctk-test.sock; exit; fi
printf 'ctk-server listening on unix:///tmp/ctk-test.sock\n'
printf '%s\n' "${CPATH-<unset>}|${SDKROOT-<unset>}" > "$CTK_SERVER_STATE_DIR/compiler-env"
trap 'exit 0' TERM
while :; do sleep 0.1; done
""")
    (tools / "uname").write_text(f"#!/usr/bin/env bash\necho {platform_name}\n")
    (tools / "launchctl").write_text("""#!/usr/bin/env bash
set -eu
case "$1" in
submit)
  shift
  while [[ "$1" != -- ]]; do
    case "$1" in -l) label="$2";; -o) output="$2";; -e) error="$2";; esac
    shift 2
  done
  shift
  /usr/bin/env -u CPATH -u SDKROOT "$@" </dev/null >>"$output" 2>>"$error" &
  printf '%s %s\n' "$!" "$label" > "$CTK_SERVER_STATE_DIR/job"
  echo submit >> "$CTK_SERVER_STATE_DIR/actions"
  ;;
list)
  if [[ ! -f "$CTK_SERVER_STATE_DIR/job" && -n "${2:-}" ]]; then exit 1; fi
  if [[ -f "$CTK_SERVER_STATE_DIR/job" ]]; then
    read -r pid label < "$CTK_SERVER_STATE_DIR/job"
    printf '%s\t0\t%s\n' "$pid" "$label"
  fi
  ;;
remove)
  [[ "${CTK_LAUNCH_REMOVE_STATUS:-0}" == 0 ]] || exit "$CTK_LAUNCH_REMOVE_STATUS"
  read -r pid label < "$CTK_SERVER_STATE_DIR/job"
  [[ "$2" == "$label" ]]
  kill -TERM "$pid"
  rm "$CTK_SERVER_STATE_DIR/job"
  echo remove >> "$CTK_SERVER_STATE_DIR/actions"
  ;;
esac
""")
    for path in tools.iterdir():
        path.chmod(0o755)
    env = os.environ | {
        "PATH": f"{tools}:{os.environ['PATH']}",
        "CTK_SERVER_BINARY": str(server),
        "CTK_SERVER_STATE_DIR": str(state),
        "CTK_STORAGE_ROOT": str(tmp_path / "storage"),
        "CPATH": str(tmp_path / "headers with spaces"),
        "SDKROOT": "",
    }
    commands = tmp_path / "compile_commands.json"
    commands.write_text('[{"arguments":["clang++","-arch","arm64"]}]')
    before = commands.read_bytes()
    try:
        for operation in ["start", "restart", "status", "stop"]:
            if operation == "restart" and platform_name == "Darwin":
                blocked = subprocess.run(
                    ["bash", str(root / "scripts/server.sh"), "stop"],
                    env=env | {"CTK_LAUNCH_REMOVE_STATUS": "7"},
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                assert blocked.returncode == 1
                assert "cannot remove managed launch job" in blocked.stderr
                assert (state / "job").exists()
            if operation == "status" and platform_name == "Darwin":
                (state / "server.pid").write_text("99999999\n")
            result = subprocess.run(
                ["bash", str(root / "scripts/server.sh"), operation],
                env=env,
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            assert (state / "compiler-env").read_text().strip() == f"{env['CPATH']}|"
            if platform_name == "Darwin" and operation in {
                "start",
                "restart",
                "status",
            }:
                assert (
                    (state / "server.launchd-label")
                    .read_text()
                    .strip()
                    .startswith("dev.clang-toolkit.managed.")
                )
        if platform_name == "Darwin":
            assert (state / "actions").read_text().splitlines() == [
                "submit",
                "remove",
                "submit",
                "remove",
            ]
        else:
            assert not (state / "actions").exists()
        assert not (state / "server.pid").exists()
        assert not (state / "server.launchd-label").exists()
        assert commands.read_bytes() == before
    finally:
        if (state / "job").exists():
            pid = int((state / "job").read_text().split()[0])
            try:
                os.kill(pid, 15)
            except ProcessLookupError:
                pass
        elif (state / "server.pid").exists():
            try:
                os.kill(int((state / "server.pid").read_text()), 15)
            except ProcessLookupError:
                pass
