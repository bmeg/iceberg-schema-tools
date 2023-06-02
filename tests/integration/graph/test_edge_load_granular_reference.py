from pydantic import ValidationError


def test_edge_load_granular_reference(fhir_schema, fhir_validator, edge_schemas):
    fail = False
    for edge in edge_schemas:
        try:
            fhir_validator.validate(
                {
                    "resourceType": edge['title'],
                    "source": {"type": "Patient", "identifier": {"value": "1234"}},
                    "target": {"type": "Specimen", "identifier": {"value": "5678"}},
                }
            )
        except ValidationError:
            fail = True
            print('fail - fhir_schema should have validated granular Reference', edge['title'])
        # print(f"ok {edge['title']}")
    if not fail:
        print('  ok - all edges validated correctly with type/identifier References')
