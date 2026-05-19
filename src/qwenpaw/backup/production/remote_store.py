from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol


class RemoteStore(Protocol):
    def put(self, source: Path, key: str) -> Path: ...
    def get(self, key: str, dest: Path) -> Path: ...


class FilesystemRemoteStore:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _resolve(self, key: str) -> Path:
        target = (self._root / key).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError("remote key escapes root")
        return target

    def put(self, source: Path, key: str) -> Path:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target

    def get(self, key: str, dest: Path) -> Path:
        source = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        return dest
