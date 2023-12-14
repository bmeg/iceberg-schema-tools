import json
import pytest

import os

from iceberg_tools.dictionaryutils import DataDictionary


@pytest.fixture()
def simplified_dir():
    """cd to simplified dir"""
    # setup
    cwd = os.getcwd()
    os.chdir('iceberg/schemas/simplified')
    # run test
    yield 'iceberg/schemas/simplified'
    # teardown
    os.chdir(cwd)


@pytest.fixture()
def data_dictionary_from_yaml(simplified_dir) -> DataDictionary:
    """Load the schema from individual yaml files."""
    yield DataDictionary(root_dir=os.getcwd())


@pytest.fixture()
def distribution_schema(distribution_schema_path) -> dict:
    """Load the simplified-fhir schema"""
    yield json.load(open(distribution_schema_path))


@pytest.fixture()
def distribution_schema_path(simplified_dir) -> str:
    """path to the simplified-fhir schema"""
    return "simplified-fhir.json"
