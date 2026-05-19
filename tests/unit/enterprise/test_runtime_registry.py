from qwenpaw.enterprise.runtime_registry import (
    clear_enterprise_runtime,
    get_enterprise_runtime,
    set_enterprise_runtime,
)


def test_runtime_registry_set_get_clear():
    runtime = object()

    set_enterprise_runtime(runtime)
    assert get_enterprise_runtime() is runtime

    clear_enterprise_runtime(runtime)
    assert get_enterprise_runtime() is None


def test_runtime_registry_clear_ignores_other_runtime():
    runtime = object()
    other = object()

    set_enterprise_runtime(runtime)
    clear_enterprise_runtime(other)
    assert get_enterprise_runtime() is runtime

    clear_enterprise_runtime(runtime)
