"""Immutable editor snapshots supplied through Clang's virtual filesystem."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory


class EditorBuffers:
    def __init__(self, contents: dict[str, str]) -> None:
        self.contents = {str(Path(file).resolve()): text for file, text in contents.items()}
        self.directory = TemporaryDirectory(prefix='ctk-editor-') if contents else None
        self.arguments: list[str] = []
        if self.directory is not None:
            directory = Path(self.directory.name)
            roots = []
            for index, (file, text) in enumerate(self.contents.items()):
                snapshot = directory / f'buffer-{index}'
                snapshot.write_bytes(text.encode('utf-8'))
                roots.append({'type': 'file', 'name': file, 'external-contents': str(snapshot)})
            overlay = directory / 'overlay.json'
            overlay.write_text(json.dumps({'version': 0, 'use-external-names': False,
                                           'roots': roots}), encoding='utf-8')
            self.arguments = [f'-ivfsoverlay{overlay}']

    def fingerprint(self, file: str) -> str:
        text = self.contents.get(file)
        data = text.encode('utf-8') if text is not None else Path(file).read_bytes()
        return hashlib.sha256(data).hexdigest()

    def read_bytes(self, file: str) -> bytes:
        text = self.contents.get(file)
        return text.encode('utf-8') if text is not None else Path(file).read_bytes()

    def close(self) -> None:
        if self.directory is not None:
            self.directory.cleanup()
