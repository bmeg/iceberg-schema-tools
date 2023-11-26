# Tests for the link description object
from typing import Callable

import jsonschema
import fastjsonschema
import pytest
from jsonschema.validators import Draft202012Validator
from referencing import Registry


# import re

def test_validate_edge_properties_fastjsonschema(compiled_schema: Callable,
                                                 instance: dict,
                                                 bad_instance: dict,
                                                 bad_links: dict):
    """Ensures schema validates using the fastjsonschema library."""

    # validate schema, checks `valid` nested object data.fizz.buzz
    compiled_schema(instance)

    # validate schema, checks `invalid` nested object data.fizz.buzz
    with pytest.raises(fastjsonschema.exceptions.JsonSchemaException):
        compiled_schema(bad_instance)

    # validate schema, test missing link required properties
    with pytest.raises(fastjsonschema.exceptions.JsonSchemaException):
        compiled_schema(bad_links)


def test_validate_edge_properties(schema: dict,
                                  registry: Registry,
                                  instance: dict,
                                  bad_instance: dict,
                                  bad_links: dict):
    """Ensures schema validates using the jsonschema library."""

    # validate schema, checks `valid` nested object data.fizz.buzz
    assert Draft202012Validator(
        schema=schema,
        registry=registry,
    ).validate(instance) is None, "Instance should have validated"

    # validate schema, checks `invalid` nested object data.fizz.buzz
    with pytest.raises(jsonschema.exceptions.ValidationError):
        assert Draft202012Validator(
            schema=schema,
            registry=registry,
        ).validate(bad_instance) is not None, "Instance should not have validated"

    # validate schema, test `missing link` required properties
    with pytest.raises(jsonschema.exceptions.ValidationError):
        assert Draft202012Validator(
            schema=schema,
            registry=registry,
        ).validate(bad_links) is not None, "Instance should not have validated"


def test_schema_is_association(schema: dict):
    """schema should be an association"""
    assert 'links' in schema, 'Schema should have links'
    assert len(schema['links']) >= 2, "Association schema should have at least two links"
    is_association = False
    for _ in schema['links']:
        if 'targetHints' in _:
            if _['targetHints'].get('association', False):
                is_association = True
    print(schema)
    assert is_association, "Schema should be an association"


def test_validate_instance(schema: dict, instance: dict):
    """Ensure instance is a valid association"""
    # validate links
    assert len(instance['links']) >= 2, "Association instance should have at least two links"

    # verify that all links are in schema
    schema_relationships = [_['rel'] for _ in schema['links']]
    for link in instance['links']:
        assert link['rel'] in schema_relationships, f"Instance of this association should have links to {schema_relationships}"
