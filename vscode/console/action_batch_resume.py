"""Restore a validated successful prefix from a saved workspace-action checkpoint."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
from typing import Any


@dataclass(frozen=True)
class ResumedBatch:
    statuses: tuple[dict[str, Any], ...] = ()
    matches: int = 0
    result_bytes: int = 0


class ResumeError(ValueError):
    """A saved checkpoint cannot safely be resumed against current inputs."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open('rb') as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise ResumeError(f'Cannot read checkpoint dependency {path}: {error}') from error
    return digest.hexdigest()


def _copy_file(source: Path, destination: Path) -> None:
    """Prefer a hard link for large immutable exports, copying across devices."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copyfile(source, destination)


def _copy_prefix(source: Path, destination: Path, length: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as input_file, destination.open('wb') as output_file:
        remaining = length
        while remaining:
            chunk = input_file.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ResumeError('Checkpoint archive ended before the indexed prefix')
            output_file.write(chunk)
            remaining -= len(chunk)


def _archive_file(value: Any, base: Path, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ResumeError(f'Checkpoint {label} path is missing')
    path = Path(value)
    return path if path.is_absolute() else base / path


def restore_completed_batch(
    request: dict[str, Any],
    action: dict[str, Any],
    files: list[str],
    settings: dict[str, Any],
    directory: Path,
    result_file: Path,
    offsets_file: Path,
) -> ResumedBatch:
    """Restore a valid contiguous succeeded prefix into a fresh result directory."""
    manifest_path_value = request.get('resumeManifest')
    if not manifest_path_value:
        return ResumedBatch()
    if not isinstance(manifest_path_value, str):
        raise ResumeError('Checkpoint manifest must be a file path')
    manifest_path = Path(manifest_path_value)
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise ResumeError(f'Cannot read checkpoint manifest: {error}') from error
    if not isinstance(manifest, dict) or manifest.get('version') != 1:
        raise ResumeError('Unsupported checkpoint manifest version')

    expected_values = request.get('values', {})
    expected_profiles = request.get('profiles', {})
    checks = (
        ('files', files),
        ('settings', settings),
        ('values', expected_values),
        ('profiles', expected_profiles),
        ('actionRevision', action.get('revision')),
        ('actionGeneratedSha256', hashlib.sha256(
            str(action.get('generated', '')).encode('utf-8')).hexdigest()),
    )
    for key, expected in checks:
        if manifest.get(key) != expected:
            raise ResumeError(f'Checkpoint {key} does not match this run')

    report = manifest.get('report')
    if not isinstance(report, dict):
        raise ResumeError('Checkpoint report is missing')
    if (report.get('stale') or report.get('sourceValidationFailed')
            or report.get('sourceValidationError') or report.get('sourceChangedFiles')):
        raise ResumeError('Checkpoint report failed source validation')

    source_hashes = manifest.get('sourceSha256')
    if not isinstance(source_hashes, dict) or set(source_hashes) != set(files):
        raise ResumeError('Checkpoint source hashes do not cover the requested files')
    for file in files:
        if _sha256(Path(file)) != source_hashes[file]:
            raise ResumeError(f'Checkpoint source changed: {file}')

    dependency_hashes = manifest.get('dependencySha256')
    if not isinstance(dependency_hashes, dict):
        raise ResumeError('Checkpoint dependency hashes are missing')
    for dependency, expected_hash in dependency_hashes.items():
        if not isinstance(dependency, str) or not isinstance(expected_hash, str):
            raise ResumeError('Checkpoint dependency hash entry is invalid')
        if _sha256(Path(dependency)) != expected_hash:
            raise ResumeError(f'Checkpoint dependency changed: {dependency}')

    file_statuses = report.get('fileStatuses')
    if not isinstance(file_statuses, list) or [
        status.get('file') if isinstance(status, dict) else None
        for status in file_statuses
    ] != files:
        raise ResumeError('Checkpoint report file order does not match this run')

    prefix: list[dict[str, Any]] = []
    for status in file_statuses:
        if status.get('status') != 'succeeded':
            break
        prefix.append(status)
    matches = sum(int(status.get('totalMatches', status.get('matches', 0)))
                  for status in prefix)
    old_total = int(report.get('totalMatches', report.get('matches', -1)))
    if old_total < 0 or matches > old_total:
        raise ResumeError('Checkpoint report has an invalid match count')

    base = manifest_path.parent
    archive_directory = _archive_file(manifest.get('archive'), base, 'archive')
    report_result_path = _archive_file(report.get('resultFile'), base, 'report result')
    old_archive = archive_directory / report_result_path.name
    if not old_archive.is_file():
        raise ResumeError('Checkpoint aggregate archive is missing')
    old_offsets = archive_directory / 'all-results.offsets'
    if not old_offsets.is_file():
        raise ResumeError('Checkpoint match offset index is missing')

    record_size = struct.calcsize('!QQ')
    if old_offsets.stat().st_size != old_total * record_size:
        raise ResumeError('Checkpoint offset index does not match the report')
    if matches < old_total:
        with old_offsets.open('rb') as index_file:
            index_file.seek(matches * record_size)
            record = index_file.read(record_size)
        if len(record) != record_size:
            raise ResumeError('Checkpoint prefix boundary is missing from the offset index')
        physical, logical = struct.unpack('!QQ', record)
        if logical != 0 or physical > old_archive.stat().st_size:
            raise ResumeError('Checkpoint prefix ends inside a gzip member')
        _copy_prefix(old_archive, result_file, physical)
    else:
        # The aggregate is appendable by the live run, so never share its inode
        # with the immutable checkpoint archive.
        _copy_prefix(old_archive, result_file, old_archive.stat().st_size)
    with old_offsets.open('rb') as source_index, offsets_file.open('wb') as target_index:
        remaining = matches * record_size
        while remaining:
            chunk = source_index.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ResumeError('Checkpoint offset index ended before the prefix')
            target_index.write(chunk)
            remaining -= len(chunk)

    restored: list[dict[str, Any]] = []
    result_bytes = 0
    for index, status in enumerate(prefix, start=1):
        source_export = _archive_file(status.get('fullResultPath'), base, 'per-file result')
        export = archive_directory / source_export.name
        if not export.is_file():
            raise ResumeError(f'Checkpoint per-file result is missing: {export}')
        destination = directory / f'file-{index:04d}.jsonl.gz'
        _copy_file(export, destination)
        resumed_status = {
            key: value for key, value in status.items() if value is not None
        }
        resumed_status.update(fullResultPath=str(destination),
                              attempted=True, resumed=True)
        restored.append(resumed_status)
        result_bytes += int(status.get('resultBytes', 0))

    return ResumedBatch(tuple(restored), matches, result_bytes)
