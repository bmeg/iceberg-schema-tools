
import yaml
from fhir.resources.specimen import Specimen

from iceberg_tools.graph import VertexSchemaLinks
from iceberg_tools.schema import _extract_schemas, BASE_URI


def test_specimen_links():
    """Ensure links are discovered from properties."""
    schemas = _extract_schemas([Specimen], BASE_URI)
    specimen_schema = VertexSchemaLinks(schemas['Specimen'])
    assert len(specimen_schema.schema['links']) == 21, ("Specimen should have 21 links", yaml.dump(specimen_schema.schema, sort_keys=False))
    actual_links = sorted([_['rel'] for _ in specimen_schema.schema['links']])
    expected_links = ['additive', 'authorReference_Organization', 'authorReference_Patient',
                      'authorReference_Practitioner', 'authorReference_PractitionerRole',
                      'authorReference_RelatedPerson', 'collector_Patient', 'collector_Practitioner',
                      'collector_PractitionerRole', 'collector_RelatedPerson', 'device', 'location',
                      'parent', 'procedure', 'request', 'subject_BiologicallyDerivedProduct',
                      'subject_Device', 'subject_Group', 'subject_Location', 'subject_Patient',
                      'subject_Substance']
    assert actual_links == expected_links, ("Specimen links should match", actual_links, expected_links)
