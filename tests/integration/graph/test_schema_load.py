def test_schema_load(fhir_schema, fhir_validator, vertex_schemas, edge_schemas):
    """Ensure whole schema can load"""
    assert fhir_schema
    assert fhir_validator
    assert len(fhir_schema['$defs']) > 90, f"There are {len(fhir_schema['$defs'])} types."
    assert len(vertex_schemas) > 90
    assert len(edge_schemas) == 0
