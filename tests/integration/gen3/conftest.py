import json
import pytest

import os

from dictionaryutils import DataDictionary


@pytest.fixture()
def gen3_dir():
    """cd to gen3 dir"""
    # setup
    cwd = os.getcwd()
    os.chdir('iceberg/schemas/gen3')
    # run test
    yield 'iceberg/schemas/gen3_dir'
    # teardown
    os.chdir(cwd)


@pytest.fixture()
def data_dictionary_from_yaml(gen3_dir) -> DataDictionary:
    """Load the schema from individual yaml files."""
    yield DataDictionary(root_dir=os.getcwd())


@pytest.fixture()
def distribution_schema(gen3_dir) -> dict:
    """Load the aced.json schema"""
    yield json.load(open("aced.json"))
