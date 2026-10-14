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
        proto._impl = MagicMock(  # noqa: SLF001
            _disconnect=AsyncMock(), _reconnect=AsyncMock()
        )

        def feed(vals, server_id="0a 01 45"):
            msg = SmlGetListResponse.__new__(SmlGetListResponse)
            dict.update(msg, serverId=server_id, valList=vals)
            proto.add_listener.call_args.args[0](msg)

        feed.proto = proto
        yield feed
