import pathlib

from orjson import orjson

from iceberg_tools.graph import VertexLinkWriter


def test_add_links_to_fhir(fhir_schema):
    """Pluck out the links from the FHIR instance and add them to the graph instance.
    Runtime: 1m """

    # quick lookup for schema
    schema_lookup = {v['title']: v for v in fhir_schema['$defs'].values()}
    emitter_lookup = {v['title']: VertexLinkWriter(v) for v in fhir_schema['$defs'].values()}
    # TODO fhir_schema set CWD to iceberg - fix this
    study_path = '../../../tests/fixtures/simplify/study'
    for path in pathlib.Path(study_path).glob("*.bundle.json"):
        with open(path) as fp:
            # load bundle
            _ = orjson.loads(fp.read())
            for entry in _['entry']:
                # pluck out the resource
                resource = entry['resource']
                resource_type = resource['resourceType']
                # lookup the schema
                schema = schema_lookup.get(resource_type, None)
                assert schema is not None, (resource_type, schema_lookup.keys())
                # lookup the link writer
                link_writer = emitter_lookup.get(resource_type, None)
                assert link_writer is not None, (resource_type, link_writer.keys())
                # add the links
                resource = link_writer.insert_links(resource)
                # validate
                if 'links' in schema:
                    assert 'links' in resource
