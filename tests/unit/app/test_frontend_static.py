# -*- coding: utf-8 -*-
"""Unit tests for frontend static routing with enterprise admin support."""
from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

_WORKTREE_SRC = Path(__file__).resolve().parents[3] / "src"
_WORKTREE_QWENPAW = _WORKTREE_SRC / "qwenpaw"
_WORKTREE_APP = _WORKTREE_QWENPAW / "app"

def _prepend_unique_path(paths: list[str], new_path: Path) -> list[str]:
    resolved_new_path = str(new_path.resolve())
    normalized_paths = [str(Path(path).resolve()) for path in paths]
    return [resolved_new_path, *[path for path in normalized_paths if path != resolved_new_path]]


def _import_frontend_static_from_worktree():
    pkg = sys.modules.get("qwenpaw")
    app_pkg = sys.modules.get("qwenpaw.app")
    previous_sys_path = list(sys.path)
    previous_pkg_path = list(getattr(pkg, "__path__", [])) if pkg is not None else None
    previous_app_path = list(getattr(app_pkg, "__path__", [])) if app_pkg is not None else None
    previous_frontend_static = sys.modules.get("qwenpaw.app.frontend_static")
    removed_stale_frontend_static = False

    try:
        sys.path = _prepend_unique_path(sys.path, _WORKTREE_SRC)

        # Worktree 验证不能被 editable install 指向的原仓库包路径污染。
        if pkg is not None:
            pkg.__path__ = _prepend_unique_path(list(pkg.__path__), _WORKTREE_QWENPAW)

        if app_pkg is not None:
            app_pkg.__path__ = _prepend_unique_path(list(app_pkg.__path__), _WORKTREE_APP)

        if previous_frontend_static is not None:
            loaded_path = Path(getattr(previous_frontend_static, "__file__", "")).resolve()
            if _WORKTREE_SRC.resolve() not in loaded_path.parents:
                del sys.modules["qwenpaw.app.frontend_static"]
                removed_stale_frontend_static = True

        module = import_module("qwenpaw.app.frontend_static")
    finally:
        sys.path = previous_sys_path
        if pkg is not None and previous_pkg_path is not None:
            pkg.__path__ = previous_pkg_path
        if app_pkg is not None and previous_app_path is not None:
            app_pkg.__path__ = previous_app_path
        if previous_frontend_static is not None:
            sys.modules["qwenpaw.app.frontend_static"] = previous_frontend_static
        elif removed_stale_frontend_static:
            sys.modules.pop("qwenpaw.app.frontend_static", None)

    return module


_frontend_static = _import_frontend_static_from_worktree()
assert _WORKTREE_SRC.resolve() in Path(_frontend_static.__file__).resolve().parents

FrontendBuild = _frontend_static.FrontendBuild
get_frontend_mode = _frontend_static.get_frontend_mode
is_console_enabled = _frontend_static.is_console_enabled
register_frontend_routes = _frontend_static.register_frontend_routes
select_root_frontend = _frontend_static.select_root_frontend


def _write_index(static_dir: Path, body: str) -> None:
    static_dir.mkdir()
    (static_dir / "index.html").write_text(
        f"<!DOCTYPE html><html><body>{body}</body></html>",
        encoding="utf-8",
    )
    (static_dir / "assets").mkdir()


def _make_frontend_builds(
    tmp_path: Path,
) -> tuple[FrontendBuild, FrontendBuild, FrontendBuild]:
    enterprise_dir = tmp_path / "enterprise-admin"
    console_dir = tmp_path / "console"
    webchat_dir = tmp_path / "webchat"
    _write_index(enterprise_dir, "Enterprise Admin")
    _write_index(console_dir, "Console")
    _write_index(webchat_dir, "WebChat")
    return (
        FrontendBuild(
            name="enterprise-admin",
            static_dir=enterprise_dir,
            index_path=enterprise_dir / "index.html",
            url_prefix="/enterprise-admin",
        ),
        FrontendBuild(
            name="console",
            static_dir=console_dir,
            index_path=console_dir / "index.html",
            url_prefix="/console",
        ),
        FrontendBuild(
            name="webchat",
            static_dir=webchat_dir,
            index_path=webchat_dir / "index.html",
            url_prefix="/webchat",
        ),
    )


def test_frontend_mode_defaults_to_enterprise() -> None:
    """未配置 QWENPAW_FRONTEND_MODE 时，默认模式为 enterprise."""
    with patch.dict(os.environ, {}, clear=True):
        mode = get_frontend_mode()
        assert mode == "enterprise"


def test_frontend_mode_allows_console_for_migration() -> None:
    """显式配置 QWENPAW_FRONTEND_MODE=console 时，允许迁移期开关."""
    with patch.dict(os.environ, {"QWENPAW_FRONTEND_MODE": "console"}):
        mode = get_frontend_mode()
        assert mode == "console"


def test_frontend_mode_falls_back_to_enterprise_for_unknown_value() -> None:
    """未知前端模式应回退到 enterprise."""
    with patch.dict(os.environ, {"QWENPAW_FRONTEND_MODE": "legacy"}):
        mode = get_frontend_mode()
        assert mode == "enterprise"


def test_console_enabled_defaults_false() -> None:
    """未配置 QWENPAW_CONSOLE_ENABLED 时，console 开关默认为关闭。"""
    with patch.dict(os.environ, {}, clear=True):
        assert is_console_enabled() is False


def test_console_enabled_reads_true() -> None:
    """QWENPAW_CONSOLE_ENABLED=true 时，console 开关应开启。"""
    with patch.dict(os.environ, {"QWENPAW_CONSOLE_ENABLED": "true"}, clear=True):
        assert is_console_enabled() is True


def test_select_root_frontend_uses_enterprise_mode() -> None:
    """QWENPAW_FRONTEND_MODE=enterprise 时，根路径优先服务企业工作台."""
    console_build = FrontendBuild(
        name="console",
        static_dir=Path("/fake/console"),
        index_path=Path("/fake/console/index.html"),
        url_prefix="/console",
    )
    webchat_build = FrontendBuild(
        name="webchat",
        static_dir=Path("/fake/webchat"),
        index_path=Path("/fake/webchat/index.html"),
        url_prefix="/webchat",
    )
    enterprise_build = FrontendBuild(
        name="enterprise-admin",
        static_dir=Path("/fake/enterprise-admin"),
        index_path=Path("/fake/enterprise-admin/index.html"),
        url_prefix="/enterprise-admin",
    )

    with patch.dict(os.environ, {"QWENPAW_FRONTEND_MODE": "enterprise"}):
        root_build = select_root_frontend(
            console_build=console_build,
            webchat_build=webchat_build,
            enterprise_build=enterprise_build,
        )
        assert root_build is enterprise_build
        assert root_build.name == "enterprise-admin"


def test_register_frontend_routes_serves_enterprise_admin(
    tmp_path: Path,
) -> None:
    """register_frontend_routes 应服务 /enterprise-admin/ 路由."""
    enterprise_build, console_build, webchat_build = _make_frontend_builds(tmp_path)
    enterprise_dir = enterprise_build.static_dir
    (enterprise_dir / "assets" / "app.js").write_text("console.log('enterprise')")

    app = FastAPI()
    register_frontend_routes(
        app=app,
        console_build=console_build,
        webchat_build=webchat_build,
        enterprise_build=enterprise_build,
    )

    client = TestClient(app)

    # 测试企业工作台路由
    response = client.get("/enterprise-admin/")
    assert response.status_code == 200
    assert "Enterprise Admin" in response.text

    response = client.get("/enterprise-admin/dashboard")
    assert response.status_code == 200
    assert "Enterprise Admin" in response.text


def test_register_frontend_routes_enterprise_root_redirect(
    tmp_path: Path,
) -> None:
    """enterprise 模式下根路径 / 应重定向到 /enterprise-admin/."""
    enterprise_build, console_build, webchat_build = _make_frontend_builds(tmp_path)

    app = FastAPI()
    with patch.dict(os.environ, {"QWENPAW_FRONTEND_MODE": "enterprise"}):
        register_frontend_routes(
            app=app,
            console_build=console_build,
            webchat_build=webchat_build,
            enterprise_build=enterprise_build,
        )

    client = TestClient(app)

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/enterprise-admin/"

    # enterprise 模式下 catch-all 不应注册 console fallback
    response = client.get("/unknown-path")
    assert response.status_code == 404


def test_register_frontend_routes_defaults_root_to_enterprise_admin(
    tmp_path: Path,
) -> None:
    """clear env 下根路径应默认跳转到企业工作台，未知路径不走 console fallback."""
    enterprise_build, console_build, webchat_build = _make_frontend_builds(tmp_path)

    app = FastAPI()
    with patch.dict(os.environ, {}, clear=True):
        register_frontend_routes(
            app=app,
            console_build=console_build,
            webchat_build=webchat_build,
            enterprise_build=enterprise_build,
        )

    client = TestClient(app)

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/enterprise-admin/"

    response = client.get("/unknown-path")
    assert response.status_code == 404


def test_console_mode_without_console_enabled_keeps_root_on_enterprise_admin(
    tmp_path: Path,
) -> None:
    """仅设置 console mode 时，根路径仍应停留在 enterprise-admin。"""
    enterprise_build, console_build, webchat_build = _make_frontend_builds(tmp_path)

    app = FastAPI()
    with patch.dict(os.environ, {"QWENPAW_FRONTEND_MODE": "console"}, clear=True):
        register_frontend_routes(
            app=app,
            console_build=console_build,
            webchat_build=webchat_build,
            enterprise_build=enterprise_build,
        )

    client = TestClient(app)

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/enterprise-admin/"
    assert "Console" not in response.text


def test_register_frontend_routes_keeps_webchat_independent(
    tmp_path: Path,
) -> None:
    """clear env 下 WebChat 仍独立服务，不受默认根路径影响."""
    enterprise_build, console_build, webchat_build = _make_frontend_builds(tmp_path)

    app = FastAPI()
    with patch.dict(os.environ, {}, clear=True):
        register_frontend_routes(
            app=app,
            console_build=console_build,
            webchat_build=webchat_build,
            enterprise_build=enterprise_build,
        )

    client = TestClient(app)

    response = client.get("/webchat/")
    assert response.status_code == 200
    assert "WebChat" in response.text


def test_console_route_is_disabled_by_default(tmp_path: Path) -> None:
    enterprise_build, console_build, webchat_build = _make_frontend_builds(tmp_path)
    app = FastAPI()
    with patch.dict(os.environ, {}, clear=True):
        register_frontend_routes(
            app=app,
            console_build=console_build,
            webchat_build=webchat_build,
            enterprise_build=enterprise_build,
        )
    client = TestClient(app)
    response = client.get("/console/")
    assert response.status_code == 404


def test_console_route_can_be_enabled_for_migration(tmp_path: Path) -> None:
    enterprise_build, console_build, webchat_build = _make_frontend_builds(tmp_path)
    app = FastAPI()
    with patch.dict(
        os.environ,
        {
            "QWENPAW_FRONTEND_MODE": "console",
            "QWENPAW_CONSOLE_ENABLED": "true",
        },
        clear=True,
    ):
        register_frontend_routes(
            app=app,
            console_build=console_build,
            webchat_build=webchat_build,
            enterprise_build=enterprise_build,
        )
    client = TestClient(app)
    response = client.get("/console/")
    assert response.status_code == 200
    assert "Console" in response.text
