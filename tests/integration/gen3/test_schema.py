import fastjsonschema


def test_schema(distribution_schema):
    """Ensure the schema compiles as a legal json schema."""
    compiled_schema = fastjsonschema.compile(distribution_schema)
    assert compiled_schema
