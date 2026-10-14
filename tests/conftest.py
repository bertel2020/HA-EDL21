"""Fixtures for EDL21 tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sml import SmlGetListResponse

import custom_components.edl21.sensor  # noqa: F401


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom_components."""


@pytest.fixture
def sml():
    """Patch the SML reader; yields a function that feeds a telegram."""
    with patch("custom_components.edl21.sensor.SmlProtocol") as proto_cls:
        proto = proto_cls.return_value
        proto.connect = AsyncMock()
        proto._impl = MagicMock(_disconnect=AsyncMock())  # noqa: SLF001

        def feed(vals):
            msg = SmlGetListResponse.__new__(SmlGetListResponse)
            dict.update(msg, serverId="0a 01 45", valList=vals)
            proto.add_listener.call_args.args[0](msg)

        yield feed
