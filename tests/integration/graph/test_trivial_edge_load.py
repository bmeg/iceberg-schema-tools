from pydantic import ValidationError


def test_trivial_edge_load(fhir_schema, fhir_validator, edge_schemas):
    fail = False
    for edge in edge_schemas:
        try:
            fhir_validator.validate(
                {
                    "resourceType": edge['title'],
                    "source": {"reference": "Patient/1234"},
                    "target": {"reference": "Specimen/5678"},
                }
            )
        except ValidationError:
            fail = True
            print('  fail - fhir_schema should have validated edge with relative References', edge['title'])
        # print(f"ok {edge['title']}")
    if not fail:
        print('  ok - all edges validated correctly with relative References')
