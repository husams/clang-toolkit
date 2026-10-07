"""Shared YAML configuration for the clang-toolkit gRPC client and server."""

from __future__ import annotations

import copy
import ipaddress
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml


class ConfigurationError(ValueError):
    """Raised when a configuration file is malformed or invalid."""


@dataclass(frozen=True)
class NetworkConfig:
    target: str
    transport: str
    client_options: tuple[tuple[str, int], ...]
    server_options: tuple[tuple[str, int], ...]
    rpc_timeout: float | None
    shutdown_grace: float | None
    pool_size: int
    queue_size: int
    max_files: int
    max_memory_bytes: int
    provenance: Mapping[str, str] = field(default_factory=dict)
    effective_values: Mapping[str, Any] = field(default_factory=dict)


_DEFAULTS: dict[str, Any] = {
    "version": 1,
    "network": {"transport": "unix", "unix": {"socket_path": None}, "tcp": {}},
    "pool": {"size": 3},
    "queue": {"size": 100},
    "server": {"grpc": {"max_send_message_bytes": 67_108_864}, "shutdown_grace_ms": None},
    "session": {"max_files": 100, "max_memory_bytes": 2_147_483_648},
    "client": {"grpc": {"max_receive_message_bytes": 67_108_864}, "rpc_timeout_ms": None},
}
_ALLOWED = {
    "": {"version", "network", "pool", "queue", "server", "session", "client"},
    "network": {"transport", "unix", "tcp"},
    "network.unix": {"socket_path"},
    "network.tcp": {"host", "port"},
    "pool": {"size"},
    "queue": {"size"},
    "server": {"grpc", "shutdown_grace_ms"},
    "client": {"grpc", "rpc_timeout_ms"},
    "server.grpc": {"max_receive_message_bytes", "max_send_message_bytes"},
    "client.grpc": {"max_receive_message_bytes", "max_send_message_bytes"},
    "session": {"max_files", "max_memory_bytes"},
}


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    prefix = getattr(loader, "_key_path", ())
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise ConfigurationError("configuration mapping keys must be strings")
        if key in result:
            raise ConfigurationError(f"duplicate YAML key: {'.'.join((*prefix, key))}")
        loader._key_path = (*prefix, key)
        try:
            result[key] = loader.construct_object(value_node, deep=True)
        finally:
            loader._key_path = prefix
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping
)


def _decimal_integer(loader: _UniqueKeyLoader, node: yaml.ScalarNode) -> int:
    value = loader.construct_scalar(node)
    if re.fullmatch(r"-?[0-9]+", value) is None:
        path = ".".join(getattr(loader, "_key_path", ()))
        raise ConfigurationError(f"{path or 'configuration'}: configuration integers must use base-10 notation")
    return int(value, 10)


_UniqueKeyLoader.add_constructor("tag:yaml.org,2002:int", _decimal_integer)


def _validate_keys(
    value: Any, path: str = "", active: set[int] | None = None, depth: int = 0
) -> None:
    if not isinstance(value, dict):
        if isinstance(value, list):
            raise ConfigurationError(f"{path or 'configuration'}: sequences are not supported")
        if isinstance(value, str) and "\0" in value:
            raise ConfigurationError(f"{path or 'configuration'}: embedded NUL is not supported")
        return
    active = active if active is not None else set()
    if depth >= 64:
        raise ConfigurationError(f"{path or 'configuration'}: nesting exceeds 63 levels")
    if id(value) in active:
        raise ConfigurationError(f"{path or 'configuration'}: recursive YAML aliases are not supported")
    active.add(id(value))
    allowed = _ALLOWED.get(path)
    if allowed is None:
        raise ConfigurationError(f"unknown configuration mapping: {path}")
    for key, child in value.items():
        if not isinstance(key, str) or key not in allowed:
            raise ConfigurationError(f"unknown configuration key: {path + '.' if path else ''}{key}")
        if "\0" in key:
            raise ConfigurationError("configuration keys cannot contain NUL")
        child_path = f"{path}.{key}" if path else key
        if child_path in _ALLOWED and not isinstance(child, dict):
            raise ConfigurationError(f"{child_path} must be a mapping")
        if isinstance(child, dict):
            _validate_keys(child, child_path, active, depth + 1)
        else:
            _validate_keys(child, child_path, active, depth + 1)
    active.remove(id(value))


def _merge(base: dict[str, Any], override: dict[str, Any], origin: Path, origins: dict[str, Path], prefix: str = "") -> None:
    for key, value in override.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value, origin, origins, dotted)
        else:
            base[key] = copy.deepcopy(value)
            origins[dotted] = origin


def _load_file(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            value = yaml.load(stream, Loader=_UniqueKeyLoader)
    except (OSError, yaml.YAMLError, ConfigurationError) as exc:
        raise ConfigurationError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"{path}: top-level YAML value must be a mapping")
    try:
        _validate_keys(value)
        _validate_supplied_values(value)
    except ConfigurationError as exc:
        raise ConfigurationError(f"{path}: {exc}") from exc
    return value


def _validate_supplied_values(value: dict[str, Any]) -> None:
    def integer(
        mapping: dict[str, Any], key: str, dotted: str, *, minimum: int,
        maximum: int = (1 << 63) - 1,
        nullable: bool = False,
    ) -> None:
        if key in mapping and not (nullable and mapping[key] is None) and (
            type(mapping[key]) is not int
            or mapping[key] < minimum
            or mapping[key] > maximum
        ):
            raise ConfigurationError(f"{dotted} must be an integer from {minimum} to {maximum}")

    if "version" in value and (type(value["version"]) is not int or value["version"] != 1):
        raise ConfigurationError("version must be integer 1")
    network = value.get("network", {})
    if "transport" in network and network["transport"] not in ("unix", "tcp"):
        raise ConfigurationError("network.transport must be 'unix' or 'tcp'")
    unix = network.get("unix", {})
    if "socket_path" in unix and unix["socket_path"] is not None and (
        not isinstance(unix["socket_path"], str) or not unix["socket_path"]
    ):
        raise ConfigurationError("network.unix.socket_path must be null or a nonempty path")
    tcp = network.get("tcp", {})
    if "host" in tcp:
        host = tcp["host"]
        if not isinstance(host, str) or not host:
            raise ConfigurationError("network.tcp.host must be a nonempty string")
        unwrapped = host[1:-1] if host.startswith("[") and host.endswith("]") else host
        if unwrapped != "localhost":
            try:
                address = ipaddress.ip_address(unwrapped)
            except ValueError as exc:
                raise ConfigurationError("network.tcp.host must be localhost or a loopback IP literal") from exc
            if not address.is_loopback:
                raise ConfigurationError("network.tcp.host must be localhost or a loopback IP literal")
    integer(tcp, "port", "network.tcp.port", minimum=1, maximum=65535)
    if "port" in tcp and tcp["port"] > 65535:
        raise ConfigurationError("network.tcp.port must be from 1 to 65535")
    for path, section, key in (
        ("pool.size", value.get("pool", {}), "size"),
        ("queue.size", value.get("queue", {}), "size"),
        ("session.max_files", value.get("session", {}), "max_files"),
        ("session.max_memory_bytes", value.get("session", {}), "max_memory_bytes"),
    ):
        integer(
            section, key, path, minimum=1,
            maximum=(1 << 31) - 1 if path in {"pool.size", "queue.size", "session.max_files"} else (1 << 63) - 1,
        )
    for side in ("server", "client"):
        section = value.get(side, {})
        for option, setting in section.get("grpc", {}).items():
            if setting is not None and (
                type(setting) is not int
                or setting > (1 << 31) - 1
                or (setting != -1 and setting <= 0)
            ):
                raise ConfigurationError(f"{side}.grpc.{option} must be null, -1, or a positive integer")
    integer(value.get("client", {}), "rpc_timeout_ms", "client.rpc_timeout_ms", minimum=1, nullable=True)
    integer(value.get("server", {}), "shutdown_grace_ms", "server.shutdown_grace_ms", minimum=0, nullable=True)


def _discovered_files(cwd: Path, home: Path, system_dir: Path) -> list[Path]:
    found: list[Path] = []
    for directory, names in (
        (system_dir, ("clang-toolkit.yaml",)),
        (home, ("clang-toolkit.yaml", ".clang-toolkit.yaml")),
        (cwd, ("clang-toolkit.yaml", ".clang-toolkit.yaml")),
    ):
        for name in names:
            path = directory / name
            if path.exists():
                if not path.is_file():
                    raise ConfigurationError(f"configuration path is not a file: {path}")
                found.append(path)
    return found


def load_network_config(
    config_path: str | os.PathLike[str] | None = None,
    *,
    cwd: Path | None = None,
    home: Path | None = None,
    system_dir: Path = Path("/etc/clang-toolkit"),
) -> NetworkConfig:
    """Load and validate layered config; explicit config is the highest layer."""
    cwd = Path(os.path.abspath(cwd or Path.cwd()))
    home = Path(os.path.abspath(home or Path.home()))
    config: dict[str, Any] = copy.deepcopy(_DEFAULTS)
    origins: dict[str, Path] = {}
    for path in _discovered_files(cwd, home, system_dir):
        _merge(config, _load_file(path), Path(os.path.abspath(path)), origins)
    if config_path is not None:
        explicit = Path(config_path)
        if not explicit.is_absolute():
            explicit = cwd / explicit
        if not explicit.exists():
            raise ConfigurationError(f"selected configuration file does not exist: {explicit}")
        if not explicit.is_file():
            raise ConfigurationError(f"selected configuration path is not a file: {explicit}")
        _merge(config, _load_file(explicit), Path(os.path.abspath(explicit)), origins)

    if type(config["version"]) is not int or config["version"] != 1:
        raise ConfigurationError("version must be integer 1")
    transport = config["network"]["transport"]
    if transport not in ("unix", "tcp"):
        raise ConfigurationError("network.transport must be 'unix' or 'tcp'")
    unix_path = config["network"]["unix"]["socket_path"]
    tcp = config["network"]["tcp"]
    if transport == "unix":
        if unix_path is not None and (not isinstance(unix_path, str) or not unix_path):
            raise ConfigurationError("network.unix.socket_path must be null or a nonempty path")
        if unix_path is None:
            resolved = Path(os.path.normpath(os.path.join(tempfile.gettempdir(), "ctk.sock")))
        else:
            resolved = Path(unix_path)
            if not resolved.is_absolute():
                source = origins.get("network.unix.socket_path")
                resolved = (source.parent if source else cwd) / resolved
            resolved = Path(os.path.normpath(os.path.abspath(resolved)))
        target = f"unix://{resolved}"
    else:
        host, port = tcp.get("host"), tcp.get("port")
        if not isinstance(host, str) or not host.strip():
            source = origins.get("network.transport", "<defaults>")
            raise ConfigurationError(f"{source}: network.tcp.host is required for TCP")
        if type(port) is not int or not 1 <= port <= 65535:
            source = origins.get("network.tcp.port", origins.get("network.transport", "<defaults>"))
            raise ConfigurationError(f"{source}: network.tcp.port must be an integer from 1 to 65535")
        host = host.strip()
        unwrapped = host[1:-1] if host.startswith("[") and host.endswith("]") else host
        if unwrapped != "localhost":
            try:
                address = ipaddress.ip_address(unwrapped)
            except ValueError as exc:
                raise ConfigurationError("TCP host must be localhost or a loopback IP literal") from exc
            if not address.is_loopback:
                raise ConfigurationError("network.tcp.host must be a loopback IP literal")
            normalized = str(address)
            host = f"[{normalized}]" if address.version == 6 else normalized
        target = f"{host}:{port}"

    def positive(mapping: dict[str, Any], key: str, dotted: str) -> int:
        value = mapping[key]
        if type(value) is not int or value <= 0:
            raise ConfigurationError(f"{dotted} must be a positive integer")
        return value

    pool_size = positive(config["pool"], "size", "pool.size")
    queue_size = positive(config["queue"], "size", "queue.size")
    max_files = positive(config["session"], "max_files", "session.max_files")
    max_memory = positive(config["session"], "max_memory_bytes", "session.max_memory_bytes")
    client_options: list[tuple[str, int]] = []
    for option, value in config["client"]["grpc"].items():
        if value is not None:
            if type(value) is not int or (value != -1 and value <= 0):
                raise ConfigurationError(f"client.grpc.{option} must be null, -1, or a positive integer")
            client_options.append((f"grpc.{option.removesuffix('_bytes')}_length", value))
    timeout_ms = config["client"]["rpc_timeout_ms"]
    if timeout_ms is not None and (type(timeout_ms) is not int or timeout_ms <= 0):
        raise ConfigurationError("client.rpc_timeout_ms must be a positive integer or null")
    for side in ("server", "client"):
        grpc_values = config[side]["grpc"]
        if not isinstance(grpc_values, dict):
            raise ConfigurationError(f"{side}.grpc must be a mapping")
        for option, value in grpc_values.items():
            if value is not None and (type(value) is not int or (value != -1 and value <= 0)):
                raise ConfigurationError(f"{side}.grpc.{option} must be null, -1, or a positive integer")
    grace = config["server"]["shutdown_grace_ms"]
    if grace is not None and (type(grace) is not int or grace < 0):
        raise ConfigurationError("server.shutdown_grace_ms must be a nonnegative integer or null")
    effective = _flatten(config)
    return NetworkConfig(
        target, transport, tuple(client_options),
        tuple((f"grpc.{key.removesuffix('_bytes')}_length", value) for key, value in config["server"]["grpc"].items() if value is not None),
        None if timeout_ms is None else timeout_ms / 1000,
        None if grace is None else grace / 1000,
        pool_size, queue_size, max_files, max_memory,
        MappingProxyType({key: str(origins.get(key, "<defaults>")) for key in effective}),
        MappingProxyType(effective),
    )


def _flatten(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, child in value.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            flattened.update(_flatten(child, dotted))
        else:
            flattened[dotted] = child
    return flattened
