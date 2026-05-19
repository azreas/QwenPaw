#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地后端调试启动脚本。

用途：
- 支持 IDE / 调试器直接启动后端
- 支持部署前的预检查与干跑
- 自动准备工作目录、密钥目录、临时目录与控制台静态资源路径

示例：
  python scripts/start_backend_debug.py
  python scripts/start_backend_debug.py --host 0.0.0.0 --port 8088
  python scripts/start_backend_debug.py --reload --log-level debug
  python scripts/start_backend_debug.py --dry-run
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from _start_backend_common import prepare_runtime


def _load_dotenv(repo_root: Path) -> None:
    """加载仓库根目录 .env 文件中的环境变量（不覆盖已设变量）。"""
    env_file = repo_root / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        eq = stripped.find("=")
        if eq <= 0:
            continue
        key = stripped[:eq].strip()
        value = stripped[eq + 1:].strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value
    print(f"[backend-debug] 已加载 {env_file}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="启动 QwenPaw 后端调试服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8088, help="监听端口")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载（开发模式）",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="日志级别",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印解析后的启动配置，不真正启动服务",
    )
    parser.add_argument(
        "--working-dir",
        default="",
        help="覆盖 QWENPAW_WORKING_DIR（相对路径按仓库根目录解析）",
    )
    parser.add_argument(
        "--secret-dir",
        default="",
        help="覆盖 QWENPAW_SECRET_DIR（相对路径按仓库根目录解析）",
    )
    parser.add_argument(
        "--console-static-dir",
        default="",
        help="显式指定控制台静态资源目录",
    )
    parser.add_argument(
        "--allow-missing-console",
        action="store_true",
        help="允许在缺少控制台静态资源时继续启动后端",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    # 在准备运行环境之前加载 .env（不覆盖已设环境变量）
    repo_root_path = Path(__file__).resolve().parent.parent
    _load_dotenv(repo_root_path)

    repo_root, working_dir, secret_dir, tmp_dir, console_static_dir = (
        prepare_runtime(
            working_dir_arg=args.working_dir,
            secret_dir_arg=args.secret_dir,
            console_static_dir_arg=args.console_static_dir,
            allow_missing_console=args.allow_missing_console,
        )
    )

    from qwenpaw.cli.app_cmd import app_cmd

    click_args = [
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--log-level",
        args.log_level,
    ]
    if args.reload:
        click_args.append("--reload")

    print(f"[backend-debug] repo={repo_root}")
    print(f"[backend-debug] working_dir={working_dir}")
    print(f"[backend-debug] secret_dir={secret_dir}")
    print(f"[backend-debug] tmp_dir={tmp_dir}")
    if console_static_dir is not None:
        print(f"[backend-debug] console_static_dir={console_static_dir}")
    else:
        print("[backend-debug] console_static_dir=<missing, allowed>")
    print(
        "[backend-debug] start: "
        f"host={args.host} port={args.port} reload={args.reload} "
        f"log={args.log_level}",
    )

    if args.dry_run:
        print("[backend-debug] dry-run 模式，未启动服务。")
        return

    app_cmd.main(
        args=click_args,
        prog_name="qwenpaw app",
        standalone_mode=True,
    )


if __name__ == "__main__":
    main()
