import fastjsonschema
from iceberg_tools.schema.simplified_validator import ensure_schema


def test_schema(distribution_schema):
    """Ensure the schema compiles as a legal json schema."""
    compiled_schema = fastjsonschema.compile(distribution_schema)
    assert compiled_schema


def test_schema_load(distribution_schema_path):
    """Ensure we can load using dictionaryutils."""
    assert ensure_schema(schema_path=distribution_schema_path), f"should have loaded {distribution_schema_path}"
