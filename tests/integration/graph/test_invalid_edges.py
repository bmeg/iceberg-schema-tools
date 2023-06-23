from jsonschema.exceptions import ValidationError


def test_invalid_edges(fhir_schema, fhir_validator, edge_schemas):
    invalid_edges = [
        # missing resourceType
        {
            "source": {"type": "Patient", "identifier": {"value": "1234"}},
            "destination": {"type": "Specimen", "identifier": {"value": "5678"}},
        },
        # missing source
        {
            "resourceType": 'Observation_performer_Patient',
            "destination": {"type": "Specimen", "identifier": {"value": "5678"}},
        },
        # missing destination
        {
            "resourceType": 'Observation_performer_Patient',
            "source": {"type": "Patient", "identifier": {"value": "1234"}},
        },
        # invalid source reference
        {
            "resourceType": 'Observation_performer_Patient',
            "source": {"foo"},
            "destination": {"type": "Specimen", "identifier": {"value": "5678"}},
        },
        # invalid destination reference
        {
            "resourceType": 'Observation_performer_Patient',
            "source": {"type": "Patient", "identifier": {"value": "1234"}},
            "destination": {"foo"},
        },
    ]

    for edge in invalid_edges:
        try:
            fhir_validator.validate(edge)
            assert False, ("Should not validate", edge)
        except ValidationError:
            pass

    print('  ok - all invalid edges validated correctly')
