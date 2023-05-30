def test_specimen_plucked_properties(distribution_schema: dict):
    """Ensure that additive, method plucked from Specimen.processing."""
    specimen = distribution_schema['specimen.yaml']
    expected_properties = ['processing_additive', 'processing_method']
    for expected_property in expected_properties:
        assert expected_property in specimen['properties'], f"Should have {expected_property} {specimen['properties'].keys()}"
    assert 'Substance' in specimen['properties']['processing_additive']['enum_reference_types']
    assert 'http://hl7.org/fhir/ValueSet/specimen-processing-method' == specimen['properties']['processing_method']['binding_uri']
