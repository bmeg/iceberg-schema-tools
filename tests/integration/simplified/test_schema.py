import fastjsonschema
from iceberg_tools.schema.simplified_validator import ensure_schema


def test_schema(distribution_schema):
    """Ensure the schema compiles as a legal json schema."""
    compiled_schema = fastjsonschema.compile(distribution_schema)
    assert compiled_schema


def test_schema_load(distribution_schema_path):
    """Ensure we can load using dictionaryutils."""
    assert ensure_schema(schema_path=distribution_schema_path), f"should have loaded {distribution_schema_path}"


def test_schema_denormalized_fields(distribution_schema_path):
    """Ensure specimen and document_reference have _identifier denormalized fields."""
    schema = ensure_schema(schema_path=distribution_schema_path)
    assert schema, f"should have loaded {distribution_schema_path}"

    properties = schema['specimen']['properties']
    for _ in ['patient_identifier']:
        assert _ in properties, f"should have denormalized field {_}"

    properties = schema['document_reference']['properties']
    for _ in ['patient_identifier', 'specimen_identifier', 'task_identifier']:
        assert _ in properties, f"should have denormalized field {_}"

    properties = schema['observation']['properties']
    for _ in ['patient_identifier', 'specimen_identifier', 'condition_identifier']:
        assert _ in properties, f"should have denormalized field {_}"
