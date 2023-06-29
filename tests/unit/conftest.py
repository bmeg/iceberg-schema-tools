from typing import List

import pytest


@pytest.fixture
def python_source_directories() -> List[str]:
    """Directories to scan with flake8."""
    return ["tools", "tests"]
