

def test_schema_load(fhir_schema, fhir_validator, vertex_schemas, edge_schemas):
    """Ensure whole schema can load"""
    assert 'DocumentReference' in fhir_schema['$defs']
    document_reference = fhir_schema['$defs']['DocumentReference']
    assert document_reference
    link_hrefs = set([_['href'].split('/')[0] for _ in document_reference['links']])
    out_of_scope = set([
        'RelatedPerson',
        'Practitioner',
        'PractitionerRole',
        'Organization'])
    assert (out_of_scope - link_hrefs) == out_of_scope, f"Did not expect {out_of_scope - link_hrefs}"
