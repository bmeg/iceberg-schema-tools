import copy
import logging
import pathlib
from collections import OrderedDict

import inflection
import requests
import requests_cache
import yaml
from yaml import SafeLoader

from iceberg_tools.schema import _list_of_type, _scalar_of_type, _list_of_any_type, _scalar_of_any_type

logger = logging.getLogger(__name__)

cache_path = pathlib.Path("~/.iceberg").expanduser()
cache_path.mkdir(parents=True, exist_ok=True)
cache_path = cache_path / "requests_cache"
requests_cache.install_cache(cache_path)


FHIR_PRIMITIVES_TO_JSON_SCHEMA = {
    "boolean": 'boolean',
    "string": 'string',
    "base64Binary": 'string',
    "code": 'string',
    "id": 'string',
    "decimal": 'string',
    "integer": 'number',
    "unsignedInt": 'number',
    "positiveInt": 'number',
    "uri": 'string',
    "oid": 'string',
    "uuid": 'string',
    "canonical": 'string',
    "url": 'string',
    "markdown": 'string',
    "xhtml": 'string',
    "date": 'string',
    "dateTime": 'string',
    "instant": 'string',
    "time": 'string'
}


def _simplify_schemas(gen3_config, gen3_fixtures, schemas):  # , edge_schemas
    """Make the schema Gen3 (data-frame) friendly."""

    # config_paths = gen3_config['paths']
    config_categories = gen3_config['categories']
    ignored_properties = gen3_config['ignored_properties']
    dependency_order = gen3_config['dependency_order']
    extra_properties = gen3_config['extra_properties']
    renamed_properties = gen3_config['renamed_properties']
    limit_links = gen3_config['limit_links']
    extensions = gen3_config['extensions']

    # delete vertices we don't want
    vertices_to_delete = set(schemas.keys()) - set(dependency_order)
    for k in vertices_to_delete:
        del schemas[k]

    _remove_required_flag(schemas)

    _ensure_description(schemas)
    _add_extra_properties(schemas, extra_properties)
    _rename_properties(schemas, renamed_properties)

    _add_gen3_schema_scaffolding(config_categories, schemas)
    _add_extensions(extensions, schemas)

    # do this before _remove_ignored_properties since we have dummy references in extra_properties
    _simplify_references(schemas, dependency_order, limit_links)
    _remove_ignored_properties(ignored_properties, schemas)
    _simplify_identifiers(schemas)
    _simplify_codeable_concepts(schemas)
    _simplify_quantities(schemas)

    _simplify_embedded_types(schemas)

    _add_gen3_static_dependencies(gen3_fixtures, schemas)

    # save gen3 schema in order
    dependency_order.extend(k for k in schemas if k not in dependency_order)

    # change to lowercase for gen3
    gen3_schema = {inflection.underscore(k).replace('.yaml', ''): schemas[k] for k in dependency_order if k in schemas}

    return gen3_schema


def _add_gen3_static_dependencies(gen3_fixtures, schemas):
    # add gen3 dependencies
    for fn in ["_definitions.yaml", "_terms.yaml", "_program.yaml", "_project.yaml", "_core_metadata_collection.yaml",
               "_settings.yaml"]:
        with open(gen3_fixtures / pathlib.Path(fn)) as fp:
            schemas[fn] = yaml.load(fp, SafeLoader)


def _add_extensions(extensions, schemas):
    """Add extensions to schema properties"""
    for k, schema in schemas.items():
        if 'properties' not in schema:
            continue
        if schema['title'] not in extensions:
            continue
        for extension in extensions[schema['title']]:
            # fetch url
            response = requests.get(extension)
            assert response.status_code == 200, ('Failed to fetch extension', extension, response.content)

            extension = requests.get(extension).json()
            extension_description = extension['description']
            # get parts
            elements = extension['snapshot']['element']
            # eg "Extension.extension:ombCategory.value[x]" -> ombCategory
            extension_elements = {_['id'].split(':')[-1].split('.')[0]: _ for _ in elements if
                                  'Extension.extension:' in _['id'] and '.value[x]' in _['id']}

            if len(extension_elements) == 0:
                extension_elements = {'': _ for _ in elements if
                                      'Extension.value[x]' == _['id']}
            assert len(extension_elements) > 0, ('Could not find values in extension', extension)
            extension_name = extension['id'].replace('-', '_')

            for element_name, element in extension_elements.items():
                type_ = element['type'][0]['code']
                # https://github.com/nazrulworld/fhir.resources/blob/02b04257dfe2f956fb2c7825624da50f8a464afd/fhir/resources/fhirtypes.py#L33
                if type_[0].isupper():
                    type_ = ('$ref', f"{type_}.yaml")
                else:
                    assert type_ in FHIR_PRIMITIVES_TO_JSON_SCHEMA, f"Unknown FHIR primitive: {type_}"
                    type_ = FHIR_PRIMITIVES_TO_JSON_SCHEMA[type_]
                    type_ = ('type', type_)
                property_type = type_
                property_items = None
                if element.get('max', None) == '*':
                    property_items = property_type
                    property_type = ('type', 'array')
                property_ = {
                    'description': f"[extension {extension_name}] {extension_description}",
                    property_type[0]: property_type[1]
                }

                if property_items:
                    property_['items'] = property_items
                binding = element.get('binding', None)
                if binding:
                    property_['binding_strength'] = binding['strength']
                    property_['binding_description'] = binding.get('description', None)
                    if 'valueSet' in binding:
                        uri = binding['valueSet']
                        version = None
                        if '|' in uri:
                            uri, version = binding['valueSet'].split('|')
                        property_['binding_uri'] = uri
                        property_['binding_version'] = version
                property_name = f"{extension_name}_{element_name}"
                if len(element_name) == 0:
                    property_name = extension_name

                _add_term_def(property_)
                _add_enum(property_)
                schema['properties'][property_name] = property_
            logger.info(f"Added extension: {extension_name}")


def _add_gen3_schema_scaffolding(config_categories, schemas):
    """add gen3 boilerplate to individual schemas"""
    for k, schema in schemas.items():
        if 'properties' not in schema:
            # print(f"No properties in {k}")
            continue

        # add boiler plate
        schema["program"] = "*"
        schema["project"] = "*"
        schema["additionalProperties"] = True
        schema["category"] = config_categories.get(schema['title'], 'Clinical')

        # rename $id to id, make it lowercase since Peregrine does not quote table names
        if '$id' in schema:
            schema['id'] = inflection.underscore(schema['$id'])
            del schema['$id']


def _simplify_identifiers(schemas: dict):
    """Transform identifiers to a list of strings"""
    for schema in schemas.values():
        if 'properties' not in schema:
            continue
        if 'identifier' not in schema['properties']:
            continue
        schema['properties']['identifier']['items']['type'] = 'string'
        del schema['properties']['identifier']['items']['$ref']

        identifier_text_coding = copy.deepcopy(schema['properties']['identifier'])
        identifier_text_coding['description'] = "[system#code representation of identifier.text] " + identifier_text_coding['description']
        schema['properties']['identifier_text_coding'] = identifier_text_coding

        identifier_coding = copy.deepcopy(schema['properties']['identifier'])
        identifier_coding['description'] = "[system#code representation of identifier] " + identifier_coding['description']
        schema['properties']['identifier_coding'] = identifier_coding


def _add_term_def(property_: dict):
    """Add Gen3 termDef"""
    if 'binding_uri' not in property_:
        return
    property_['term'] = {
        'description': property_.get('binding_description', ''),
        'termDef': {
            'cde_id': property_['binding_uri'],
            'term': property_['binding_uri'],
            'term_url': property_['binding_uri'],
            'cde_version': None,
            'source': 'fhir',
            'strength': property_['binding_strength']
        }
    }


def _add_enum(property_):
    """If required binding strength, set enum"""
    if 'enum_values' in property_:
        if property_['binding_strength'] == 'required':
            property_['enum'] = property_['enum_values']
        else:
            description_addendum = property_['binding_strength'] + '\n- '.join(property_['enum_values'])
        if 'description' in property_:
            property_['description'] += description_addendum


def _adjust_description(property_):

    if 'enum_values' in property_:
        if property_['binding_strength'] != 'required':
            description_addendum = property_['binding_strength'] + '\n- '.join(property_['enum_values'])
            if 'description' in property_:
                property_['description'] += description_addendum


def _add_coding(schema, name, property_):
    """Creates a new property with coding suffix."""
    coding_name = f"{name}_coding"
    coding_property = copy.deepcopy(property_)
    coding_property['description'] = f"[system#code representation.] {coding_property['description']}"
    schema['properties'][coding_name] = coding_property

    text_name = f"{name}_text"
    text_property = copy.deepcopy(property_)
    text_property['description'] = f"[text representation.] {coding_property['description']}"
    schema['properties'][text_name] = coding_property


def _simplify_codeable_concepts(schemas: dict):
    """Transform CodeableConcept."""
    for schema in schemas.values():

        # adjust lists of CodeableConcept
        codeable_concepts = _list_of_type(schema, 'CodeableConcept')
        codeable_concepts.update(_list_of_type(schema, 'CodeableReference'))
        for name, property_ in codeable_concepts.items():
            _add_term_def(property_)
            _add_enum(property_)
            _adjust_description(property_)

            del property_['items']['$ref']
            property_['items']['type'] = 'string'

            _add_coding(schema, name, property_)
            property_['description'] = f"text representation. {property_['description']}"

        # adjust scalars of CodeableConcept
        codeable_concepts = _scalar_of_type(schema, 'CodeableConcept')
        codeable_concepts.update(_scalar_of_type(schema, 'CodeableReference'))
        for name, property_ in codeable_concepts.items():
            _add_term_def(property_)
            _add_enum(property_)
            _adjust_description(property_)

            del property_['$ref']
            property_['type'] = 'string'

            _add_coding(schema, name, property_)
            property_['description'] = f"text representation. {property_['description']}"


def _simplify_quantities(schemas: dict):
    """Transform Quantity."""
    for schema in schemas.values():

        # adjust lists of Quantity
        codeable_concepts = _list_of_type(schema, 'Quantity')
        for name, property_ in codeable_concepts.items():
            property_['description'] = f"text representation. {property_['description']}"
            property_['items']['type'] = 'string'
            del property_['items']['$ref']

        # adjust scalars of CodeableConcept
        codeable_concepts = _scalar_of_type(schema, 'Quantity')
        for name, property_ in codeable_concepts.items():

            # separate into _unit, value
            schema['properties'][f"{name}_unit"] = {'type': 'string', 'title': f"Unit representation. {property_['title']}"}
            schema['properties'][f"{name}_value"] = {'type': 'number', 'title': f"Numerical value (with implicit precision) representation. {property_['title']}"}

            property_['description'] = f"text representation. {property_['description']}"


# def _simplify_coding(schemas):
#     """Transform Coding."""
#     for schema in schemas.values():
#         codings = _list_of_type(schema, 'Coding')
#         if len(codings) > 0:
#             print()
#         codings = _scalar_of_type(schema, 'Coding')
#         if len(codings) > 0:
#             print()

def _simplify_embedded_types(schemas):
    """Any remaining embedded types are simply rendered as strings."""
    for schema in schemas.values():
        lists_of_any = _list_of_any_type(schema)
        for name, property_ in lists_of_any.items():
            property_['description'] = f"[Text representation of {property_['items']['$ref'].replace('.yaml', '')}] {property_['description']}"
            property_['items']['type'] = 'string'
            del property_['items']['$ref']
        scalars_of_any = _scalar_of_any_type(schema)
        for name, property_ in scalars_of_any.items():
            property_['description'] = f"[Text representation of {property_['$ref'].replace('.yaml', '')}] {property_['description']}"
            property_['type'] = 'string'
            del property_['$ref']


def _ensure_description(schemas):
    """Every property has a description"""
    for schema in schemas.values():
        for name_, property_ in schema['properties'].items():
            if 'description' not in property_:
                property_['description'] = property_.get('title', '')


def _remove_ignored_properties(ignored_properties, schemas):
    """Trim ignored properties"""
    for schema in schemas.values():
        properties_to_delete = []
        for name_, property_ in schema['properties'].items():
            if name_ in ignored_properties or name_.startswith('_'):
                properties_to_delete.append(name_)
                continue
        for name_ in properties_to_delete:
            del schema['properties'][name_]


def _simplify_references(schemas: dict, dependency_order: list, limit_links: dict) -> dict:
    """Add links or render as string"""
    for schema in schemas.values():
        if 'properties' not in schema:
            continue

        links_to_add = OrderedDict()

        permitted_destinations = None
        if schema['title'] in limit_links:
            permitted_destinations = limit_links[schema['title']]

        # give priority to subject link
        names = list(schema['properties'].keys())
        if 'subject' in names:
            names.insert(0, names.pop(names.index('subject')))

        for name_ in names:
            property_ = schema['properties'][name_]
            if not isinstance(property_, dict):
                continue
            type_ = property_.get('type', None)
            if type_ and type_ != 'array':
                continue
            ref = property_.get('$ref', None)
            items_ref = property_.get('items', {}).get('$ref', None)

            if ref in ['CodeableReference.yaml', 'Reference.yaml'] or items_ref in ['CodeableReference.yaml',
                                                                                    'Reference.yaml']:
                links_to_add[name_] = property_

        links = []
        targets = {}
        delete_from_properties = []
        for name_, property_ in links_to_add.items():
            if 'enum_reference_types' not in property_:
                logger.warning(
                    f"{schema['title']}.{name_} has no defined targets, "
                    "i.e a Reference->Any.  Not supported by Gen3. Skipping."
                )
                continue

            multiple_targets = len(property_['enum_reference_types']) > 1
            for reference_type in property_['enum_reference_types']:
                # is the reference in scope
                assert 'backref' in property_, (f"{schema['title']}_{name_}", property_)
                if reference_type not in dependency_order:
                    logger.debug(f"Out of scope Reference {schema['title']}_{name_}_{reference_type}_{property_['backref']}")
                    continue
                if permitted_destinations and reference_type not in permitted_destinations:
                    logger.info(f"Edge destination suppressed: {schema['title']}.{name_} -> {reference_type}")
                    continue

                target_type = inflection.underscore(reference_type)
                label = f"{schema['title']}_{name_}_{reference_type}_{property_['backref']}"
                if target_type in targets:
                    logger.warning(f"{schema['title']} already has link to {target_type} via {targets[target_type]}. "
                                   f"Therefore ignoring: {label}")
                    continue
                link_name = name_
                if multiple_targets:
                    link_name = f"{name_}_{reference_type}"
                links.append({
                    'backref': property_['backref'],
                    'label': label,
                    'multiplicity': 'many_to_many',
                    'name': link_name,
                    'required': False,
                    'target_type': target_type
                })
                targets[target_type] = label
                delete_from_properties.append(name_)

        # # remove link from property dict
        # for name_ in set(delete_from_properties):
        #     del schema['properties'][name_]

        schema['links'] = links


def _add_extra_properties(schemas, extra_properties):
    """Add any additional properties."""
    for schema in schemas.values():
        if 'properties' not in schema:
            continue

        if schema['title'] in extra_properties:
            for snippet_key, snippet_value in extra_properties[schema['title']].items():
                schema['properties'][snippet_key] = snippet_value

        schema['properties']['project_id'] = {
            'type': 'string',
            'term': {
                '$ref': "_terms.yaml#/project_id"
            }
        }


def _remove_required_flag(schemas):
    """Remove required items, if the required item is a sub resource"""
    for schema in schemas.values():
        if 'properties' not in schema:
            continue
        if 'required' not in schema:
            continue
        for required_name in [_ for _ in schema['required']]:
            required_property = schema['properties'][required_name]
            # print(schema['title'], required_name, required_property)
            if '$ref' in required_property:
                # print('removing required flag', schema['title'], required_name, required_property['$ref'])
                schema['required'].remove(required_name)
            if 'items' in required_property and '$ref' in required_property['items']:
                # print('removing required flag', schema['title'], required_name, required_property['items']['$ref'])
                schema['required'].remove(required_name)
        if len(schema['required']) == 0:
            del schema['required']


def _rename_properties(schemas, renamed_properties):
    """Rename properties."""
    for schema in schemas.values():
        if 'properties' not in schema:
            continue
        names = list(schema['properties'].keys())
        for old_name, new_name in renamed_properties.items():
            if old_name in names:
                schema['properties'][new_name] = schema['properties'][old_name]
                del schema['properties'][old_name]
                logger.info(f"Renamed {schema['title']}.{old_name} to {new_name}")
