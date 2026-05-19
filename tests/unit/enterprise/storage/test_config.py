from qwenpaw.enterprise.storage.config import StorageConfig


def test_storage_config_defaults_to_json(monkeypatch):
    monkeypatch.delenv("QWENPAW_STORAGE_BACKEND", raising=False)
    config = StorageConfig.from_env()
    assert config.backend == "json"
    assert config.enabled is False


def test_storage_config_sqlite(monkeypatch):
    monkeypatch.setenv("QWENPAW_STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("QWENPAW_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    config = StorageConfig.from_env()
    assert config.backend == "sqlite"
    assert config.enabled is True
    assert config.database_url == "sqlite+aiosqlite:///:memory:"


def test_storage_config_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("QWENPAW_STORAGE_BACKEND", "mongo")
    try:
        StorageConfig.from_env()
    except ValueError as exc:
        assert "Unsupported storage backend" in str(exc)
    else:
        raise AssertionError("StorageConfig must reject unsupported backend")
