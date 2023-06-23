import json
import logging
import pathlib

import yaml
logger = logging.getLogger(__name__)


def _bundle_schemas(output_path, base_uri) -> pathlib.Path:
    """Create a single uber schema in json with all """
    schemas = {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': base_uri,
        '$defs': {},
        'anyOf': []
    }

    for input_file in output_path.glob('*.yaml'):

        if input_file.stem.startswith('_'):
            continue

        with open(input_file) as fp:
            schema_str = fp.read()
            schema_str = schema_str.replace('.yaml', '').replace('$ref: ', f'$ref: {base_uri}/')
            schema = yaml.safe_load(schema_str)

            if 'title' not in schema:
                vertex = next(
                    iter([k for k in schema.keys() if not k.startswith('$') and k not in ['description', 'allOf']]), None)
                _ = schema
                schema = schema[vertex]

            assert 'title' in schema, schema
            schema['$id'] = f"{base_uri}/{schema['title']}"

            schemas['$defs'][schema['title']] = schema
            schemas['anyOf'].append({'$ref': f"{base_uri}/{schema['title']}"})

    path = output_path / pathlib.Path("graph-fhir.json")
    with open(path, "w") as fp:
        json.dump(schemas, fp, indent=2)

    return path
