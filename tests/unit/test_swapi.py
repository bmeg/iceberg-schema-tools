import json
import os

import pathlib
from typing import Any

import pytest
import requests
import yaml

import fastjsonschema

from iceberg_tools.graph import VertexLinkWriter
from iceberg_tools.schema.graph import bundle_schemas

SCHEMA_PATHS = """
        tests/fixtures/swapi/character.yaml
        tests/fixtures/swapi/film.yaml
        tests/fixtures/swapi/planet.yaml
        tests/fixtures/swapi/species.yaml
        tests/fixtures/swapi/starship.yaml
        tests/fixtures/swapi/vehicle.yaml
        tests/fixtures/swapi/planets.yaml
        tests/fixtures/swapi/reference.yaml
    """.split()

RESOURCES = {}


def load_yaml(path) -> dict:
    """Load yaml file and return dict.
    :param path: path to yaml file
    """
    with open(path) as fp:
        return yaml.safe_load(fp)


def retriever(uri: str):
    """Retrieve a resource from RESOURCES or the internet."""

    global RESOURCES
    if not RESOURCES:
        for path in SCHEMA_PATHS:
            name = pathlib.Path(path).name
            schema = load_yaml(path)
            RESOURCES[name] = schema

    if uri in RESOURCES:
        return RESOURCES[uri]

    return requests.get(uri).json()


def compile_schema(schema) -> Any:
    """Compile schema dict with $ref resolver"""
    return fastjsonschema.compile(schema, handlers={'': retriever, 'http': retriever, 'https': retriever})


def validate_hyper_schema(schema) -> dict:
    """Load yaml file for schema and ensure it is valid.
    :param schema: schema dict
    Raises exception if schema is not valid. (SchemaError, ValidationError
    """

    # validate it is a valid jsonschema
    return compile_schema(schema)


def type_is(property_, type_) -> bool:
    """Check if property[type] is of type_."""
    if "type" not in property_:
        return False
    if type_ == property_["type"]:
        return True
    if type_ in property_["type"]:
        return True
    return False


def test_validator():
    """Test the validator."""
    for path in SCHEMA_PATHS:
        print("Validating", path)
        schema = load_yaml(path)
        validate_hyper_schema(schema)
        print(f"\tOK {schema['title']} schema is valid")
        break


def test_valid_schemas():
    """Load yaml files for all schema and ensure it is valid."""

    for path in SCHEMA_PATHS:
        print("Validating", path)

        schema = load_yaml(path)
        validate_hyper_schema(schema)
        print(f"\tOK {schema['title']} schema is valid")

        # ensure that link rels are unique
        rel_names = [_['rel'] for _ in schema.get("links", [])]
        assert len(rel_names) == len(set(rel_names)), f"{schema['title']} has duplicate link rels"

        # ensure that every link is also a property
        for link in schema.get("links", []):
            assert link["rel"] in schema["properties"], f"{link['rel']} not in {schema['properties']}"

            print(f"\tOK {schema['title']} link.{link['rel']} has properties entry")

        # ensure that every link multiplicity is appropriate
        for link in schema.get("links", []):
            property_ = schema["properties"][link["rel"]]
            target_hints = link.get("targetHints", {})
            multiplicity = target_hints.get("multiplicity", "has_many")
            if multiplicity == "has_many":
                assert type_is(property_,
                               "array"), f"{link['rel']} has multiplicity has_many and therefore should be an array"
            elif multiplicity == "has_one":
                assert not type_is(property_, "array"), f"{link['rel']} has_one should not be an array"
            else:
                raise ValueError(f"Unknown multiplicity {multiplicity} for {link['rel']}")

            print(f"\tOK {schema['title']} link.{link['rel']} multiplicity to property type")


def test_instances():
    """Ensure sample instances are valid."""

    #     tests/fixtures/swapi/swapi_planets.ndjson association
    instances = """tests/fixtures/swapi/swapi_character.ndjson
    tests/fixtures/swapi/swapi_film.ndjson
    tests/fixtures/swapi/swapi_planet.ndjson
    tests/fixtures/swapi/swapi_species.ndjson
    tests/fixtures/swapi/swapi_starship.ndjson
    tests/fixtures/swapi/swapi_vehicle.ndjson
    tests/fixtures/swapi/swapi_planets.ndjson
    """.split()

    for path in instances:
        print(f"Validating instances in: {path}")
        with open(path) as fp:
            validate = None
            for line in fp:
                instance = json.loads(line)
                if validate is None:
                    _ = load_yaml(f"tests/fixtures/swapi/{instance['label'].lower()}.yaml")
                    validate = compile_schema(_)
                # print(f"\tvalidating:", instance)
                validate(instance)
                print(f"\tOK {instance['gid']} instance is valid")


def test_generate_links_from_instances():
    """Ensure we can generate links from instances + schemas, test links uniqueness."""

    instances = """tests/fixtures/swapi/swapi_character.ndjson
    tests/fixtures/swapi/swapi_film.ndjson
    tests/fixtures/swapi/swapi_planet.ndjson
    tests/fixtures/swapi/swapi_species.ndjson
    tests/fixtures/swapi/swapi_starship.ndjson
    tests/fixtures/swapi/swapi_vehicle.ndjson
    tests/fixtures/swapi/swapi_planets.ndjson
    """.split()

    for path in instances:
        print(f"Generating links for instances in: {path}")
        schema = None
        with open(path) as fp:
            for line in fp:
                instance = json.loads(line)
                schema = load_yaml(f"tests/fixtures/swapi/{instance['label'].lower()}.yaml")
                break

        with VertexLinkWriter(schema) as mgr:
            with open(path) as fp:
                for line in fp:
                    instance = mgr.insert_links(json.loads(line))

                    assert 0 < len(instance['links']), f"{instance['gid']} does not have at least one link"

                    assert all(['href' in _ and 'rel' in _ for _ in
                                instance['links']]), f"{instance['gid']} links do not have href and rel"

                    instance_links = [_['href'] for _ in instance['links']]
                    print(sorted(instance_links))
                    if len(sorted(instance_links)) != len(set(sorted(instance_links))):
                        print("?")
                    assert len(sorted(instance_links)) == len(set(sorted(instance_links))), f"{instance['gid']} has duplicate links {sorted(instance_links)}"
                    print(f"\tOK {instance['gid']} has {len(instance['links'])} links")


@pytest.mark.skip(reason="Use to create bundled json file")
def test_bundled():
    """Ensure we can bundle yaml files into a single json file."""

    bundle_schemas(pathlib.Path("tests/fixtures/swapi"), "http://bmeg-swapi/0.0.1", "graph-swapi.json")
    validate_hyper_schema(json.load(open("tests/fixtures/swapi/graph-swapi.json")))


@pytest.mark.skip(reason="Use to create edge json file")
def test_create_links():
    """Ensure we can create instances with links."""

    instances = """tests/fixtures/swapi/swapi_character.ndjson
    tests/fixtures/swapi/swapi_film.ndjson
    tests/fixtures/swapi/swapi_planet.ndjson
    tests/fixtures/swapi/swapi_species.ndjson
    tests/fixtures/swapi/swapi_starship.ndjson
    tests/fixtures/swapi/swapi_vehicle.ndjson
    tests/fixtures/swapi/swapi_planets.ndjson
    """.split()

    for path in instances:
        print(f"Generating links for instances in: {path}")
        schema = None
        with open(path) as fp:
            for line in fp:
                instance = json.loads(line)
                schema = load_yaml(f"tests/fixtures/swapi/{instance['label'].lower()}.yaml")
                break

        with VertexLinkWriter(schema) as mgr:
            output_path = path.replace(".ndjson", "-links.ndjson")
            with open(output_path, "w") as out_fp:
                with open(path) as fp:
                    for line in fp:
                        instance = mgr.insert_links(json.loads(line))
                        out_fp.write(json.dumps(instance) + "\n")
            assert os.path.exists(output_path), f"{output_path} does not exist"
