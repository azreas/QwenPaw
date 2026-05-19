from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from pydantic import BaseModel


class RestoreDrillResult(BaseModel):
    ok: bool
    extracted_files: int
    sandbox_dir: str
    error: str = ""


def _safe_member_path(root: Path, member_name: str) -> Path:
    target = (root / member_name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"unsafe backup member: {member_name}")
    return target


def run_restore_drill(backup_zip: Path, sandbox_dir: Path) -> RestoreDrillResult:
    # 仅允许清理 _restore_drills 下的演练目录，防止误删
    if sandbox_dir.exists():
        if sandbox_dir.name and "_restore_drills" in sandbox_dir.parts:
            shutil.rmtree(sandbox_dir)
        else:
            return RestoreDrillResult(
                ok=False,
                extracted_files=0,
                sandbox_dir=str(sandbox_dir),
                error="refusing to delete non-drill directory",
            )
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(backup_zip) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            try:
                target = _safe_member_path(sandbox_dir, member.filename)
            except ValueError as exc:
                return RestoreDrillResult(
                    ok=False,
                    extracted_files=count,
                    sandbox_dir=str(sandbox_dir),
                    error=str(exc),
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            count += 1
    return RestoreDrillResult(
        ok=True,
        extracted_files=count,
        sandbox_dir=str(sandbox_dir),
    )
