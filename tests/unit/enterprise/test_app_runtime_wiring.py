def test_app_exposes_enterprise_runtime_imports():
    from qwenpaw.enterprise.runtime import create_enterprise_runtime

    runtime = create_enterprise_runtime()
    assert runtime.storage is not None
