"""Hard invariant: history synchronization has one explicit entry point."""

from pathlib import Path


def test_automatic_lifecycle_modules_never_invoke_history_sync() -> None:
    """Creation, updates, reconciliation, startup, and reload never start sync."""
    integration = Path("custom_components/virtual_device")
    automatic_modules = (
        "__init__.py",
        "source_manager.py",
        "lifecycle.py",
        "virtual_device_manager.py",
        "virtual_device_workflow.py",
        "virtual_device_services.py",
        "sensor.py",
        "storage.py",
    )

    for module in automatic_modules:
        assert ".async_sync(" not in (integration / module).read_text(encoding="utf-8")


def test_websocket_is_the_only_production_sync_invocation() -> None:
    integration = Path("custom_components/virtual_device")
    callers = []
    for path in integration.rglob("*.py"):
        if path.name == "manager.py" and path.parent.name == "history":
            continue
        if ".async_sync(" in path.read_text(encoding="utf-8"):
            callers.append(path.as_posix())

    assert callers == ["custom_components/virtual_device/websocket.py"]
