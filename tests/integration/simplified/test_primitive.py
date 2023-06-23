# disability_adjusted_life_years


def test_decimal(distribution_schema: dict):
    """Only json schema types should be used."""
    for entity_name, schema in distribution_schema.items():
        if 'properties' not in schema:
            continue
        if 'identifier' not in schema['properties']:
            continue
        for k, v in schema['properties'].items():
            if not isinstance(v, dict):
                continue
            assert v.get('type', None) != 'decimal', (schema['id'], k)


def test_code(distribution_schema: dict):
    """Only json schema types should be used."""
    for entity_name, schema in distribution_schema.items():
        if 'properties' not in schema:
            continue
        if 'identifier' not in schema['properties']:
            continue
        for k, v in schema['properties'].items():
            if not isinstance(v, dict):
                continue
            assert v.get('type', None) != 'code', (schema['id'], k)
