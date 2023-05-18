from dictionaryutils import DataDictionary


def test_keys(data_dictionary_from_yaml: DataDictionary):
    """Schema has Gen3 friendly identifiers."""
    schema = data_dictionary_from_yaml.schema
    assert all([_.islower() for _ in schema]), "All keys should be lowercase"
