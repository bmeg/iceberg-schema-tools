from pydantic import ValidationError

from tests.integration.graph import is_edge


def test_negative_trivial_schema_load(fhir_schema, fhir_validator):
    """a negative test - all should fail"""

    for vertex_name in fhir_schema['$defs']:

        if not is_edge(fhir_schema['$defs'][vertex_name]):
            continue

        try:
            # a trivial instance example
            fhir_validator.validate(
                {"id": 1234, "resourceType": vertex_name},
            )
            raise Exception(f'!ok - {vertex_name} should have raised ValidationError')
        except ValidationError:
            pass

    print('  ok - caught invalid id')
