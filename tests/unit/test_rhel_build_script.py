"""Exercise RHEL repository setup without changing the host's repositories."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest


def test_e2e_uses_compiler_from_selected_build_directory(tmp_path: Path) -> None:
    script = (Path(__file__).resolve().parents[2] / "scripts/build-rhel9.sh").read_text()
    phase = script.split('if [[ "${SKIP_TESTS:-0}" != 1 ]]; then\n', 1)[1]
    phase = phase.split('\nfi\nif [[ "${PACKAGE:-0}"', 1)[0]
    build_dir = tmp_path / "custom build"
    native_tests = build_dir / "server/tests/ctk_tests"
    native_tests.parent.mkdir(parents=True)
    native_tests.write_text("#!/bin/sh\nexit 0\n")
    native_tests.chmod(0o755)
    compiler = "/opt/custom toolchain/bin/clang++"
    (build_dir / "ctk-clang-tool-path.txt").write_text(compiler + "\n")
    log = tmp_path / "test-environment.log"
    result = subprocess.run(["bash", "-c", """
set -euo pipefail
build_dir="$BUILD_PATH"
repo_root="$PROJECT_PATH"
server_binary="$build_dir/server/ctk-server"
uv() { printf '%s|%s\n' "$CTK_SERVER" "$CTK_TEST_CLANG" >> "$COMMAND_LOG"; }
""" + phase], env=os.environ | {
        "BUILD_PATH": str(build_dir), "PROJECT_PATH": str(tmp_path),
        "COMMAND_LOG": str(log), "CTK_SERVER": "stale-server",
        "CTK_TEST_CLANG": "stale-compiler",
    }, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert log.read_text().splitlines() == [
        "stale-server|stale-compiler",
        f"{build_dir}/server/ctk-server|{compiler}",
    ]


@pytest.mark.parametrize(
    ("distribution", "repositories", "has_subscription_manager", "expected"),
    [
        ("rhel", "ubi-9-codeready-builder-rpms UBI disabled", False,
         "dnf config-manager --set-enabled ubi-9-codeready-builder-rpms"),
        ("rhel", "ubi-9-codeready-builder-rpms UBI disabled", True,
         "dnf config-manager --set-enabled ubi-9-codeready-builder-rpms"),
        ("rhel", "codeready-builder-for-rhel-9-rhui-rpms RHUI disabled", False,
         "dnf config-manager --set-enabled codeready-builder-for-rhel-9-rhui-rpms"),
        ("rhel", "codeready-builder-for-rhel-9-x86_64-rpms RHEL enabled", True,
         "subscription-manager repos --enable codeready-builder-for-rhel-9-x86_64-rpms"),
        ("rhel", "codeready-builder-for-rhel-9-x86_64-rpms RHEL enabled", False,
         "dnf config-manager --set-enabled codeready-builder-for-rhel-9-x86_64-rpms"),
        ("rhel", "custom-build Custom enabled", False, None),
        ("rhel", "custom-build Custom enabled", True,
         "subscription-manager repos --enable codeready-builder-for-rhel-9-x86_64-rpms"),
        ("rhel", "codeready-builder-for-rhel-9-x86_64-debug-rpms Debug disabled\n"
         "codeready-builder-for-rhel-9-x86_64-source-rpms Source disabled", False, None),
        ("rocky", "crb CRB disabled", False,
         "dnf config-manager --set-enabled crb"),
    ],
)
def test_builder_repository_setup(
    tmp_path: Path,
    distribution: str,
    repositories: str,
    has_subscription_manager: bool,
    expected: str | None,
) -> None:
    script = (Path(__file__).resolve().parents[2] / "scripts/build-rhel9.sh").read_text()
    # Execute the actual dependency setup through builder enablement, stopping
    # before EPEL/package installation and platform-specific build commands.
    setup = script.split('if [[ "${SKIP_DEPS:-0}" != 1 ]]; then\n', 1)[1]
    setup = setup.split('  if ! rpm -q epel-release', 1)[0]
    log = tmp_path / "commands.log"
    environment = os.environ | {
        "ID": distribution,
        "REPOSITORIES": repositories,
        "HAS_SUBSCRIPTION_MANAGER": str(int(has_subscription_manager)),
        "COMMAND_LOG": str(log),
    }
    result = subprocess.run(
        ["bash", "-c", """
set -euo pipefail
privilege=(sudo)
sudo() { "$@"; }
dnf() {
  printf 'dnf %s\n' "$*" >> "$COMMAND_LOG"
  if [[ "$*" == '-q repolist --all' ]]; then
    printf '%s\n' "$REPOSITORIES"
  fi
}
command() {
  if [[ "$*" == '-v subscription-manager' ]]; then
    [[ "$HAS_SUBSCRIPTION_MANAGER" == 1 ]]
  else
    builtin command "$@"
  fi
}
subscription-manager() {
  [[ "$HAS_SUBSCRIPTION_MANAGER" == 1 ]] || return 127
  printf 'subscription-manager %s\n' "$*" >> "$COMMAND_LOG"
}
arch() { printf 'x86_64\n'; }
""" + setup],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    commands = log.read_text().splitlines()
    changes = [line for line in commands if "--set-enabled" in line or "repos --enable" in line]
    assert changes == ([] if expected is None else [expected])
    if distribution == "rhel" and expected is None:
        assert "using existing repositories" in result.stdout


@pytest.mark.parametrize(
    ("package", "install", "already_installed", "action"),
    [(False, False, False, None), (True, False, False, None),
     (False, True, False, "install"), (False, True, True, "reinstall")],
)
def test_rpm_package_install(
    tmp_path: Path, package: bool, install: bool, already_installed: bool,
    action: str | None,
) -> None:
    script = (Path(__file__).resolve().parents[2] / "scripts/build-rhel9.sh").read_text()
    phase = script[script.index('if [[ "${PACKAGE:-0}" == 1'):]
    (tmp_path / "ctk-rpm-filename.txt").write_text("server.rpm\n")
    package_file = tmp_path / "packages/server.rpm"
    log = tmp_path / "commands.log"
    log.touch()
    environment = os.environ | {
        "PACKAGE": str(int(package)), "INSTALL": str(int(install)),
        "RPM_INSTALLED": str(int(already_installed)),
        "BUILD_PATH": str(tmp_path), "RPM_PATH": str(package_file),
        "COMMAND_LOG": str(log),
    }
    result = subprocess.run(["bash", "-c", """
set -euo pipefail
build_dir="$BUILD_PATH"
server_binary="$BUILD_PATH/ctk-server"
privilege=(sudo)
sudo() { "$@"; }
fail() { printf '%s\n' "$*" >&2; exit 1; }
rpmbuild() { :; }
cpack() {
  printf 'cpack %s\n' "$*" >> "$COMMAND_LOG"
  mkdir -p "$(dirname "$RPM_PATH")"
  touch "$RPM_PATH"
}
rpm() {
  if [[ "$1" == -qp ]]; then
    printf 'clang-toolkit-server-0.1.0-1.el9.x86_64'
  else
    [[ "$RPM_INSTALLED" == 1 ]]
  fi
}
dnf() { printf 'dnf %s\n' "$*" >> "$COMMAND_LOG"; }
""" + phase], env=environment, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    commands = log.read_text().splitlines()
    packages = [command for command in commands if command.startswith("cpack ")]
    assert len(packages) == int(package or install)
    transactions = [command for command in commands if command.startswith("dnf ")]
    assert transactions == ([] if action is None else [f"dnf -y {action} {package_file}"])
