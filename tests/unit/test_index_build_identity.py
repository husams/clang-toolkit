"""Build configuration must not invalidate unrelated project-index work."""

from __future__ import annotations

from pathlib import Path
import platform
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "api/index/v1/index_service.proto"
BASELINE = "7881a179b73526ee65b304d4872ee579a744b318a8d710661270fffcc5c548cd"


def cmake_script(tmp_path: Path, source: str) -> str:
    script = tmp_path / "test.cmake"
    script.write_text(source)
    result = subprocess.run(
        ["cmake", "-P", str(script)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return (tmp_path / "result").read_text()


def protocol_identity(tmp_path: Path, protocol: str) -> str:
    path = tmp_path / "index.proto"
    path.write_text(protocol)
    return cmake_script(
        tmp_path,
        f'''
include("{ROOT}/cmake/IndexProtocolFingerprint.cmake")
ctk_index_protocol_fingerprint("{path}" digest)
file(WRITE "{tmp_path}/result" "${{digest}}")
''',
    )


@pytest.mark.parametrize("change", ["none", "rpc", "inventory", "comments"])
def test_unrelated_protocol_updates_preserve_existing_index_identity(
    tmp_path: Path, change: str
) -> None:
    text = PROTOCOL.read_text()
    if change == "rpc":
        text = text.replace(
            "service IndexService {",
            "service IndexService {\n  rpc Health(ProjectIndexRequest) returns (ProjectIndexStatus);",
        )
    elif change == "inventory":
        text = text.replace(
            "uint64 total_count = 2;",
            "uint64 total_count = 2;\n  string display_name = 3;",
        )
    elif change == "comments":
        text = text.replace(
            "message IndexWorkerRequest {",
            "// UI-only release\nmessage IndexWorkerRequest {\n /* A comment does not change the wire contract. */\n",
        )
    assert protocol_identity(tmp_path, text) == BASELINE


@pytest.mark.parametrize(
    "before,after",
    [
        ("string source = 1;", "bytes source = 1;"),
        ("string usr = 1;", "bytes usr = 1;"),
        ("uint64 reused_header_symbols = 7;", "uint64 reused_header_symbols = 8;"),
    ],
)
def test_worker_and_symbol_contract_changes_invalidate_index_identity(
    tmp_path: Path, before: str, after: str
) -> None:
    text = PROTOCOL.read_text().replace(before, after)
    assert protocol_identity(tmp_path, text) != BASELINE


@pytest.mark.parametrize("architecture", [None, "", "arm64", "arm64;x86_64"])
def test_macos_architecture_is_pinned_and_explicit_settings_are_preserved(
    tmp_path: Path, architecture: str | None
) -> None:
    configured = (
        ""
        if architecture is None
        else f'set(CMAKE_OSX_ARCHITECTURES "{architecture}" CACHE STRING "selected architecture")'
    )
    expected = platform.machine() if architecture is None else architecture
    result = cmake_script(
        tmp_path,
        f'''
set(CMAKE_HOST_APPLE TRUE)
set(CMAKE_HOST_SYSTEM_PROCESSOR arm64)
set(CTK_LLVM_ROOT "")
{configured}
include("{ROOT}/cmake/Platform.cmake")
include("{ROOT}/cmake/Platform.cmake")
get_property(pinned CACHE CMAKE_OSX_ARCHITECTURES PROPERTY TYPE)
if(NOT pinned STREQUAL "STRING")
  message(FATAL_ERROR "Architecture default was not saved in the build cache")
endif()
file(WRITE "{tmp_path}/result" "${{CMAKE_OSX_ARCHITECTURES}}")
''',
    )
    assert result == expected
