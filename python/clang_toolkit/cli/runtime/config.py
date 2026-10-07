"""Layered, validated YAML settings for the interactive runtime."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """A settings file or update is invalid."""


DEFAULTS: dict[str, Any] = {
    "traversal": "AsIs",
    "extra_args": [],
    "compile_commands": None,
    "cache_dir": None,
    "files": [],
    "output": "stdout",
    "vars": {},
}
_ALLOWED_TRAVERSAL = {"AsIs", "IgnoreUnlessSpelledInSource"}
_ALLOWED_KEYS = frozenset(DEFAULTS)


def _merge(lower: dict[str, Any], upper: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(lower)
    for key, value in upper.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _validate(data: dict[str, Any]) -> None:
    unknown = set(data) - _ALLOWED_KEYS
    if unknown:
        raise ConfigError(f"unknown setting: {sorted(unknown)[0]}")
    if (
        not isinstance(data["traversal"], str)
        or data["traversal"] not in _ALLOWED_TRAVERSAL
    ):
        raise ConfigError("traversal must be AsIs or IgnoreUnlessSpelledInSource")
    if not isinstance(data["extra_args"], list) or not all(
        isinstance(arg, str) for arg in data["extra_args"]
    ):
        raise ConfigError("extra_args must be a list of strings")
    if data["compile_commands"] is not None and (not isinstance(data["compile_commands"], str) or not data["compile_commands"]):
        raise ConfigError("compile_commands must be a nonempty path string or null")
    if data["cache_dir"] is not None and not isinstance(data["cache_dir"], str):
        raise ConfigError("cache_dir must be a path string or null")
    if not isinstance(data["files"], list) or not all(
        isinstance(path, str) for path in data["files"]
    ):
        raise ConfigError("files must be a list of paths")
    if not isinstance(data["output"], str):
        raise ConfigError("output must be stdout or a path string")
    if not isinstance(data["vars"], dict) or not all(
        isinstance(key, str) for key in data["vars"]
    ):
        raise ConfigError("vars must be a mapping with string keys")


class ConfigStore:
    """Read system, home, and project files; persist only selected overlays."""

    def __init__(
        self,
        cwd: Path,
        *,
        home: Path | None = None,
        system: Path | None = None,
    ) -> None:
        user_home = home or Path.home()
        self.paths = {
            "system": system or Path("/etc/clang_tools/config.yaml"),
            "user": user_home / ".clang_tools.yaml",
            "project": cwd / ".clang_tools.yaml",
        }
        self.layers: dict[str, dict[str, Any]] = {}
        self._hashes: dict[str, str | None] = {}
        self.effective: dict[str, Any] = {}
        self.reload()

    @staticmethod
    def _hash(path: Path) -> str | None:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

    def reload(self) -> dict[str, Any]:
        layers: dict[str, dict[str, Any]] = {}
        hashes: dict[str, str | None] = {}
        effective = deepcopy(DEFAULTS)
        for scope in ("system", "user", "project"):
            path = self.paths[scope]
            hashes[scope] = self._hash(path)
            if not path.exists():
                layers[scope] = {}
                continue
            try:
                data = yaml.safe_load(path.read_text()) or {}
            except (OSError, yaml.YAMLError) as exc:
                raise ConfigError(f"cannot read {path}: {exc}") from exc
            if not isinstance(data, dict):
                raise ConfigError(f"{path}: expected a YAML mapping")
            if set(data) - _ALLOWED_KEYS:
                raise ConfigError(
                    f"{path}: unknown setting: {sorted(set(data) - _ALLOWED_KEYS)[0]}"
                )
            layers[scope] = data
            effective = _merge(effective, data)
        _validate(effective)
        self.layers = layers
        self._hashes = hashes
        self.effective = effective
        return deepcopy(effective)

    @property
    def revision(self) -> str:
        encoded = json.dumps(self.effective, sort_keys=True, default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    def set(self, key: str, value: Any, *, scope: str = "project") -> None:
        self._update(key, value, scope=scope, remove=False)

    def clear(self, key: str, *, scope: str = "project") -> None:
        self._update(key, None, scope=scope, remove=True)

    def _update(self, key: str, value: Any, *, scope: str, remove: bool) -> None:
        if scope not in {"project", "user"}:
            raise ConfigError("only project and user settings can be changed")
        if key not in _ALLOWED_KEYS:
            raise ConfigError(f"unknown setting: {key}")
        path = self.paths[scope]
        if self._hash(path) != self._hashes[scope]:
            raise ConfigError(
                f"{path} changed since settings were loaded; reload first"
            )
        layer = deepcopy(self.layers[scope])
        if remove:
            layer.pop(key, None)
        else:
            layer[key] = deepcopy(value)
        candidate = deepcopy(DEFAULTS)
        for name in ("system", "user", "project"):
            candidate = _merge(candidate, layer if name == scope else self.layers[name])
        _validate(candidate)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                delete=False,
            ) as handle:
                temp_name = handle.name
                yaml.safe_dump(layer, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        except OSError as exc:
            raise ConfigError(f"cannot save {path}: {exc}") from exc
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
        self.reload()
