#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""后端启动脚本的公共辅助函数。"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def repo_root() -> Path:
    """返回仓库根目录。"""
    return Path(__file__).resolve().parents[1]


def resolve_from_repo(current_repo_root: Path, raw: str) -> Path:
    """按仓库根目录解析相对路径。"""
    value = (raw or "").strip()
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (current_repo_root / path).resolve()


def ensure_src_on_path(current_repo_root: Path) -> None:
    """确保仓库 `src/` 已加入导入路径。"""
    src_dir = current_repo_root / "src"
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


def load_repo_dotenv(current_repo_root: Path) -> None:
    """优先加载仓库根目录下的 `.env`。"""
    env_path = current_repo_root / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except Exception:
        # 非致命失败，运行时仍会再次尝试加载。
        pass


def prepare_working_dir_env(
    current_repo_root: Path,
    cli_working_dir: str = "",
) -> Path:
    """解析并导出工作目录环境变量。"""
    if cli_working_dir.strip():
        resolved = resolve_from_repo(current_repo_root, cli_working_dir)
        os.environ["QWENPAW_WORKING_DIR"] = str(resolved)
        return resolved

    for key in ("QWENPAW_WORKING_DIR", "COPAW_WORKING_DIR"):
        value = os.getenv(key, "").strip()
        if value:
            resolved = resolve_from_repo(current_repo_root, value)
            os.environ["QWENPAW_WORKING_DIR"] = str(resolved)
            return resolved

    multitenant_dir = os.getenv("MULTITENANT_WORKING_DIR", "").strip()
    if multitenant_dir:
        resolved = resolve_from_repo(current_repo_root, multitenant_dir)
        os.environ["QWENPAW_WORKING_DIR"] = str(resolved)
        return resolved

    resolved = (current_repo_root / "data").resolve()
    os.environ["QWENPAW_WORKING_DIR"] = str(resolved)
    return resolved


def validate_multitenant_runtime_policy() -> None:
    """校验默认开启的多租户部署模式。"""
    mode = os.getenv("MULTITENANT_DEPLOYMENT_MODE", "single").strip().lower()
    mode = mode or "single"
    if mode not in {"single", "distributed"}:
        raise RuntimeError(
            "MULTITENANT_DEPLOYMENT_MODE 仅支持 single 或 distributed",
        )

    if mode == "distributed" and not os.getenv("MULTITENANT_REDIS_URL", "").strip():
        raise RuntimeError(
            "MULTITENANT_DEPLOYMENT_MODE=distributed 时必须配置 "
            "MULTITENANT_REDIS_URL",
        )

    os.environ["MULTITENANT_DEPLOYMENT_MODE"] = mode


def prepare_secret_dir_env(
    current_repo_root: Path,
    working_dir: Path,
    cli_secret_dir: str = "",
) -> Path:
    """解析并导出密钥目录环境变量。"""
    if cli_secret_dir.strip():
        resolved = resolve_from_repo(current_repo_root, cli_secret_dir)
        os.environ["QWENPAW_SECRET_DIR"] = str(resolved)
        return resolved

    secret_env = os.getenv("QWENPAW_SECRET_DIR", "").strip()
    if secret_env:
        resolved = resolve_from_repo(current_repo_root, secret_env)
        os.environ["QWENPAW_SECRET_DIR"] = str(resolved)
        return resolved

    repo_data_dir = (current_repo_root / "data").resolve()
    if working_dir == repo_data_dir:
        resolved = (current_repo_root / "data.secret").resolve()
    else:
        resolved = Path(f"{working_dir}.secret").resolve()

    os.environ["QWENPAW_SECRET_DIR"] = str(resolved)
    return resolved


def resolve_console_static_dir(
    current_repo_root: Path,
    cli_console_static_dir: str = "",
) -> Path | None:
    """按运行时约定解析控制台静态资源目录。"""
    candidates: list[Path] = []

    if cli_console_static_dir.strip():
        candidates.append(
            resolve_from_repo(current_repo_root, cli_console_static_dir),
        )

    env_static_dir = os.getenv("QWENPAW_CONSOLE_STATIC_DIR", "").strip()
    if env_static_dir:
        candidates.append(resolve_from_repo(current_repo_root, env_static_dir))

    candidates.extend(
        [
            (current_repo_root / "src" / "qwenpaw" / "console").resolve(),
            (current_repo_root / "console" / "dist").resolve(),
        ],
    )

    for candidate in candidates:
        if candidate.is_dir() and (candidate / "index.html").exists():
            return candidate
    return None


def prepare_console_static_env(
    current_repo_root: Path,
    cli_console_static_dir: str = "",
    allow_missing_console: bool = False,
) -> Path | None:
    """设置控制台静态资源环境变量。"""
    resolved = resolve_console_static_dir(
        current_repo_root=current_repo_root,
        cli_console_static_dir=cli_console_static_dir,
    )
    if resolved is None:
        if allow_missing_console:
            return None
        raise FileNotFoundError(
            "未找到控制台静态资源。请先执行前端构建，或使用 "
            "--console-static-dir 显式指定目录。",
        )

    os.environ["QWENPAW_CONSOLE_STATIC_DIR"] = str(resolved)
    return resolved


def prepare_tmp_dir(current_repo_root: Path) -> Path:
    """准备仓库内的临时目录。"""
    tmp_dir = current_repo_root / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("TMP", str(tmp_dir))
    os.environ.setdefault("TEMP", str(tmp_dir))
    os.environ.setdefault("TMPDIR", str(tmp_dir))
    return tmp_dir


def ensure_runtime_dirs(*paths: Path) -> None:
    """确保运行时目录存在。"""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def prepare_runtime(
    working_dir_arg: str = "",
    secret_dir_arg: str = "",
    console_static_dir_arg: str = "",
    allow_missing_console: bool = False,
) -> tuple[Path, Path, Path, Path, Path | None]:
    """统一准备运行环境并返回解析后的目录。"""
    current_repo_root = repo_root()
    load_repo_dotenv(current_repo_root)
    validate_multitenant_runtime_policy()

    working_dir = prepare_working_dir_env(
        current_repo_root=current_repo_root,
        cli_working_dir=working_dir_arg,
    )
    secret_dir = prepare_secret_dir_env(
        current_repo_root=current_repo_root,
        working_dir=working_dir,
        cli_secret_dir=secret_dir_arg,
    )
    console_static_dir = prepare_console_static_env(
        current_repo_root=current_repo_root,
        cli_console_static_dir=console_static_dir_arg,
        allow_missing_console=allow_missing_console,
    )

    ensure_src_on_path(current_repo_root)
    tmp_dir = prepare_tmp_dir(current_repo_root)
    ensure_runtime_dirs(working_dir, secret_dir, tmp_dir)
    return current_repo_root, working_dir, secret_dir, tmp_dir, console_static_dir
