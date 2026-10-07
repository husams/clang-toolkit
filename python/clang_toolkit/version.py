"""Version captured at installation, independent of the caller's checkout."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
import json


@dataclass(frozen=True)
class VersionInfo:
    version: str
    revision: str

    def format(self, component: str) -> str:
        return f"{component} {self.version} (revision {self.revision})"


def client_version() -> VersionInfo:
    try:
        data = json.loads(files("clang_toolkit").joinpath("_build_version.json").read_text())
        return VersionInfo(data["version"], data["revision"])
    except FileNotFoundError:
        try:
            installed = version("clang-toolkit")
        except PackageNotFoundError:
            installed = "unknown"
        return VersionInfo(installed, "unknown")
