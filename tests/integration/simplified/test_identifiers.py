from dictionaryutils import DataDictionary


def test_identifiers(data_dictionary_from_yaml: DataDictionary):
    """Schema has Gen3 friendly identifiers."""
    schemas = data_dictionary_from_yaml.schema
    for entity_name, schema in schemas.items():
        if 'properties' not in schema:
            continue
        if 'identifier' not in schema['properties']:
            continue
        assert schema['properties']['identifier']['items']['type'] == 'string', "identifiers type should be string"
