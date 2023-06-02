from jsonschema.exceptions import ValidationError
from jsonschema.validators import Draft202012Validator, validate


def test_spot_check_embedded_type(fhir_schema, fhir_validator):
    """spot check an embedded type"""
    try:
        instance = {"id": "1234", "resourceType": "HumanName", "period": {"start": "1234"}}
        assert not validate(instance, fhir_schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
        print('  fail - fhir_schema period nonsense period invalid')
    except ValidationError as e:
        assert '1234' in e.message
        print('  ok - fhir_schema period nonsense period invalid correctly')

    try:
        instance = {"id": "1234", "resourceType": 'HumanName',
                    "period": {"start": "2023-01-01T00:00:00Z", "end": "2024-01-01T00:00:00Z"}}
        validate(instance, fhir_schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
        # print('ok - fhir_schema period valid period validated correctly')
    except ValidationError:
        print('  fail - fhir_schema valid period should have validated ', instance)

    print('  ok - all vertices validated correctly')
