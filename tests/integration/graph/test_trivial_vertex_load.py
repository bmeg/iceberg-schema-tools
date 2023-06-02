from jsonschema.exceptions import ValidationError, UnknownType

from tests.integration.graph import is_edge


def test_trivial_schema_load(fhir_schema, fhir_validator):
    """Ensure whole schema can load"""
    for vertex_name in fhir_schema['$defs']:

        if not is_edge(fhir_schema['$defs'][vertex_name]):
            continue

        try:
            # a trivial instance example
            fhir_validator.validate(
                {"id": "1234", "resourceType": vertex_name},
            )
            # print(f'ok - {vertex_name} validated correctly')
        except ValidationError:
            # print(f'ok, expected error - {vertex_name}  {[c.message for c in e.context if c.schema["title"] == vertex_name]}')
            pass
        except UnknownType as e:
            print("!ok Houston we have a problem.  All types in $defs should have a schema.")
            raise e
