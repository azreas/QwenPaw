import zipfile
from pathlib import Path

from qwenpaw.backup.production.drill import run_restore_drill


def test_restore_drill_extracts_to_sandbox(tmp_path: Path):
    backup = tmp_path / "backup.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("config.json", "{}")

    sandbox = tmp_path / "_restore_drills" / "test1"
    result = run_restore_drill(backup, sandbox)

    assert result.ok
    assert (sandbox / "config.json").is_file()


def test_restore_drill_rejects_zip_slip(tmp_path: Path):
    backup = tmp_path / "backup.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("../escape.txt", "bad")

    sandbox = tmp_path / "_restore_drills" / "test2"
    result = run_restore_drill(backup, sandbox)

    assert not result.ok
    assert not (tmp_path / "escape.txt").exists()


def test_restore_drill_skips_directories(tmp_path: Path):
    backup = tmp_path / "backup.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("subdir/file.txt", "hello")

    sandbox = tmp_path / "_restore_drills" / "test3"
    result = run_restore_drill(backup, sandbox)

    assert result.ok
    assert result.extracted_files == 1
    assert (sandbox / "subdir" / "file.txt").is_file()


def test_restore_drill_refuses_non_drill_directory(tmp_path: Path):
    backup = tmp_path / "backup.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr("test.txt", "hello")

    # 非 _restore_drills 下的目录，已存在时拒绝 rmtree
    dangerous_dir = tmp_path / "important_data"
    dangerous_dir.mkdir()
    (dangerous_dir / "keep.txt").write_text("do not delete")

    result = run_restore_drill(backup, dangerous_dir)

    assert not result.ok
    assert "non-drill" in result.error
    # 原有文件未被删除
    assert (dangerous_dir / "keep.txt").is_file()
