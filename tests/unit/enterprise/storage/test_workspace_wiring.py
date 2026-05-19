from qwenpaw.enterprise.storage.config import StorageConfig
from qwenpaw.enterprise.storage.manager import (
    StorageManager,
    get_storage_manager_from_app,
)


def test_storage_manager_is_resolved_from_workspace_app_state():
    storage = StorageManager(StorageConfig(backend="json"))

    class State:
        enterprise_runtime = type("Runtime", (), {"storage": storage})()

    class App:
        state = State()

    assert get_storage_manager_from_app(App()) is storage


def test_get_storage_manager_returns_none_without_app():
    assert get_storage_manager_from_app(None) is None


def test_get_storage_manager_returns_none_without_runtime():
    class State:
        pass

    class App:
        state = State()

    assert get_storage_manager_from_app(App()) is None


def test_get_storage_manager_returns_none_for_noop():
    """NoopStorageManager 不是 StorageManager 实例，应返回 None。"""
    from qwenpaw.enterprise.noop import NoopStorageManager

    class Runtime:
        storage = NoopStorageManager()

    class State:
        enterprise_runtime = Runtime()

    class App:
        state = State()

    assert get_storage_manager_from_app(App()) is None
