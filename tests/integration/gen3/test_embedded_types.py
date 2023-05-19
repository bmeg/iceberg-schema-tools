
def test_embedded_types(distribution_schema: dict):
    """Ensure that subtypes are described as simple `string`"""
    patient = distribution_schema['patient.yaml']
    # lists
    assert patient['properties']['name']['items']['type'] == 'string'
    assert patient['properties']['address']['items']['type'] == 'string'
    # scalars
    condition = distribution_schema['condition.yaml']
    condition['properties']['encounter']['type'] == 'string'
