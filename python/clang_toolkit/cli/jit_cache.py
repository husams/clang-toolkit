"""Local Clang prelude and relocatable object artifacts for ctk-jit."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

_INCREMENTAL = ("-Xclang", "-fincremental-extensions")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True).encode("utf-8")


def _identity(path: Path) -> tuple[int, ...]:
    status = path.stat()
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


@dataclass(frozen=True)
class Toolchain:
    compiler: str
    flags: tuple[str, ...]
    prelude: str | None
    fingerprint: str

    @classmethod
    def from_runner(cls, runner: Path) -> Toolchain:
        config = json.loads(subprocess.check_output([str(runner), "config"]))
        fingerprint = _sha(
            _json(
                {
                    "config": config,
                    "runner": _file_sha(runner),
                    "header": _file_sha(Path(config["runtime_header"])),
                    "toolchain": [
                        _identity(Path(path))
                        for path in [config["compiler"], *config["libraries"]]
                    ],
                }
            )
        )
        return cls(
            config["compiler"], tuple(config["flags"]), config["prelude"], fingerprint
        )

    def clang(self, *args: str, source: bytes = b"") -> bytes:
        result = subprocess.run(
            [self.compiler, *self.flags, *args],
            input=source,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
            raise ValueError(
                diagnostic or f"Clang exited with status {result.returncode}"
            )
        return result.stdout


def cache_directory() -> Path:
    if path := os.environ.get("CTK_JIT_CACHE_DIR"):
        return Path(path).resolve()
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "ctk-jit"


@contextmanager
def _lock(cache: Path, key: str) -> Iterator[None]:
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    status = cache.stat()
    if status.st_uid != os.getuid() or status.st_mode & 0o022:
        raise ValueError(
            "ctk-jit cache must be owned by the current user and privately writable"
        )
    with (cache / (key + ".lock")).open("ab") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def write_atomic(path: Path, content: bytes) -> None:
    with TemporaryDirectory(dir=path.parent) as directory:
        temporary = Path(directory) / "artifact"
        temporary.write_bytes(content)
        temporary.replace(path)


def cached_prelude(toolchain: Toolchain, cache: Path) -> Path | None:
    if toolchain.prelude is None:
        return None
    # Preprocessing observes include selection and changes to the prelude inputs.
    scan = (*_INCREMENTAL, "-E", "-dD", "-x", "c++-header", toolchain.prelude)
    input_sha = _sha(toolchain.clang(*scan))
    key = f"pch-{toolchain.fingerprint}-{input_sha}"
    path = cache / (key + ".pch")
    checksum = path.with_suffix(".sha256")
    with _lock(cache, key):
        try:
            if checksum.read_text(encoding="ascii") == _file_sha(path):
                toolchain.clang(
                    *_INCREMENTAL,
                    "-include-pch",
                    str(path),
                    "-fsyntax-only",
                    "-x",
                    "c++",
                    "-",
                )
                return path
        except (OSError, ValueError):
            pass  # Missing, corrupted or rejected PCH.

        with TemporaryDirectory(dir=cache) as directory:
            built = Path(directory) / "prelude.pch"
            toolchain.clang(
                *_INCREMENTAL, "-x", "c++-header", toolchain.prelude, "-o", str(built)
            )
            if _sha(toolchain.clang(*scan)) != input_sha:
                raise ValueError("prelude headers changed during compilation")
            digest = _file_sha(built)
            built.replace(path)
            write_atomic(checksum, digest.encode("ascii"))
    return path


def bundle_object(
    data: bytes, toolchain: Toolchain, input_sha: str | None = None
) -> bytes:
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            if not isinstance(manifest, dict) or manifest.get("version") != 1:
                raise ValueError("unsupported bundle version")
            if manifest.get("toolchain") != toolchain.fingerprint:
                raise ValueError("bundle was built for a different ctk-jit toolchain")
            if input_sha is not None and manifest.get("input_sha256") != input_sha:
                raise ValueError("bundle does not match its cache key")
            obj = archive.read("program.o")
            if manifest.get("object_sha256") != _sha(obj):
                raise ValueError("bundle object checksum mismatch")
            return obj
    except (BadZipFile, KeyError, RuntimeError, NotImplementedError) as error:
        raise ValueError(f"invalid ctk-jit bundle: {error}") from error


def _compile(toolchain: Toolchain, source: bytes, input_sha: str) -> bytes:
    with TemporaryDirectory() as directory:
        path = Path(directory) / "program.o"
        toolchain.clang(
            "-x", "c++-cpp-output", "-c", "-", "-o", str(path), source=source
        )
        obj = path.read_bytes()
    output = io.BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(
            "manifest.json",
            _json(
                {
                    "version": 1,
                    "toolchain": toolchain.fingerprint,
                    "input_sha256": input_sha,
                    "object_sha256": _sha(obj),
                }
            ),
        )
        archive.writestr("program.o", obj)
    return output.getvalue()


def precompile(
    toolchain: Toolchain, source: bytes, quote_dir: str, cache: Path | None
) -> bytes:
    # Compile the exact preprocessed snapshot used in the key. This also catches
    # newly introduced headers that shadow a previously resolved include.
    quotes = ("-iquote", quote_dir) if quote_dir else ()
    frozen = toolchain.clang(*quotes, "-E", "-x", "c++", "-", source=source)
    input_sha = _sha(frozen)
    if cache is None:
        return _compile(toolchain, frozen, input_sha)

    key = f"obj-{toolchain.fingerprint}-{input_sha}"
    path = cache / (key + ".bundle")
    with _lock(cache, key):
        try:
            data = path.read_bytes()
            bundle_object(data, toolchain, input_sha)
            return data
        except (FileNotFoundError, ValueError):
            pass
        data = _compile(toolchain, frozen, input_sha)
        write_atomic(path, data)
        return data
