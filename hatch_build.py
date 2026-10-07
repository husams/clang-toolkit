"""Stamp the installed client, including wheels built from source archives."""
from pathlib import Path
import json
import runpy
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        root = Path(self.root)
        helpers = runpy.run_path(str(root / "scripts/generate_version.py"))
        info = helpers["build_version"](root)
        stamp = root / "python/clang_toolkit/_build_version.json"
        helpers["write_if_changed"](stamp, json.dumps(info) + "\n")
        build_data["artifacts"].append("python/clang_toolkit/_build_version.json")
