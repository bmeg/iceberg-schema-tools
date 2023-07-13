import json

import yaml
from fhir.resources.specimen import Specimen

from iceberg_tools.graph import VertexSchemaDecorator, VertexLinkWriter, SchemaLinkWriter
from iceberg_tools.schema import extract_schemas, BASE_URI

EXPECTED_LINKS = ['collection_collector_Patient', 'collection_collector_Practitioner',
                  'collection_collector_PractitionerRole', 'collection_collector_RelatedPerson', 'collection_procedure',
                  'container_device', 'container_location', 'note_authorReference_Organization',
                  'note_authorReference_Patient', 'note_authorReference_Practitioner',
                  'note_authorReference_PractitionerRole', 'note_authorReference_RelatedPerson', 'parent',
                  'processing_additive', 'request', 'subject_BiologicallyDerivedProduct', 'subject_Device',
                  'subject_Group', 'subject_Location', 'subject_Patient', 'subject_Substance']


def test_specimen_schema_decorator():
    """Ensure links are discovered from properties."""
    schemas = extract_schemas([Specimen], BASE_URI)
    specimen_schema = VertexSchemaDecorator(schemas['Specimen'])
    assert len(specimen_schema.schema['links']) == 21, ("Specimen should have 21 links", yaml.dump(specimen_schema.schema, sort_keys=False))
    actual_links = sorted([_['rel'] for _ in specimen_schema.schema['links']])
    print(sorted(actual_links))
    assert actual_links == EXPECTED_LINKS, ("Specimen links should match", actual_links, EXPECTED_LINKS)


def test_vertex_link_writer_polymorphic():
    """Ensure links are discovered from properties. Use a context manager for throughput."""
    schemas = extract_schemas([Specimen], BASE_URI)
    specimen_schema = VertexSchemaDecorator(schemas['Specimen'])
    with VertexLinkWriter(specimen_schema) as mgr:
        for specimen in [
            {'id': 's-p1', 'resourceType': 'Specimen', 'subject': {'reference': 'Patient/p1'}},
            {'id': 's-d1', 'resourceType': 'Specimen', 'subject': {'reference': 'Device/d1'}},
            {'id': 's-g1', 'resourceType': 'Specimen', 'subject': {'reference': 'Group/g1'}}
        ]:
            specimen = mgr.insert_links(specimen)
            assert specimen['links'] is not None, "Links should be added to specimen"
            assert len(specimen['links']) > 0, "Links should be added to specimen"

            ref = specimen['subject']['reference']
            entity_type = ref.split('/')[0]
            assert specimen['links'][0] == {'rel': f'subject_{entity_type}', 'href': ref}, "Links should be added to specimen"


def test_vertex_link_writer_nested():
    """Ensure links are discovered from properties. Use a context manager for throughput."""
    schemas = extract_schemas([Specimen], BASE_URI)
    specimen_schema = VertexSchemaDecorator(schemas['Specimen'])

    with VertexLinkWriter(specimen_schema) as mgr:

        for specimen in [
            {"id": "s-processing-1", "resourceType": "Specimen", "processing": [{"additive": [{"reference": "Substance/sub-1"}]}]},
        ]:
            specimen = mgr.insert_links(specimen)

            assert specimen['links'] is not None, "Links should be added to specimen"
            assert len(specimen['links']) > 0, "Links should be added to specimen"

            print(json.dumps(specimen, indent=2))
            assert specimen['links'][0] == {'rel': 'processing_additive', 'href': specimen['processing'][0]['additive'][0]['reference']}, "Links should be added to specimen"

        for specimen in [
            {
                'id': 's-processing-1', 'resourceType': 'Specimen',
                "processing": [
                    {"additive": [{"reference": "Substance/sub-1"}]},
                    {"additive": [{"reference": "Substance/sub-2"}]}
                ]
            },
        ]:
            specimen = mgr.insert_links(specimen)

            assert specimen['links'] is not None, "Links should be added to specimen"
            assert len(specimen['links']) == 2, "Links should be added to specimen"

            for i in range(1):
                assert specimen['links'][i] == {'rel': 'processing_additive', 'href': specimen['processing'][i]['additive'][i]['reference']}, "Links should be added to specimen"


def test_schema_link_writer_nested():
    """Ensure links are discovered from schema. Use a context manager for throughput."""
    schemas = extract_schemas([Specimen], BASE_URI)
    specimen_schema = schemas['Specimen']

    with SchemaLinkWriter() as mgr:
        specimen_schema = mgr.insert_links(specimen_schema)
        assert specimen_schema['links'] is not None, "Links should be added to specimen"
        assert specimen_schema['properties']['links'] is not None, "Links should be added to specimen properties"
