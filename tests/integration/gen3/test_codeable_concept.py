from dictionaryutils import DataDictionary


def test_codeable_concept(data_dictionary_from_yaml: DataDictionary):
    """Schema has Gen3 friendly CodeableConcept."""
    schemas = data_dictionary_from_yaml.schema
    condition = schemas['condition']
    code = condition['properties']['code']
    code_coding = condition['properties']['code_coding']
    category = condition['properties']['category']
    category_coding = condition['properties']['category_coding']
    verification_status = condition['properties']['verificationStatus']

    assert 'text representation' in code['description']
    assert 'text representation' in category['description']
    assert 'system#code representation' in code_coding['description']
    assert 'system#code representation' in category_coding['description']
    assert verification_status['binding_strength'] == 'required'
    assert verification_status['binding_uri']
