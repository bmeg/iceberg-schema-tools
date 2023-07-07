from typing import List, Callable

import fastjsonschema
import pytest
import yaml


@pytest.fixture
def python_source_directories() -> List[str]:
    """Directories to scan with flake8."""
    return ["tools", "tests"]


_SCHEMA = yaml.safe_load("""
---
"$schema": https://json-schema.org/draft/2020-12/schema
"$id": https://bmeg.io/foo-bar-association
title: FooBarAssociation
properties:
  data:
    type: object
    properties:
      fizz:
        type: string
  links:
    type: array
    items:
      "$ref": https://json-schema.org/draft/2020-12/links

links:
- rel: bar
  href: urn:uuid:{id}
  targetSchema:
    "$ref": Foo
  templatePointers:
    id: "/id"
  targetHints:
    multiplicity:
        - has_many
    directionality:
        - out
    association:
        - true

- rel: foo
  href: Bar/{id}
  targetSchema:
    "$ref": Bar
  templatePointers:
    id: "/id"
  targetHints:
    multiplicity:
        - has_many
    directionality:
        - out
    association:
        - true
""")

_INSTANCE = yaml.safe_load("""
---
data:
  fizz: buzz
links:
- rel: foo
  href: Bar/9a652678-4616-475d-af12-aca21cfbe06d
- rel: bar
  href: urn:uuid:f81d4fae-7dec-11d0-a765-00a0c91e6bf6
""")

_BAD_INSTANCE = yaml.safe_load("""
---
data:
  # this should be a string
  fizz: 1
links:
- rel: foo
  href: Bar/9a652678-4616-475d-af12-aca21cfbe06d
- rel: bar
  href: urn:uuid:f81d4fae-7dec-11d0-a765-00a0c91e6bf6
""")

_BAD_LINKS = yaml.safe_load("""
---
data:
  fizz: buzz
links:
- missing_required_fields: xxx
- rel: bar
  href: urn:uuid:f81d4fae-7dec-11d0-a765-00a0c91e6bf6
""")


_NOT_ASSOCIATION_SCHEMA = yaml.safe_load("""
---
"$schema": https://json-schema.org/draft/2020-12/schema
"$id": https://bmeg.io/not-an-association
properties:
  data:
    type: object
    properties:
      fizz:
        type: string
  links:
    type: array
    items:
      "$ref": https://json-schema.org/draft/2020-12/links

""")


# * A Foo instance
_FOO = yaml.safe_load("""
---
id: f81d4fae-7dec-11d0-a765-00a0c91e6bf6
""")

_BAD_FOO = yaml.safe_load("""
---
missing_id: xxxxx
""")


# * A Bar instance

_BAR = yaml.safe_load("""
---
id: 9a652678-4616-475d-af12-aca21cfbe06d
""")


_NESTED_REFERENCES = yaml.safe_load("""
---
references:
- id: s-processing-1
  resourceType: Specimen
  _expected_reference_count: 1
  processing:
  - additive:
    - reference: Substance/sub-1
- id: s-processing-2
  resourceType: Specimen
  _expected_reference_count: 2
  processing:
  - additive:
    - reference: Substance/sub-1
  - additive:
    - reference: Substance/sub-2
- id: s-processing-3
  resourceType: Specimen
  _expected_reference_count: 2
  processing:
  - additive:
    - reference: Substance/sub-1
    - reference: Substance/sub-2
""")


@pytest.fixture
def nested_references():
    return _NESTED_REFERENCES['references']


@pytest.fixture
def schema():
    return _SCHEMA


@pytest.fixture
def not_an_association_schema():
    return _NOT_ASSOCIATION_SCHEMA


@pytest.fixture
def instance():
    return _INSTANCE


@pytest.fixture
def bad_instance():
    return _BAD_INSTANCE


@pytest.fixture
def bad_links():
    return _BAD_LINKS


@pytest.fixture
def compiled_schema(schema: dict) -> Callable:
    """compile schema"""
    return fastjsonschema.compile(schema)


@pytest.fixture
def foo() -> dict:
    """Instance of Foo"""
    return _FOO


@pytest.fixture
def bar() -> dict:
    """Instance of Bar"""
    return _BAR


@pytest.fixture
def bad_foo() -> dict:
    """Instance of Foo with missing id"""
    return _BAD_FOO
