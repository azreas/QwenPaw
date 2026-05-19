# -*- coding: utf-8 -*-
"""覆盖率门禁脚本——读取 coverage XML 并检查 line-rate 是否达到阈值。"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoverageResult:
    line_rate: float


def parse_coverage_xml(path: Path) -> CoverageResult:
    """解析 coverage XML 并返回百分比形式的 line-rate。"""
    if not path.is_file():
        raise FileNotFoundError(str(path))
    root = ET.parse(path).getroot()
    line_rate = float(root.attrib["line-rate"]) * 100
    return CoverageResult(line_rate=round(line_rate, 2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="检查覆盖率是否达到阈值"
    )
    parser.add_argument("--xml", default="coverage.xml")
    parser.add_argument("--min", type=float, default=80.0)
    args = parser.parse_args(argv)

    result = parse_coverage_xml(Path(args.xml))
    if result.line_rate < args.min:
        print(f"coverage {result.line_rate:.2f}% is below {args.min:.2f}%")
        return 1
    print(f"coverage {result.line_rate:.2f}% meets {args.min:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
