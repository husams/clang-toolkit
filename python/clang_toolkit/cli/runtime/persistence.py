"""Versioned variable exchange in YAML, JSON, and flat typed CSV."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .filesystem import Directory, File, FileSystemEntry
from .values import MatchSet, MatcherExpr, QualifiedName


class PersistenceError(ValueError):
    """A value cannot be saved or an external file cannot be loaded safely."""


_SUFFIXES = {"yaml": ".yaml", "json": ".json", "csv": ".csv"}
_TYPES = {"str", "bool", "int", "float"}


def _encode(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int):
        return {"type": "int", "value": value}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, FileSystemEntry):
        return {
            "type": "directory" if isinstance(value, Directory) else "file",
            "value": {
                "path": value.path,
                "absolute": value.absolute,
                "size": value.size,
                "modified": value.modified.isoformat(),
            },
        }
    if isinstance(value, list):
        return {"type": "list", "value": [_encode(item) for item in value]}
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {
            "type": "record",
            "value": {key: _encode(item) for key, item in value.items()},
        }
    if isinstance(value, MatcherExpr):
        return {
            "type": "matcher",
            "value": {
                "name": value.name,
                "arguments": [_encode(arg) for arg in value.arguments],
                "binding": value.binding,
            },
        }
    if isinstance(value, QualifiedName):
        return {"type": "qualified_name", "value": value.text}
    if isinstance(value, MatchSet):
        return {"type": "match_snapshot", "value": [_encode(row) for row in value.rows]}
    raise PersistenceError(f"cannot save value of type {type(value).__name__}")


def _decode(envelope: Any) -> Any:
    if not isinstance(envelope, dict) or set(envelope) != {"type", "value"}:
        raise PersistenceError("invalid typed value envelope")
    kind, value = envelope["type"], envelope["value"]
    if kind == "null" and value is None:
        return None
    if kind == "bool" and type(value) is bool:
        return value
    if kind == "int" and type(value) is int:
        return value
    if kind == "float" and type(value) in {int, float}:
        return float(value)
    if kind == "str" and isinstance(value, str):
        return value
    if kind in {"file", "directory"} and isinstance(value, dict):
        if (
            set(value) == {"path", "absolute", "size", "modified"}
            and isinstance(value["path"], str)
            and isinstance(value["absolute"], str)
            and type(value["size"]) is int
            and isinstance(value["modified"], str)
        ):
            try:
                modified = datetime.fromisoformat(value["modified"])
            except ValueError as exc:
                raise PersistenceError("invalid file modification time") from exc
            if Path(value["absolute"]).is_absolute() and modified.tzinfo is not None:
                entry_type = File if kind == "file" else Directory
                return entry_type(
                    value["path"], value["absolute"], value["size"], modified
                )
    if kind == "list" and isinstance(value, list):
        return [_decode(item) for item in value]
    if (
        kind == "record"
        and isinstance(value, dict)
        and all(isinstance(key, str) for key in value)
    ):
        return {key: _decode(item) for key, item in value.items()}
    if kind == "qualified_name" and isinstance(value, str):
        return QualifiedName(value)
    if kind == "matcher" and isinstance(value, dict):
        name = value.get("name")
        args = value.get("arguments")
        binding = value.get("binding")
        if (
            isinstance(name, str)
            and isinstance(args, list)
            and (binding is None or isinstance(binding, str))
        ):
            return MatcherExpr(name, tuple(_decode(item) for item in args), binding)
    if kind == "match_snapshot" and isinstance(value, list):
        return MatchSet(tuple(_decode(item) for item in value))
    raise PersistenceError(f"invalid or unsupported typed value: {kind}")


def _scalar_kind(value: Any) -> str:
    if type(value) is bool:
        return "bool"
    if type(value) is int:
        return "int"
    if type(value) is float:
        return "float"
    if type(value) is str:
        return "str"
    raise PersistenceError(
        "CSV supports only flat lists of primitive values or records"
    )


def _csv_rows(value: Any) -> tuple[list[str], list[list[str]]]:
    if not isinstance(value, list):
        raise PersistenceError("CSV requires a list")
    if not value:
        return ["value:str"], []
    if all(isinstance(item, dict) for item in value):
        keys = list(value[0])
        if not keys or any(set(row) != set(keys) for row in value):
            raise PersistenceError("CSV records must have the same nonempty fields")
        kinds = {key: _scalar_kind(value[0][key]) for key in keys}
        if any(_scalar_kind(row[key]) != kinds[key] for row in value for key in keys):
            raise PersistenceError("CSV column types must be consistent")
        return [f"{key}:{kinds[key]}" for key in keys], [
            [
                str(row[key]).lower() if kinds[key] == "bool" else str(row[key])
                for key in keys
            ]
            for row in value
        ]
    kind = _scalar_kind(value[0])
    if any(_scalar_kind(item) != kind for item in value):
        raise PersistenceError("CSV scalar list must have one type")
    return [f"value:{kind}"], [
        [str(item).lower() if kind == "bool" else str(item)] for item in value
    ]


def _csv_load(path: Path) -> list[Any]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise PersistenceError("CSV is missing a header")
        names: list[str] = []
        kinds: list[str] = []
        for header in reader.fieldnames:
            if ":" in header and header.rsplit(":", 1)[1] in _TYPES:
                name, kind = header.rsplit(":", 1)
            else:
                name, kind = header, "str"
            if not name or name in names:
                raise PersistenceError("CSV has duplicate or empty columns")
            names.append(name)
            kinds.append(kind)

        def decode_cell(raw: str, kind: str) -> Any:
            if kind == "str":
                return raw
            if kind == "bool":
                if raw not in {"true", "false"}:
                    raise PersistenceError("CSV boolean must be true or false")
                return raw == "true"
            try:
                return int(raw) if kind == "int" else float(raw)
            except ValueError as exc:
                raise PersistenceError(f"invalid CSV {kind} value: {raw}") from exc

        rows: list[Any] = []
        for row in reader:
            if None in row or any(
                row.get(header) is None for header in reader.fieldnames
            ):
                raise PersistenceError("CSV row has wrong number of fields")
            record = {
                name: decode_cell(row[header], kind)
                for header, name, kind in zip(reader.fieldnames, names, kinds)
            }
            rows.append(record["value"] if names == ["value"] else record)
        return rows


def _format_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    for kind, extension in _SUFFIXES.items():
        if suffix == extension:
            return kind
    raise PersistenceError(f"unsupported file extension: {suffix}")


def _save_path(path: Path, format_name: str | None) -> tuple[Path, str]:
    if format_name is not None and format_name not in _SUFFIXES:
        raise PersistenceError(f"unsupported format: {format_name}")
    kind = format_name or (_format_from_path(path) if path.suffix else "yaml")
    if not path.suffix:
        path = path.with_suffix(_SUFFIXES[kind])
    elif _format_from_path(path) != kind:
        raise PersistenceError("file extension and requested format disagree")
    return path, kind


def save(value: Any, path: Path, *, format_name: str | None = None) -> Path:
    path, kind = _save_path(path, format_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temp_name = handle.name
            if kind == "csv":
                headers, rows = _csv_rows(value)
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerows(rows)
            else:
                document = {"schema_version": 1, **_encode(value)}
                if kind == "json":
                    json.dump(document, handle, ensure_ascii=False, indent=2)
                else:
                    yaml.safe_dump(
                        document, handle, allow_unicode=True, sort_keys=False
                    )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except (OSError, yaml.YAMLError, TypeError) as exc:
        raise PersistenceError(f"cannot save {path}: {exc}") from exc
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return path


def load(path: Path) -> Any:
    if not path.suffix:
        candidates = [
            path.with_suffix(extension)
            for extension in (".yaml", ".yml", ".json", ".csv")
        ]
        existing = [candidate for candidate in candidates if candidate.exists()]
        if len(existing) != 1:
            raise PersistenceError("extensionless load needs exactly one matching file")
        path = existing[0]
    kind = _format_from_path(path)
    try:
        if kind == "csv":
            return _csv_load(path)
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle) if kind == "json" else yaml.safe_load(handle)
    except (OSError, ValueError, yaml.YAMLError, csv.Error) as exc:
        raise PersistenceError(f"cannot load {path}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise PersistenceError("unsupported or missing schema_version")
    return _decode(
        {key: value for key, value in document.items() if key != "schema_version"}
    )
