from jsonschema.exceptions import ValidationError
from jsonschema.validators import Draft202012Validator


def is_edge(schema) -> bool:
    """ Has an edge vocabulary?"""
    vocabulary_fields = [
        'source_property_name',
        'source_multiplicity',
        'destination_property_name',
        'destination_multiplicity',
        'label',
        'is_primary',
        'source_type',
        'destination_type',
    ]
    return all([f in schema for f in vocabulary_fields])


def edge_validator(validator: Draft202012Validator, edge):
    """Extra layer of validation, check both schema validation and vocabulary matching."""
    validator.validate(edge)
    sub_schema = validator.schema['$defs'][edge['resourceType']]
    if is_edge(sub_schema):
        expected_source_type = sub_schema['source_type']
        expected_destination_type = sub_schema['destination_type']
        source = edge['source']
        destination = edge['target']
        if 'reference' in source:
            actual_source_type = source['reference'].split('/')[0]
        else:
            assert 'type' in source, ('Edge.source needs reference or source', edge)
            actual_source_type = source['type']
        if 'reference' in destination:
            actual_destination_type = destination['reference'].split('/')[0]
        else:
            assert 'type' in destination, ('Edge.destination needs reference or source', edge)
            actual_destination_type = destination['type']
        if not actual_source_type == expected_source_type:
            raise ValidationError(f"{actual_source_type} does not match expected {expected_source_type}")
        if not actual_destination_type == expected_destination_type:
            raise ValidationError(f"{actual_destination_type} does not match expected {expected_destination_type}")
