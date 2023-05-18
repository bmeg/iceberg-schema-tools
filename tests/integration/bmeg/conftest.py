import json
import os
import pathlib

import pytest
from jsonschema.validators import Draft202012Validator

from tests.integration.bmeg import is_edge


@pytest.fixture()
def bmeg_dir():
    """cd to bmeg dir"""
    # setup
    cwd = os.getcwd()
    os.chdir('iceberg/schemas/bmeg')
    # run test
    yield 'iceberg/schemas/bmeg'
    # teardown
    os.chdir(cwd)


@pytest.fixture()
def fhir_schema(bmeg_dir):
    fhir_schema = json.load(open("aced-bmeg.json"))
    Draft202012Validator.check_schema(fhir_schema)
    yield fhir_schema


@pytest.fixture()
def fhir_validator(fhir_schema):
    yield Draft202012Validator(fhir_schema)


@pytest.fixture()
def vertex_schemas(fhir_schema):
    yield [v for v in fhir_schema['$defs'].values() if not is_edge(v)]


@pytest.fixture()
def edge_schemas(fhir_schema):
    yield [v for v in fhir_schema['$defs'].values() if is_edge(v)]


@pytest.fixture()
def lath_path():
    return pathlib.Path('~/go/bin/lathe').expanduser()
