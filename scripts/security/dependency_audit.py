# -*- coding: utf-8 -*-
"""统一执行和解析 pip-audit 安全扫描结果。"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditFinding:
    package: str
    version: str
    vulnerability_id: str
    aliases: tuple[str, ...] = ()
    fix_versions: tuple[str, ...] = ()


def parse_pip_audit_json(payload: dict[str, Any]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for dep in payload.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            findings.append(
                AuditFinding(
                    package=dep.get("name", ""),
                    version=dep.get("version", ""),
                    vulnerability_id=vuln.get("id", ""),
                    aliases=tuple(vuln.get("aliases", []) or []),
                    fix_versions=tuple(vuln.get("fix_versions", []) or []),
                )
            )
    return findings


def has_blocking_findings(findings: list[AuditFinding]) -> bool:
    return bool(findings)


def _parse_ignore_ids(ignore_file: Path) -> list[str]:
    """从 ignore 文件中提取漏洞 ID（每行格式: ID # 理由）。"""
    ids: list[str] = []
    for line in ignore_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # 取 # 前面的部分
        vuln_id = stripped.split("#", 1)[0].strip()
        if vuln_id:
            ids.append(vuln_id)
    return ids


def run_pip_audit(
    output: Path, project_root: Path, ignore_file: Path | None = None
) -> tuple[int, str]:
    """运行 pip-audit，返回 (exit_code, stderr)。

    使用 ``--local`` 限制扫描范围到虚拟环境本地安装的包，
    避免全局安装的无关包（如 uv）污染审计结果。
    """
    cmd = [
        sys.executable,
        "-m",
        "pip_audit",
        "--format",
        "json",
        "--local",
        str(project_root),
    ]
    if ignore_file and ignore_file.exists():
        for vuln_id in _parse_ignore_ids(ignore_file):
            cmd.extend(["--ignore-vuln", vuln_id])
    result = subprocess.run(
        cmd,
        check=False,
        text=True,
        capture_output=True,
    )
    output.write_text(result.stdout or "{}", encoding="utf-8")
    return result.returncode, (result.stderr or "").strip()


def _default_ignore_file() -> str:
    return str(Path(__file__).resolve().parent / "pip-audit-ignores.toml")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pip-output", default=".tmp/pip-audit.json")
    parser.add_argument(
        "--project-root",
        default=".",
        help="项目根目录，pip-audit 基于此路径审计依赖",
    )
    parser.add_argument(
        "--ignore-file",
        default=_default_ignore_file(),
        help="pip-audit 忽略规则文件路径",
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    output = Path(args.pip_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    ignore_file = Path(args.ignore_file) if args.ignore_file else None
    exit_code, stderr = run_pip_audit(
        output, project_root=project_root, ignore_file=ignore_file
    )
    if output.exists():
        payload = json.loads(output.read_text(encoding="utf-8") or "{}")
    else:
        payload = {}
    findings = parse_pip_audit_json(payload)
    if findings:
        for finding in findings:
            print(
                f"{finding.package} {finding.version}: "
                f"{finding.vulnerability_id} fixes={','.join(finding.fix_versions)}"
            )
    # pip-audit 执行失败（exit_code != 0）但无可解析漏洞时，说明扫描器本身
    # 出了问题（如未安装、网络错误），必须返回失败而非误判为通过
    if exit_code != 0 and not findings:
        if stderr:
            print(f"pip-audit error: {stderr}", file=sys.stderr)
        else:
            print("pip-audit exited with error but produced no findings", file=sys.stderr)
        return 1
    return 1 if has_blocking_findings(findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
