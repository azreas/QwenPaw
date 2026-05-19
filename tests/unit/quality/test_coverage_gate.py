# -*- coding: utf-8 -*-
"""coverage gate 脚本的单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

# 将项目根目录加入 sys.path 以便导入 scripts 包
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.quality.coverage_gate import CoverageResult, parse_coverage_xml


def test_parse_coverage_xml_reads_line_rate(tmp_path: Path):
    xml = tmp_path / "coverage.xml"
    xml.write_text(
        '<coverage line-rate="0.8123"></coverage>', encoding="utf-8"
    )

    result = parse_coverage_xml(xml)

    assert result == CoverageResult(line_rate=81.23)


def test_parse_coverage_xml_rejects_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.xml"

    try:
        parse_coverage_xml(missing)
    except FileNotFoundError as exc:
        assert "missing.xml" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_main_returns_0_when_above_threshold(tmp_path: Path):
    from scripts.quality.coverage_gate import main

    xml = tmp_path / "coverage.xml"
    xml.write_text(
        '<coverage line-rate="0.85"></coverage>', encoding="utf-8"
    )

    rc = main(["--xml", str(xml), "--min", "80"])

    assert rc == 0


def test_main_returns_1_when_below_threshold(tmp_path: Path):
    from scripts.quality.coverage_gate import main

    xml = tmp_path / "coverage.xml"
    xml.write_text(
        '<coverage line-rate="0.45"></coverage>', encoding="utf-8"
    )

    rc = main(["--xml", str(xml), "--min", "80"])

    assert rc == 1
