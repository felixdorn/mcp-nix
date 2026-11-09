"""Use one supported async runtime for protocol and live checks."""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
