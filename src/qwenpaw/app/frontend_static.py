# -*- coding: utf-8 -*-
"""Frontend static routing with enterprise admin support.

Provides unified handling for console, webchat, and enterprise-admin
frontend builds with environment-controlled root path selection.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from ..constant import EnvVarLoader, PROJECT_NAME


logger = logging.getLogger(__name__)


_FRONTEND_MODE_ENV = "QWENPAW_FRONTEND_MODE"
_CONSOLE_ENABLED_ENV = "QWENPAW_CONSOLE_ENABLED"
_DEFAULT_FRONTEND_MODE = "enterprise"
_ALLOWED_FRONTEND_MODES = {"enterprise", "console"}


@dataclass(frozen=True)
class FrontendBuild:
    """前端构建元数据."""

    name: str
    static_dir: Path
    index_path: Path
    url_prefix: str


def get_frontend_mode() -> str:
    """读取 QWENPAW_FRONTEND_MODE 环境变量，默认使用 enterprise."""
    mode = EnvVarLoader.get_str(
        _FRONTEND_MODE_ENV,
        default=_DEFAULT_FRONTEND_MODE,
    )
    normalized_mode = mode.strip().lower()
    if normalized_mode in _ALLOWED_FRONTEND_MODES:
        return normalized_mode
    logger.warning(
        "Unknown %s value %r, falling back to %s.",
        _FRONTEND_MODE_ENV,
        mode,
        _DEFAULT_FRONTEND_MODE,
    )
    return _DEFAULT_FRONTEND_MODE


def is_console_enabled() -> bool:
    """读取 QWENPAW_CONSOLE_ENABLED 环境变量，默认关闭迁移期 Console 入口。"""
    return EnvVarLoader.get_bool(_CONSOLE_ENABLED_ENV, default=False)


def resolve_frontend_build(
    name: str,
    env_var: str,
    pkg_subdir: str,
    repo_subdir: str,
    url_prefix: str,
) -> FrontendBuild:
    """查找前端构建目录，支持环境变量覆盖、包内构建、仓库构建.

    Args:
        name: 构建名称（用于日志）
        env_var: 静态目录环境变量名
        pkg_subdir: 包内子目录名
        repo_subdir: 仓库子目录（如 "console/dist"）
        url_prefix: 路由前缀（如 "/console"）

    Returns:
        FrontendBuild 实例
    """
    static_dir = EnvVarLoader.get_str(env_var)
    if static_dir:
        static_path = Path(static_dir)
        logger.info(f"{name} static directory (from {env_var}): {static_path}")
        return FrontendBuild(
            name=name,
            static_dir=static_path,
            index_path=static_path / "index.html",
            url_prefix=url_prefix,
        )

    # Shipped dist lives in the package as static data
    pkg_dir = Path(__file__).resolve().parent.parent
    candidate = pkg_dir / pkg_subdir
    if candidate.is_dir() and (candidate / "index.html").exists():
        logger.info(f"{name} static directory (package): {candidate}")
        return FrontendBuild(
            name=name,
            static_dir=candidate,
            index_path=candidate / "index.html",
            url_prefix=url_prefix,
        )

    # Fallback to repo data
    repo_dir = pkg_dir.parent.parent
    candidate = repo_dir / repo_subdir
    if candidate.is_dir() and (candidate / "index.html").exists():
        logger.info(f"{name} static directory (repo): {candidate}")
        return FrontendBuild(
            name=name,
            static_dir=candidate,
            index_path=candidate / "index.html",
            url_prefix=url_prefix,
        )

    # Fallback to cwd data
    cwd = Path(os.getcwd())
    for subdir in (repo_subdir, f"{name}_dist"):
        candidate = cwd / subdir
        if candidate.is_dir() and (candidate / "index.html").exists():
            logger.info(f"{name} static directory (cwd): {candidate}")
            return FrontendBuild(
                name=name,
                static_dir=candidate,
                index_path=candidate / "index.html",
                url_prefix=url_prefix,
            )

    fallback = cwd / repo_subdir
    logger.warning(
        f"{name} static directory not found. Falling back to '{fallback}'.",
    )
    return FrontendBuild(
        name=name,
        static_dir=fallback,
        index_path=fallback / "index.html",
        url_prefix=url_prefix,
    )


def select_root_frontend(
    console_build: FrontendBuild,
    webchat_build: FrontendBuild,
    enterprise_build: FrontendBuild,
    console_enabled: bool | None = None,
) -> FrontendBuild:
    """根据 QWENPAW_FRONTEND_MODE 选择根路径服务的前端.

    - mode=enterprise 或默认: 优先服务企业工作台
    - mode=console 且 QWENPAW_CONSOLE_ENABLED=true: 迁移期显式服务控制台
    - mode=console 但未开启 console 开关: 仍回退到企业工作台
    - webchat 从不作为根路径

    Returns:
        作为根路径服务的 FrontendBuild
    """
    mode = get_frontend_mode()
    enabled = is_console_enabled() if console_enabled is None else console_enabled
    if mode == "console" and enabled:
        return console_build
    return enterprise_build


def _log_frontend_index_refs(name: str, index_path: Path | None) -> None:
    """记录构建到 SPA index 中的资产前缀，用于诊断 base url 问题."""
    if not index_path or not index_path.exists():
        logger.info("%s index not found; asset base cannot be inspected.", name)
        return

    try:
        html = index_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        logger.warning("%s index cannot be read for asset base check: %s", name, exc)
        return

    refs = re.findall(r'\b(?:src|href)="([^"]+)"', html)
    asset_refs = [
        ref for ref in refs if "/assets/" in ref or ref.startswith("assets/")
    ]
    if not asset_refs:
        logger.info("%s index asset base refs: none found", name)
        return

    logger.info("%s index asset base refs: %s", name, ", ".join(asset_refs[:5]))


def _make_console_unavailable_fallback() -> dict[str, str]:
    """当 console 构建不存在时，返回友好的 fallback 消息."""
    return {
        "message": (
            f"{PROJECT_NAME} web console is not available. "
            "If you installed the project from source code, please run "
            "`npm ci && npm run build` in the `console/` "
            f"directory, and restart {PROJECT_NAME} to enable the "
            "web console."
        ),
    }


def register_frontend_routes(
    app: FastAPI,
    console_build: FrontendBuild,
    webchat_build: FrontendBuild,
    enterprise_build: FrontendBuild,
) -> None:
    """注册 console、webchat、enterprise-admin 路由.

    默认模式下根路径 "/" 会 302 跳转到 "/enterprise-admin/"，
    "/webchat/*" 始终独立服务 WebChat，
    "/console/*" 仅在 QWENPAW_CONSOLE_ENABLED=true 时作为迁移期入口暴露，
    catch-all "/*" 仅在显式 console 迁移模式下注册为控制台 SPA fallback。
    """
    # 记录所有前端构建的资产引用
    _log_frontend_index_refs("console", console_build.index_path)
    _log_frontend_index_refs("webchat", webchat_build.index_path)
    _log_frontend_index_refs("enterprise-admin", enterprise_build.index_path)

    console_enabled = is_console_enabled()

    # 选择根路径前端
    root_build = select_root_frontend(
        console_build,
        webchat_build,
        enterprise_build,
        console_enabled=console_enabled,
    )

    # ---------- 根路径 "/" ----------
    def _serve_root_index():
        # enterprise 模式下根路径重定向到 /enterprise-admin/，解决 SPA basename 匹配问题
        if root_build.name == "enterprise-admin":
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/enterprise-admin/", status_code=302)
        # console 模式正常服务
        if root_build.index_path and root_build.index_path.exists():
            return FileResponse(root_build.index_path)
        # 如果根前端不存在且根是 console，返回 fallback
        if root_build.name == "console":
            return _make_console_unavailable_fallback()
        raise HTTPException(status_code=404, detail="Not Found")

    app.get("/")(_serve_root_index)

    # ---------- /console/* ----------
    if console_enabled and console_build.static_dir.is_dir():

        def _serve_console_index():
            if console_build.index_path and console_build.index_path.exists():
                return FileResponse(console_build.index_path)
            raise HTTPException(status_code=404, detail="Not Found")

        _console_assets = console_build.static_dir / "assets"
        if _console_assets.is_dir():
            app.mount(
                "/assets",
                StaticFiles(directory=str(_console_assets)),
                name="assets",
            )

        @app.get("/console")
        @app.get("/console/")
        @app.get("/console/{full_path:path}")
        def _console_spa(full_path: str = ""):
            _ = full_path
            return _serve_console_index()

    # ---------- /webchat/* ----------
    if webchat_build.static_dir.is_dir():

        def _serve_webchat_index():
            if webchat_build.index_path and webchat_build.index_path.exists():
                return FileResponse(webchat_build.index_path)
            raise HTTPException(status_code=404, detail="Not Found")

        _webchat_assets = webchat_build.static_dir / "assets"
        if _webchat_assets.is_dir():
            app.mount(
                "/webchat/assets",
                StaticFiles(directory=str(_webchat_assets)),
                name="webchat-assets",
            )

        @app.get("/webchat")
        @app.get("/webchat/")
        @app.get("/webchat/{full_path:path}")
        def _webchat_spa(full_path: str = ""):
            _ = full_path
            return _serve_webchat_index()

    # ---------- /enterprise-admin/* ----------
    if enterprise_build.static_dir.is_dir():

        def _serve_enterprise_index():
            if enterprise_build.index_path and enterprise_build.index_path.exists():
                return FileResponse(enterprise_build.index_path)
            raise HTTPException(status_code=404, detail="Not Found")

        _enterprise_assets = enterprise_build.static_dir / "assets"
        if _enterprise_assets.is_dir():
            app.mount(
                "/enterprise-admin/assets",
                StaticFiles(directory=str(_enterprise_assets)),
                name="enterprise-admin-assets",
            )

        @app.get("/enterprise-admin")
        @app.get("/enterprise-admin/")
        @app.get("/enterprise-admin/{full_path:path}")
        def _enterprise_spa(full_path: str = ""):
            _ = full_path
            return _serve_enterprise_index()

    # ---------- Catch-all /* - 仅当根不是 enterprise 时 ----------
    if (
        console_enabled
        and root_build.name != "enterprise-admin"
        and console_build.static_dir.is_dir()
    ):
        _console_path = console_build.static_dir

        def _serve_console_index_fallback():
            if console_build.index_path and console_build.index_path.exists():
                return FileResponse(console_build.index_path)
            raise HTTPException(status_code=404, detail="Not Found")

        @app.get("/{full_path:path}")
        def _console_catch_all(full_path: str):
            # 阻止捕获常见的系统/特殊路径
            if full_path in ("docs", "redoc", "openapi.json"):
                raise HTTPException(status_code=404, detail="Not Found")
            # 跳过 API 路由
            if full_path.startswith("api/") or full_path == "api":
                raise HTTPException(status_code=404, detail="Not Found")
            # 跳过 webchat 路由
            if full_path.startswith("webchat/") or full_path == "webchat":
                raise HTTPException(status_code=404, detail="Not Found")
            # 跳过 enterprise-admin 路由
            if full_path.startswith("enterprise-admin/") or full_path == "enterprise-admin":
                raise HTTPException(status_code=404, detail="Not Found")

            # 服务静态文件
            if full_path and ".." not in full_path:
                if not Path(full_path).is_absolute():
                    static_file = _console_path / full_path
                    if static_file.is_file():
                        return FileResponse(static_file)

            return _serve_console_index_fallback()
