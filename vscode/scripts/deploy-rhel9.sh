#!/usr/bin/env bash
# Deploy this checkout's prototype, Python runtime and local CTK server on RHEL 9.
# Run as the VS Code user (also from a Remote-SSH terminal), never with sudo bash.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
deploy_dir="${XDG_DATA_HOME:-$HOME/.local/share}/ctk-vscode"
workspace=""
library_dir="$HOME/.ctk/lib"
endpoint=""
manage_server=0
code_cli="code"
profile=""
vsix=""
skip_deps=0
full_tests=0
dry_run=0
scratch=""
service_name=ctk-vscode-prototype.service

fail() { printf 'error: %s\n' "$*" >&2; exit 1; }
step() { printf '\nCTK: %s\n' "$*"; }
absolute() { case "$1" in /*) printf '%s\n' "$1" ;; *) printf '%s/%s\n' "$PWD" "$1" ;; esac; }
usage() {
  cat <<'USAGE'
Usage: bash vscode/scripts/deploy-rhel9.sh [options]

  --workspace DIR   C++ project to open (default: a private demo workspace)
  --repo DIR        Prototype checkout (default: this script's checkout)
  --prefix DIR      User-owned deployment directory (default: ~/.local/share/ctk-vscode)
  --code FILE       VS Code CLI, including the CLI in a Remote-SSH terminal
  --profile NAME    Install into this VS Code profile
  --library-directory DIR  Console helpers (default: ~/.ctk/lib; existing files kept)
  --vsix FILE       Use a VSIX matching this checkout, without Node/pnpm/build
  --server ADDRESS  Use an existing local server; skip native build/user service
                    Accepts unix:///absolute/path or localhost/127.0.0.1:PORT
  --skip-deps       Do not use sudo/DNF or bootstrap missing uv/Node/VS Code
  --full-tests      Also run all native and Python tests during the native build
  --dry-run        Show deployment steps without installing or writing anything
  -h, --help        Show this help

Default deployment installs missing prerequisites, builds CTK and the VSIX,
checks the extension, installs a private Python 3.14 environment and helper
library, starts a dedicated user service, verifies live unsaved AST navigation,
installs the extension, and writes a ready-to-open .code-workspace file.
Existing project settings and helper files are kept. No VS Code window opens.
Internet and sudo access are needed unless prerequisites are already present.
USAGE
}
parse_options() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --workspace|--repo|--prefix|--code|--profile|--library-directory|--vsix|--server)
        [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || fail "$1 requires a value"
        case "$1" in
          --workspace) workspace="$(absolute "$2")" ;;
          --repo) repo_root="$(absolute "$2")" ;;
          --prefix) deploy_dir="$(absolute "$2")" ;;
          --code) code_cli="$2" ;;
          --profile) profile="$2" ;;
          --library-directory) library_dir="$(absolute "$2")" ;;
          --vsix) vsix="$(absolute "$2")" ;;
          --server) endpoint="$2" ;;
        esac
        shift 2 ;;
      --skip-deps) skip_deps=1; shift ;;
      --full-tests) full_tests=1; shift ;;
      --dry-run) dry_run=1; shift ;;
      -h|--help) usage; exit 0 ;;
      *) fail "Unknown option: $1 (use --help)" ;;
    esac
  done
  for path in "$deploy_dir" "$repo_root" "$workspace" "$library_dir"; do
    [[ "$path" != *$'\n'* && "$path" != *$'\r'* ]] || fail 'Paths cannot contain line breaks'
  done
  [[ -f "$repo_root/vscode/package.json" && -f "$repo_root/uv.lock" ]] \
    || fail 'Use --repo to select the checkout containing the VS Code prototype and uv.lock'
  [[ -z "$workspace" || -d "$workspace" ]] || fail "Workspace directory does not exist: $workspace"
  [[ -z "$vsix" || -f "$vsix" ]] || fail "VSIX does not exist: $vsix"
  if [[ -n "$endpoint" ]]; then
    [[ "$endpoint" != *$'\n'* && "$endpoint" != *$'\r'* ]] || fail 'Server address cannot contain line breaks'
    if [[ "$endpoint" == unix:///* ]]; then
      [[ "$endpoint" != unix:/// ]] || fail 'The Unix socket requires a filename'
    elif [[ "$endpoint" =~ ^(localhost|127\.0\.0\.1):([0-9]{1,5})$ ]]; then
      local port="${BASH_REMATCH[2]}"
      (( 10#$port > 0 && 10#$port < 65536 )) || fail 'Server port must be between 1 and 65535'
    else
      fail '--server requires unix:///absolute/path or localhost/127.0.0.1:PORT'
    fi
  fi
}
check_platform() {
  [[ "$(uname -s)" == Linux && -r /etc/os-release ]] || fail 'RHEL 9 or a compatible Linux distribution is required'
  # shellcheck disable=SC1091
  source /etc/os-release
  [[ "${VERSION_ID%%.*}" == 9 && " ${ID:-} ${ID_LIKE:-} " =~ [[:space:]](rhel|rocky|almalinux|centos)[[:space:]] ]] \
    || fail 'RHEL/Rocky/AlmaLinux/CentOS Stream 9 is required'
  [[ "$(id -u)" != 0 ]] || fail 'Run as your normal VS Code user; the script uses sudo only for system packages'
}
ensure_uv() {
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv >/dev/null; then
    [[ "$skip_deps" == 0 ]] || fail 'uv is missing; run without --skip-deps'
    curl --fail --show-error --location https://astral.sh/uv/install.sh -o "$scratch/uv-install.sh"
    UV_NO_MODIFY_PATH=1 UV_INSTALL_DIR="$HOME/.local/bin" sh "$scratch/uv-install.sh"
  fi
}
ensure_code() {
  if ! command -v "$code_cli" >/dev/null; then
    [[ "$code_cli" == code && "$skip_deps" == 0 ]] || fail 'VS Code CLI missing; use --code or run from a VS Code Remote-SSH terminal'
    step 'Installing VS Code from the official Microsoft RPM repository'
    cat > "$scratch/vscode.repo" <<'REPO'
[ctk-vscode-microsoft]
name=Visual Studio Code (Microsoft)
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
REPO
    sudo install -m 644 "$scratch/vscode.repo" /etc/yum.repos.d/ctk-vscode-microsoft.repo
    sudo dnf -y install code
  fi
  code_cli="$(command -v "$code_cli")"
  local version major minor
  version="$("$code_cli" --version)"
  version="${version%%$'\n'*}"
  [[ "$version" =~ ^([0-9]+)\.([0-9]+)\. ]] || fail 'Could not read the VS Code CLI version'
  major="${BASH_REMATCH[1]}"; minor="${BASH_REMATCH[2]}"
  (( major > 1 || (major == 1 && minor >= 100) )) || fail 'VS Code 1.100+ is required; update your desktop/Remote-SSH installation'
}
ensure_node() {
  if command -v node >/dev/null && command -v npm >/dev/null && node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)'; then
    return
  fi
  local node_bin
  for node_bin in "$deploy_dir"/tools/node-v*-linux-*/bin; do
    [[ -x "$node_bin/node" && -x "$node_bin/npm" ]] || continue
    if "$node_bin/node" -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)'; then
      export PATH="$node_bin:$PATH"
      return
    fi
  done
  [[ "$skip_deps" == 0 ]] || fail 'Node 22+ with npm is missing; install it or pass --vsix'
  local architecture manifest archive checksum directory
  case "$(uname -m)" in x86_64) architecture=x64 ;; aarch64|arm64) architecture=arm64 ;; *) fail 'Node bootstrap supports x86_64 and aarch64' ;; esac
  manifest="$scratch/node-sha256.txt"
  curl --fail --show-error --location https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt -o "$manifest"
  archive="$(awk -v suffix="-linux-$architecture.tar.xz" '$2 ~ /^node-v22\.[0-9]+\.[0-9]+-linux-/ && substr($2,length($2)-length(suffix)+1)==suffix {print $2}' "$manifest")"
  [[ "$archive" =~ ^node-v22\.[0-9]+\.[0-9]+-linux-(x64|arm64)\.tar\.xz$ ]] || fail 'Invalid Node download manifest'
  checksum="$(awk -v archive="$archive" '$2==archive {print $1}' "$manifest")"
  curl --fail --show-error --location "https://nodejs.org/dist/latest-v22.x/$archive" -o "$scratch/$archive"
  (cd "$scratch" && printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check -)
  directory="${archive%.tar.xz}"
  mkdir -p "$deploy_dir/tools"
  tar -xJf "$scratch/$archive" -C "$deploy_dir/tools"
  export PATH="$deploy_dir/tools/$directory/bin:$PATH"
}
build_extension() {
  ensure_node
  local manager
  manager="$(node -p 'require(process.argv[1]).packageManager' "$repo_root/vscode/package.json")"
  [[ "$manager" =~ ^pnpm@[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail 'The prototype must pin a pnpm version'
  npm install --prefix "$deploy_dir/tools/pnpm" --no-audit --no-fund "$manager"
  local pnpm_cli="$deploy_dir/tools/pnpm/node_modules/.bin/pnpm"
  # Package scripts invoke pnpm again; they must find this same pinned binary.
  export PATH="$deploy_dir/tools/pnpm/node_modules/.bin:$PATH"
  "$pnpm_cli" --dir "$repo_root/typescript" install --frozen-lockfile
  "$pnpm_cli" --dir "$repo_root/typescript" build
  "$pnpm_cli" --dir "$repo_root/vscode" install --frozen-lockfile
  "$pnpm_cli" --dir "$repo_root/vscode" check
  "$pnpm_cli" --dir "$repo_root/vscode" lint
  CTK_PYTHON="$python_binary" "$pnpm_cli" --dir "$repo_root/vscode" test
  "$pnpm_cli" --dir "$repo_root/vscode" package
  vsix="$repo_root/vscode/artifacts/clang-toolkit-prototype.vsix"
}
write_configuration() {
  "$python_binary" - "$deploy_dir" "$workspace" "$endpoint" "$unit_file" "$library_dir" <<'PY'
import json
from pathlib import Path
import re
import sys
import yaml

root, workspace, endpoint, unit, library = sys.argv[1:]
root = Path(root)
if endpoint.startswith('unix:///'):
    socket = endpoint.removeprefix('unix://')
    if len(socket.encode()) > 100:
        raise SystemExit('Unix socket path is too long; use a shorter XDG_RUNTIME_DIR')
    network = {'transport': 'unix', 'unix': {'socket_path': socket}}
else:
    match = re.fullmatch(r'(localhost|127\.0\.0\.1):([0-9]+)', endpoint)
    if not match or not 0 < int(match[2]) < 65536:
        raise SystemExit('--server requires an absolute Unix socket or loopback TCP address')
    network = {'transport': 'tcp', 'tcp': {'host': match[1], 'port': int(match[2])}}
config = root / 'server.yaml'
config.write_text(yaml.safe_dump({'network': network}))
config.chmod(0o600)
settings = {'ctk.server': endpoint, 'ctk.configPath': str(config),
            'ctk.pythonPath': str(root / 'runtime/bin/python'),
            'ctk.libraryDirectory': library}
(root / 'ctk.code-workspace').write_text(json.dumps(
    {'folders': [{'path': workspace}], 'settings': settings}, indent=2) + '\n')
if unit:
    def quoted(text, command=False):
        text = str(text).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
        return '"' + (text.replace('$', '$$') if command else text) + '"'
    Path(unit).parent.mkdir(parents=True, exist_ok=True)
    Path(unit).write_text(
        '# Managed by clang-toolkit vscode/scripts/deploy-rhel9.sh\n'
        '[Unit]\nDescription=CTK VS Code prototype server\n\n[Service]\n'
        'Type=simple\nUMask=0077\nRuntimeDirectory=ctk-vscode\nRuntimeDirectoryMode=0700\n'
        f'ExecStart={quoted(root / "bin/ctk-server", True)} -c {quoted(config, True)}\n'
        f'Environment={quoted("CTK_STORAGE_ROOT=" + str(root / "storage"))}\n'
        'Restart=on-failure\nRestartSec=2\n\n[Install]\nWantedBy=default.target\n')
PY
}
smoke_test() {
  "$python_binary" - "$scratch" "$deploy_dir" "$endpoint" "$library_dir" <<'PY'
from pathlib import Path
import sys
import grpc

scratch, root, endpoint, library = sys.argv[1:]
sys.path.insert(0, str(Path(root) / 'console'))
from action_service import ActionHost

with grpc.insecure_channel(endpoint) as channel:
    grpc.channel_ready_future(channel).result(timeout=20)
source = Path(scratch) / 'probe.cpp'
saved = 'struct SavedOnly {};\n'
source.write_text(saved)
settings = dict(directory=scratch, endpoint=endpoint,
                configPath=str(Path(root) / 'server.yaml'), timeoutMs=30000,
                compileArguments=['-std=c++20'], libraryDirectory=library,
                buffers={str(source): 'struct Base { int draft; };\nstruct Derived : Base {};\n'})
host = ActionHost(settings)
try:
    version = host.client.server_version()
    page = host.inspector.inspect(dict(settings=settings, translationUnit=str(source)))
    derived = next(node for node in page['children'] if node['name'] == 'Derived')
    page = host.inspector.inspect(dict(settings=settings, nodeId=derived['id']))
    base_id = page['semantics']['inheritance'][0]['nodeId']
    base = host.inspector.inspect(dict(settings=settings, nodeId=base_id))
    assert base['node']['name'] == 'Base'
    assert any(node['name'] == 'Base::draft' for node in base['children'])
    assert source.read_text() == saved
    assert base['parseCount'] == 1
    action = dict(title='Deployment check', path=str(source.with_suffix('.ctk-action')),
                  arguments=[], callable='deployment_fields',
                  generated='let deployment_fields(node) = { match fieldDecl().bind("field") in node }')
    result = host.run(dict(settings=settings, action=action, inputId=base_id,
                           values={}, maximum=10), lambda progress: None)
    assert result['matches'] == 1 and result['parseCount'] == 1
    assert any(item['binding'] == 'field' and item['name'] == 'Base::draft'
               for item in result['results'])
    print(f'Live CTK {version.version} ({version.revision}): unsaved AST, base navigation and node action verified.')
finally:
    host.close()
PY
}
main() {
  parse_options "$@"
  [[ -n "$endpoint" ]] || manage_server=1
  if [[ "$dry_run" == 1 ]]; then
    printf 'Target: RHEL 9; checkout: %s; deployment: %s\n' "$repo_root" "$deploy_dir"
    [[ "$skip_deps" == 1 ]] || printf 'Install missing RHEL dependencies, uv/Python, Node 22 and VS Code.\n'
    [[ -n "$endpoint" ]] && printf 'Use existing local server: %s\n' "$endpoint" \
      || printf 'Build native CTK and enable/restart dedicated user service %s.\n' "$service_name"
    [[ -n "$vsix" ]] && printf 'Use matching VSIX: %s\n' "$vsix" \
      || printf 'Install pinned pnpm; build SDK; run extension checks/tests; package VSIX.\n'
    printf 'Install private Python runtime/helpers; verify live unsaved AST navigation.\n'
    printf 'Install extension using %s; verify installed version; generate ctk.code-workspace.\n' "$code_cli"
    return
  fi
  check_platform
  command -v flock >/dev/null || fail 'flock is required (RHEL util-linux package)'
  [[ ! -L "$deploy_dir" ]] || fail 'Deployment directory cannot be a symlink'
  if [[ -d "$deploy_dir" && ! -f "$deploy_dir/.ctk-vscode-deployment" ]]; then
    [[ -z "$(ls -A -- "$deploy_dir")" ]] || fail 'Choose an empty --prefix directory; this directory is not managed by this installer'
  fi
  unit_file=""
  if [[ "$manage_server" == 1 ]]; then
    unit_file="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/$service_name"
    if [[ -f "$unit_file" ]]; then
      local marker
      IFS= read -r marker < "$unit_file" || true
      [[ "$marker" == '# Managed by clang-toolkit vscode/scripts/deploy-rhel9.sh' ]] || fail 'Existing user service is not managed by this installer'
    fi
    systemctl --user show-environment >/dev/null \
      || fail 'A working systemd user session is required; use a login/Remote-SSH terminal or --server'
  fi
  [[ "$skip_deps" == 1 ]] || command -v sudo >/dev/null || fail 'sudo is required to install system dependencies'
  scratch="$(mktemp -d /tmp/ctk-vscode-deploy.XXXXXX)"
  trap 'rm -rf -- "$scratch"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  mkdir -p "$deploy_dir"
  exec 9>"$deploy_dir/.deploy.lock"
  flock -n 9 || fail 'Another deployment is using this prefix'
  touch "$deploy_dir/.ctk-vscode-deployment"
  export PATH="$HOME/.local/bin:$PATH"
  if [[ "$skip_deps" == 0 ]]; then
    if [[ "$manage_server" == 1 ]]; then
      DEPS_ONLY=1 SKIP_DEPS=0 bash "$repo_root/scripts/build-rhel9.sh"
    fi
    local packages=(python3 tar xz unzip)
    command -v curl >/dev/null || packages+=(curl)
    sudo dnf -y install "${packages[@]}"
  fi
  ensure_uv
  ensure_code
  if [[ "$manage_server" == 1 ]]; then
    step 'Building the native server from this checkout'
    SKIP_DEPS=1 SKIP_TESTS="$((1-full_tests))" PACKAGE=0 INSTALL=0 \
      BUILD_DIR="$repo_root/build/rhel9-vscode" bash "$repo_root/scripts/build-rhel9.sh"
    local binary linkage
    for binary in ctk-server ctk-index-worker; do
      [[ -f "$repo_root/build/rhel9-vscode/server/$binary" ]] || fail "Native build did not produce $binary"
      linkage="$(ldd "$repo_root/build/rhel9-vscode/server/$binary")"
      [[ "$linkage" != *'not found'* ]] || fail "$binary has missing shared libraries"
    done
    mkdir -p "$deploy_dir/bin"
    for binary in ctk-server ctk-index-worker; do
      install -m 755 "$repo_root/build/rhel9-vscode/server/$binary" "$deploy_dir/bin/$binary.new"
      mv -f "$deploy_dir/bin/$binary.new" "$deploy_dir/bin/$binary"
    done
    endpoint="unix://${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/ctk-vscode/ctk.sock"
  fi
  step 'Installing the private Python runtime from the locked checkout'
  UV_PROJECT_ENVIRONMENT="$deploy_dir/runtime" uv sync --project "$repo_root" --frozen --no-editable --no-dev
  python_binary="$deploy_dir/runtime/bin/python"
  "$python_binary" -c 'import sys,grpc,yaml,lark,prompt_toolkit,rich; assert sys.version_info >= (3,14)'
  if [[ -z "$vsix" ]]; then step 'Building and checking the extension'; build_extension; fi
  version="$("$python_binary" - "$vsix" "$repo_root/vscode/package.json" <<'PY'
import json, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    package = json.loads(archive.read('extension/package.json'))
expected = json.load(open(sys.argv[2]))
if (package['publisher'], package['name'], package['version']) != (
        expected['publisher'], expected['name'], expected['version']):
    raise SystemExit('VSIX identity/version does not match this checkout')
print(package['version'])
PY
)"
  mkdir -p "$library_dir" "$deploy_dir/console"
  [[ -e "$library_dir/ctk_helpers.ctk" ]] || install -m 644 "$repo_root/skills/ctk-script/scripts/ctk_helpers.ctk" "$library_dir/ctk_helpers.ctk"
  # Inspect the actual packaged worker, not a different installed Python client.
  "$python_binary" - "$vsix" "$deploy_dir/console" <<'PY'
from pathlib import Path
import sys, zipfile
target = Path(sys.argv[2])
with zipfile.ZipFile(sys.argv[1]) as archive:
    for item in archive.infolist():
        if item.filename.startswith('extension/console/') and not item.is_dir():
            relative = Path(item.filename.removeprefix('extension/console/'))
            if relative.is_absolute() or '..' in relative.parts:
                raise SystemExit('Unsafe VSIX member path')
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(item))
PY
  if [[ -z "$workspace" ]]; then
    workspace="$deploy_dir/demo"
    mkdir -p "$workspace/.ctk/actions"
    [[ -e "$workspace/semantic-inspector.cpp" ]] || cp "$repo_root/vscode/examples/semantic-inspector.cpp" "$workspace/"
    [[ -e "$workspace/actions-demo.cpp" ]] || cp "$repo_root/vscode/examples/actions-demo.cpp" "$workspace/"
    [[ -e "$workspace/.ctk/actions/order-fields.ctk-action" ]] || cp "$repo_root/vscode/examples/order-fields.ctk-action" "$workspace/.ctk/actions/"
  fi
  write_configuration
  if [[ -n "$unit_file" ]]; then
    systemctl --user daemon-reload
    systemctl --user enable "$service_name"
    systemctl --user restart "$service_name"
  fi
  step 'Checking the live server and packaged unsaved-buffer inspector'
  smoke_test
  local code_command=("$code_cli")
  [[ -z "$profile" ]] || code_command+=(--profile "$profile")
  "${code_command[@]}" --install-extension "$vsix" --force
  installed="$("${code_command[@]}" --list-extensions --show-versions)"
  [[ $'\n'"$installed"$'\n' == *$'\n'"clang-toolkit.clang-toolkit-prototype@$version"$'\n'* ]] || fail 'VS Code did not report the expected installed extension version'
  if [[ ! "$vsix" -ef "$deploy_dir/clang-toolkit-prototype.vsix" ]]; then
    cp "$vsix" "$deploy_dir/clang-toolkit-prototype.vsix"
  fi
  sha256sum "$deploy_dir/clang-toolkit-prototype.vsix" > "$deploy_dir/vsix.sha256"
  step "Installed prototype $version. Open this workspace, then trust it to enable CTK:"
  printf '%q ' "${code_command[@]}" "$deploy_dir/ctk.code-workspace"
  printf '\nReload an existing VS Code window to activate an extension update.\n'
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
