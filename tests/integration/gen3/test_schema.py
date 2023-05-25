import fastjsonschema


def test_schema(distribution_schema):
    compiled_schema = fastjsonschema.compile(distribution_schema)
    assert compiled_schema
