#!/usr/bin/env bash
set -euo pipefail

# Manage a long-lived local ctk-server.
#
# Usage: scripts/server.sh {start|stop|restart|status} [-c CONFIG]
#
# Environment overrides:
#   CTK_SERVER_BINARY     server binary (default: build/dev/server/ctk-server)
#   CTK_SERVER_CONFIG     config file forwarded to ctk-server (same as -c)
#   CTK_SERVER_STATE_DIR  holds server.pid and server.log
#                         (default: ${XDG_STATE_HOME:-$HOME/.local/state}/ctk)
#
# Exit codes: 0 ok, 1 failure, 2 usage error, 3 status: not running.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
server_binary="${CTK_SERVER_BINARY:-$repo_root/build/dev/server/ctk-server}"
state_dir="${CTK_SERVER_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/ctk}"
pid_file="$state_dir/server.pid"
log_file="$state_dir/server.log"
config_path="${CTK_SERVER_CONFIG:-}"
start_timeout_ticks=75  # 15 s at 0.2 s per tick
stop_timeout_ticks=50   # 10 s at 0.2 s per tick

fail() { printf 'error: %s\n' "$*" >&2; exit 1; }

usage() {
  printf 'usage: %s {start|stop|restart|status} [-c CONFIG]\n' "${0##*/}" >&2
  exit 2
}

[[ $# -ge 1 ]] || usage
command_name="$1"
shift
case "$command_name" in
  start | stop | restart | status) ;;
  *) usage ;;
esac
while [[ $# -gt 0 ]]; do
  case "$1" in
    -c)
      [[ $# -ge 2 ]] || usage
      config_path="$2"
      shift 2
      ;;
    *) usage ;;
  esac
done

config_args=()
if [[ -n "$config_path" ]]; then
  config_args=(-c "$config_path")
fi

require_binary() {
  if [[ ! -x "$server_binary" ]]; then
    printf 'Build the server first: cmake --preset dev && cmake --build --preset dev\n' >&2
    exit 1
  fi
}

read_pid() {
  pid=""
  if [[ -f "$pid_file" ]]; then
    pid="$(tr -d '[:space:]' < "$pid_file" 2>/dev/null || true)"
  fi
  case "$pid" in
    '' | *[!0-9]*) pid="" ;;
  esac
}

# Live means: pid exists AND its command line is a ctk-server (guards pid reuse).
pid_is_server() {
  local candidate="$1" command_line
  kill -0 "$candidate" 2>/dev/null || return 1
  command_line="$(ps -p "$candidate" -o command= 2>/dev/null || true)"
  case "$command_line" in
    *ctk-server*) return 0 ;;
    *) return 1 ;;
  esac
}

# Sets $pid to the live server pid from the pidfile; returns 1 (and drops a stale pidfile) otherwise.
server_running() {
  read_pid
  if [[ -n "$pid" ]] && pid_is_server "$pid"; then
    return 0
  fi
  rm -f -- "$pid_file"
  pid=""
  return 1
}

endpoint() {
  "$server_binary" --print-config ${config_args[@]+"${config_args[@]}"} 2>/dev/null || true
}

new_log_output() {
  tail -c +"$(($1 + 1))" "$log_file" 2>/dev/null || true
}

do_start() {
  require_binary
  mkdir -p -- "$state_dir"
  if server_running; then
    printf 'ctk-server already running (pid %s) on %s\n' "$pid" "$(endpoint)"
    return 0
  fi

  touch -- "$log_file"
  local log_offset
  log_offset="$(wc -c < "$log_file" | tr -d '[:space:]')"

  # Fully detached: no stdin, output to the log, immune to hangup of the caller.
  if command -v setsid >/dev/null 2>&1; then
    setsid nohup "$server_binary" ${config_args[@]+"${config_args[@]}"} \
      </dev/null >>"$log_file" 2>&1 &
  else
    nohup "$server_binary" ${config_args[@]+"${config_args[@]}"} \
      </dev/null >>"$log_file" 2>&1 &
  fi
  local launched_pid=$!
  disown "$launched_pid" 2>/dev/null || true
  printf '%s\n' "$launched_pid" > "$pid_file"

  local tick new_output
  for ((tick = 0; tick < start_timeout_ticks; tick++)); do
    if ! kill -0 "$launched_pid" 2>/dev/null; then
      printf 'ctk-server exited during startup; log output:\n' >&2
      new_log_output "$log_offset" >&2
      rm -f -- "$pid_file"
      exit 1
    fi
    new_output="$(new_log_output "$log_offset")"
    if [[ "$new_output" == *'ctk-server listening on'* ]]; then
      printf 'ctk-server started (pid %s) on %s\n' "$launched_pid" "$(endpoint)"
      return 0
    fi
    sleep 0.2
  done

  printf 'ctk-server did not report listening within 15 s; log output:\n' >&2
  new_log_output "$log_offset" >&2
  if pid_is_server "$launched_pid"; then
    kill "$launched_pid" 2>/dev/null || true
  fi
  rm -f -- "$pid_file"
  exit 1
}

do_stop() {
  if ! server_running; then
    printf 'ctk-server not running\n'
    return 0
  fi
  local target="$pid" tick
  kill -TERM "$target" 2>/dev/null || true
  for ((tick = 0; tick < stop_timeout_ticks; tick++)); do
    kill -0 "$target" 2>/dev/null || break
    sleep 0.2
  done
  if kill -0 "$target" 2>/dev/null; then
    kill -KILL "$target" 2>/dev/null || true
    for ((tick = 0; tick < 10; tick++)); do
      kill -0 "$target" 2>/dev/null || break
      sleep 0.2
    done
  fi
  rm -f -- "$pid_file"
  printf 'ctk-server stopped (pid %s)\n' "$target"
}

do_status() {
  if server_running; then
    require_binary
    printf 'ctk-server running (pid %s) on %s\n' "$pid" "$(endpoint)"
    return 0
  fi
  printf 'ctk-server not running\n'
  exit 3
}

pid=""
case "$command_name" in
  start) do_start ;;
  stop) do_stop ;;
  restart)
    do_stop
    do_start
    ;;
  status) do_status ;;
esac
