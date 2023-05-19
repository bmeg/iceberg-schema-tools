def test_quantities(distribution_schema: dict):
    """Ensure that Quantities are rendered"""
    observation = distribution_schema['observation.yaml']
    expected_properties = ['valueQuantity', 'valueQuantity_unit', 'valueQuantity_value']
    for expected_property in expected_properties:
        assert expected_property in observation['properties'], f"Should have {expected_property}"
    assert observation['properties']['valueQuantity_value']['type'] == 'number'
