from typing import List

import pytest
import yaml
from yaml import SafeLoader


@pytest.fixture
def dependency_order() -> List[str]:
    """Ordered list of expected classes."""
    with open('config.yaml') as fp:
        gen3_config = yaml.load(fp, SafeLoader)
    return gen3_config['dependency_order']
