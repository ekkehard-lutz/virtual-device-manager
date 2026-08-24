"""Tests for neutral history synchronization models."""

from datetime import UTC, datetime

import pytest

from custom_components.virtual_device.history.models import (
    SourceSnapshot,
    VirtualEntitySourceSnapshot,
)


def test_source_snapshot_is_immutable() -> None:
    snapshot = SourceSnapshot(
        device_id="lighting",
        entities=(
            VirtualEntitySourceSnapshot("energy", "energy", "sum", ("sensor.a",)),
        ),
        created_at=datetime.now(UTC),
    )

    with pytest.raises(AttributeError):
        snapshot.device_id = "changed"
