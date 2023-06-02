from collections import defaultdict

from jsonschema.exceptions import ValidationError

from tests.integration.graph import edge_validator


def test_edge_validator(fhir_schema, fhir_validator, edge_schemas):

    for edge in edge_schemas:
        try:
            edge_validator(fhir_validator, {
                "resourceType": edge['title'],
                "source": {"type": "XXX", "identifier": {"value": "1234"}},
                "destination": {"type": "YYYY", "identifier": {"value": "5678"}},
            })
            assert False, ("Should not validate", edge)
        except ValidationError:
            pass
    print('  ok all invalid edges pass "extra" vocabulary validation')

    fail = False
    for edge in edge_schemas:
        instance = {
                "resourceType": edge['title'],
                "source": {"type": edge['source_type'], "identifier": {"value": "1234"}},
                "target": {"type": edge['destination_type'], "identifier": {"value": "5678"}},
            }
        try:
            edge_validator(fhir_validator, instance)
        except ValidationError:
            fail = True
            print(f"fail extra edge_validator {instance}")
    if not fail:
        print('  ok all valid edges pass "extra" vocabulary validation')

    print('count of primary edges:\n  ', len([edge for edge in edge_schemas if edge['is_primary']]))

    print('unresolved `Any` edge destinations:')
    needs_unresolved_primary = False
    for edge in edge_schemas:
        if edge['destination_type'] == 'Resource' and len([e for e in edge_schemas if e['source_type'] == edge['source_type']]) == 1:
            print('  ', edge['source_type']+'.'+edge['source_property_name'], edge['destination_type'])
            needs_unresolved_primary = True
    if not needs_unresolved_primary:
        print('  None')

    print('multi-edges (ie need `is_primary` manually set for uni-graphs (simplified)):')

    edge_counts = defaultdict(dict)
    for edge in edge_schemas:
        if edge['destination_type'] not in edge_counts[edge['source_type']]:
            edge_counts[edge['source_type']][edge['destination_type']] = False
        if not edge_counts[edge['source_type']][edge['destination_type']]:
            edge_counts[edge['source_type']][edge['destination_type']] = edge['is_primary']

    needs_is_primary = False
    for source_type in edge_counts:
        for destination_type in edge_counts[source_type]:
            if not edge_counts[source_type][destination_type]:
                if destination_type == 'Resource':
                    continue
                print(source_type, '->', destination_type)
                needs_is_primary = True

    if not needs_is_primary:
        print('  None')
