"""Keep E2E console startup independent of machine-local script libraries."""

import subprocess

import pytest


@pytest.fixture(autouse=True)
def isolate_default_console_libraries(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Use empty libraries for CLI subprocesses unless a test names its own."""
    empty_libraries = tmp_path / "empty-ctk-libraries"
    empty_libraries.mkdir()
    original_popen = subprocess.Popen

    def isolated_popen(args, *positional, **options):
        if isinstance(args, (list, tuple)) and "-m" in args:
            module_index = args.index("-m")
            if (
                module_index + 1 < len(args)
                and args[module_index + 1] == "clang_toolkit.cli.app"
                and "--lib-dir" not in args
            ):
                args = [
                    *args[: module_index + 2],
                    "--lib-dir",
                    str(empty_libraries),
                    *args[module_index + 2 :],
                ]
        return original_popen(args, *positional, **options)

    monkeypatch.setattr(subprocess, "Popen", isolated_popen)
