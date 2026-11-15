import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))


@pytest.fixture
def anyio_backend():
    return "asyncio"
