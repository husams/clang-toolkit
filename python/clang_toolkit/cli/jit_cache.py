"""Local relocatable object artifacts for ctk-jit."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import time
from zipfile import BadZipFile, ZipFile

from .jit_dependencies import identity, observe, unchanged

_PREPROCESS = ("-E", "-x", "c++", "-")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True).encode("utf-8")


@dataclass(frozen=True)
class Toolchain:
    compiler: str
    flags: tuple[str, ...]
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
                        identity(Path(path))
                        for path in [config["compiler"], *config["libraries"]]
                    ],
                }
            )
        )
        return cls(config["compiler"], tuple(config["flags"]), fingerprint)

    def invoke(
        self, *args: str, source: bytes = b""
    ) -> subprocess.CompletedProcess[bytes]:
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
        return result

    def clang(self, *args: str, source: bytes = b"") -> bytes:
        return self.invoke(*args, source=source).stdout


def cache_directory() -> Path:
    if path := os.environ.get("CTK_JIT_CACHE_DIR"):
        return Path(path).resolve()
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "ctk-jit"


@contextmanager
def _lock(cache: Path, key: str) -> Iterator[None]:
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    status = cache.stat()
    if status.st_uid != os.getuid() or status.st_mode & 0o022:
        raise PermissionError(
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
    frozen = toolchain.clang(*quotes, *_PREPROCESS, source=source)
    return _precompile_snapshot(toolchain, frozen, cache)


def _object_key(toolchain: Toolchain, input_sha: str) -> str:
    return f"obj-{toolchain.fingerprint}-{input_sha}"


def _precompile_snapshot(
    toolchain: Toolchain, frozen: bytes, cache: Path | None
) -> bytes:
    input_sha = _sha(frozen)
    if cache is None:
        return _compile(toolchain, frozen, input_sha)

    key = _object_key(toolchain, input_sha)
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


def _cached_script_hit(index: Path, toolchain: Toolchain, cache: Path) -> bytes | None:
    try:
        record = json.loads(index.read_bytes())
        if not isinstance(record, dict):
            return None
        input_sha = record.get("input_sha256")
        if not isinstance(input_sha, str) or not re.fullmatch(
            "[0-9a-f]{64}", input_sha
        ):
            return None
        if not unchanged(record.get("observations")):
            return None
        data = (cache / (_object_key(toolchain, input_sha) + ".bundle")).read_bytes()
        bundle_object(data, toolchain, input_sha)
        return data
    except (OSError, ValueError):
        return None


def cached_script_bundle(
    toolchain: Toolchain,
    cache: Path,
    script: Path,
    contents: bytes,
    frontend_files: Sequence[Path],
    frontend_versions: tuple[str, ...],
    lower: Callable[[], bytes],
) -> bytes:
    # The driver dry-run captures implicit toolchain/search-path choices without
    # entering Clang's preprocessor. Virtual or modular inputs use the slow path.
    plan = toolchain.invoke(*_PREPROCESS, "-###").stderr
    if b'"-cc1"' not in plan or any(
        option in plan
        for option in (b'"-ivfsoverlay"', b'"-vfsoverlay"', b'"-fmodules"')
    ):
        return precompile(toolchain, lower(), "", cache)
    key = "script-" + _sha(
        _json(
            {
                "version": 1,
                "script": str(script),
                "contents": _sha(contents),
                "frontend": [_file_sha(path) for path in frontend_files],
                "versions": frontend_versions,
                "toolchain": toolchain.fingerprint,
                "plan": _sha(plan),
            }
        )
    )
    index = cache / (key + ".json")
    with _lock(cache, key):
        if data := _cached_script_hit(index, toolchain, cache):
            return data
        source = lower()
        with TemporaryDirectory() as directory:
            depfile = Path(directory) / "deps"
            started = time.time_ns()
            result = toolchain.invoke(
                *_PREPROCESS,
                "-MD",
                "-MF",
                str(depfile),
                "-MT",
                "ctk-jit",
                "-v",
                "-Wdate-time",
                source=source,
            )
            try:
                observations = observe(
                    os.fsdecode(depfile.read_bytes()),
                    os.fsdecode(result.stderr),
                    started,
                )
            except OSError:
                observations = None
        data = _precompile_snapshot(toolchain, result.stdout, cache)
        if observations is not None:
            write_atomic(
                index,
                _json(
                    {
                        "input_sha256": _sha(result.stdout),
                        "observations": observations,
                    }
                ),
            )
        return data
