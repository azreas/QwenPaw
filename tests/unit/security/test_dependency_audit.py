# -*- coding: utf-8 -*-
"""dependency_audit 脚本的单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

# 将项目根目录加入 sys.path 以便导入 scripts 包
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.security.dependency_audit import (
    AuditFinding,
    _parse_ignore_ids,
    has_blocking_findings,
    parse_pip_audit_json,
)


def test_parse_pip_audit_json_extracts_aliases():
    payload = {
        "dependencies": [
            {
                "name": "demo",
                "version": "1.0",
                "vulns": [
                    {
                        "id": "PYSEC-1",
                        "fix_versions": ["1.1"],
                        "aliases": ["CVE-2026-0001"],
                    }
                ],
            }
        ]
    }

    findings = parse_pip_audit_json(payload)

    assert findings == [
        AuditFinding(
            package="demo",
            version="1.0",
            vulnerability_id="PYSEC-1",
            aliases=("CVE-2026-0001",),
            fix_versions=("1.1",),
        )
    ]


def test_has_blocking_findings_blocks_any_vulnerability():
    assert has_blocking_findings([AuditFinding("demo", "1.0", "PYSEC-1")])
    assert not has_blocking_findings([])


def test_main_returns_1_when_pip_audit_fails_without_findings(tmp_path: Path):
    """pip-audit 执行失败且无漏洞时，必须返回 1 而非误判为通过。"""
    from unittest.mock import patch

    from scripts.security.dependency_audit import main

    output = tmp_path / "audit.json"
    ignore = tmp_path / "ignores.toml"

    # 模拟 pip-audit 不存在或执行失败：exit_code=1，stdout 为空
    with patch("scripts.security.dependency_audit.run_pip_audit", return_value=(1, "No module named pip_audit")):
        rc = main(["--pip-output", str(output), "--project-root", str(tmp_path), "--ignore-file", str(ignore)])

    assert rc == 1


def test_main_returns_0_when_pip_audit_succeeds_and_clean(tmp_path: Path):
    """pip-audit 正常运行且无漏洞时返回 0。"""
    from unittest.mock import patch

    from scripts.security.dependency_audit import main

    output = tmp_path / "audit.json"
    ignore = tmp_path / "ignores.toml"

    def _fake_run(out: Path, project_root=None, ignore_file=None):
        out.write_text("{}", encoding="utf-8")
        return 0, ""

    with patch("scripts.security.dependency_audit.run_pip_audit", side_effect=_fake_run):
        rc = main(["--pip-output", str(output), "--project-root", str(tmp_path), "--ignore-file", str(ignore)])

    assert rc == 0


def test_parse_ignore_ids_extracts_vulnerability_ids(tmp_path: Path):
    """从 ignore 文件中提取漏洞 ID，跳过注释和空行。"""
    ignore = tmp_path / "ignores.toml"
    ignore.write_text(
        "# header comment\n"
        "CVE-2024-0001  # some reason\n"
        "\n"
        "PYSEC-2025-49\n"
        "# another comment\n",
        encoding="utf-8",
    )

    ids = _parse_ignore_ids(ignore)

    assert ids == ["CVE-2024-0001", "PYSEC-2025-49"]
