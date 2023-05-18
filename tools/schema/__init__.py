import copy
import importlib
import logging
import sqlite3
from collections import defaultdict
from typing import List

import inflection
import orjson
from fhir.resources.core.utils.common import get_fhir_type_name
from fhir.resources.fhirprimitiveextension import FHIRPrimitiveExtension

ELEMENT_DB = sqlite3.connect("resources/fhir/element_bindings.sqlite")
BASE_URI = 'http://bmeg.io/schema/0.0.2'

logger = logging.getLogger(__name__)


def _find_fhir_classes(gen3_config) -> List[type]:
    """Based on config, expand dependencies."""
    class_names = [c for c in gen3_config['dependency_order'] if not c.startswith('_')]
    class_names = [c for c in class_names if c not in ['Program', 'Project']]
    mod = importlib.import_module('fhir.resources')
    classes = set()
    for class_name in class_names:
        classes.add(mod.get_fhir_model_class(class_name))
    # find subclasses 3 levels deep
    for _ in range(3):
        embedded_classes = set()
        for klass in classes:
            for p in klass.element_properties():
                mod = importlib.import_module('fhir.resources')
                try:
                    embedded_class = mod.get_fhir_model_class(get_fhir_type_name(p.type_))
                    embedded_classes.add(embedded_class)
                except KeyError:
                    pass
        classes.update(embedded_classes)
        classes.add(FHIRPrimitiveExtension)
    return classes


def _extract_schemas(classes: List[type], base_uri: str) -> dict:
    """Get json schema for all classes."""
    schemas = {}
    for klass in classes:
        schema = klass.schema()
        assert 'title' in schema, schema
        schema['$id'] = schema['title']

        schema = _decorate_schema_bindings(schema)
        schema = _decorate_schema_backrefs(schema)

        schema['description'] = schema.get('description', '').replace('\n\n', '\n')
        schema['description'] = schema['description'].replace("""Disclaimer: Any field name ends with ``__ext`` doesn't part of\nResource StructureDefinition, instead used to enable Extensibility feature\nfor FHIR Primitive Data Types.\n""", '')
        schema['description'] = schema['description'].replace('\n', ' ')

        schema['description'] += f" [See https://hl7.org/fhir/R5/{schema['title']}]"

        # rename python style name back to resourceType
        if 'resource_type' in schema['properties']:
            schema['properties']['resourceType'] = schema['properties']['resource_type']
            schema['properties']['resourceType']['description'] = 'One of the resource types defined as part of FHIR'
            del schema['properties']['resource_type']
        # rename python reserved names
        if 'for' in schema['properties']:
            schema['properties']['for_fhir'] = copy.deepcopy(schema['properties']['for'])
            schema['properties']['for_fhir']['description'] = "[Reserved word `for` renamed to `for_fhir`] " + schema['properties']['for_fhir']['description']
            del schema['properties']['for']
        #
        # style as an anonymous schema
        #

        # rename type Resource to $ref
        for p_ in schema['properties'].values():
            if 'type' not in p_:
                continue
            if p_['type'][0].isupper():
                p_['$ref'] = f"{p_['type']}.yaml"
                del p_['type']
        for p_ in schema['properties'].values():
            if 'items' not in p_:
                continue
            if 'type' not in p_['items']:
                continue
            if p_['items']['type'][0].isupper():
                p_['items']['$ref'] = f"{p_['items']['type']}.yaml"
                del p_['items']['type']

        schemas[klass.__name__] = schema

    return schemas


def _decorate_schema_bindings(schema):
    """Supplement schema with bindings."""
    elements = {}
    klass = schema['title']
    with ELEMENT_DB:
        cursor = ELEMENT_DB.cursor()
        cursor.execute('select id, entity from element_bindings where id like ?;', (f"{klass}.%", ))
        for row in cursor.fetchall():
            elements[row[0]] = orjson.loads(row[1])
    if len(elements) == 0:
        return schema
    for property_name, property_ in schema['properties'].items():
        if f"{klass}.{property_name}" not in elements:
            continue
        element = elements[f"{klass}.{property_name}"]
        if 'binding' in element:
            binding = element['binding']
            property_['binding_strength'] = binding.get('strength', None)
            property_['binding_description'] = binding.get('description', None)
            if 'valueSet' in binding:
                uri = binding['valueSet']
                version = None
                if '|' in uri:
                    uri, version = binding['valueSet'].split('|')
                property_['binding_uri'] = uri
                property_['binding_version'] = version
    return schema


def _decorate_schema_backrefs(schema) -> dict:
    """Ensure references have a backref, if there are multiple edges between vertices, distinguish the backref name."""
    references = _scalar_of_type(schema, 'Reference')
    references.update(_scalar_of_type(schema, 'CodeableReference'))
    references.update(_list_of_type(schema, 'Reference'))
    references.update(_list_of_type(schema, 'CodeableReference'))
    targets_to_itemize = _targets_to_itemize(references)
    schema = _decorate_scalar_reference_backref(schema, targets_to_itemize)
    schema = _decorate_list_reference_backref(schema, targets_to_itemize)
    return schema


def _decorate_list_reference_backref(schema: dict, targets_to_itemize: list) -> dict:
    """Set backref in scalar Reference."""
    references = _list_of_type(schema, 'Reference')
    references.update(_list_of_type(schema, 'CodeableReference'))
    if len(references) == 0:
        return schema
    base_backref_name = inflection.underscore(schema['$id'])
    for k, v in references.items():
        backref = f"{k}_{base_backref_name}"
        v['backref'] = backref
    return schema


def _decorate_scalar_reference_backref(schema: dict, targets_to_itemize: list) -> dict:
    """Set backref in scalar Reference."""
    references = _scalar_of_type(schema, 'Reference')
    references.update(_scalar_of_type(schema, 'CodeableReference'))
    if len(references) == 0:
        return schema

    base_backref_name = inflection.underscore(schema['$id'])

    for k, v in references.items():
        enum_reference_types = set(v.get('enum_reference_types', []))
        backref = base_backref_name
        intersection = targets_to_itemize.intersection(enum_reference_types)
        if len(intersection) > 0:
            backref = f"{k}_{base_backref_name}"
            # logger.debug(f"backref: targets:{intersection} {backref}")
        v['backref'] = backref
    return schema


def _targets_to_itemize(references: dict) -> set:
    """Destination vertices with more than one edge."""
    target_counts = defaultdict(int)
    nestedlist = [v.get('enum_reference_types', []) for k, v in references.items()]
    targets = [element for sublist in nestedlist for element in sublist]
    for target in targets:
        target_counts[target] += 1
    targets_to_itemize = set([k for k, v in target_counts.items() if v > 1])
    return targets_to_itemize


def _is_list_of_type(property_: dict, type_: str) -> bool:
    """True if property is a list of type_."""
    if not _is_list_of_any(property_):
        return False
    items = property_.get('items', {})
    return items.get('type', None) == type_ or items.get('$ref', None) == f"{type_}.yaml"


def _is_list_of_any(property_: dict) -> bool:
    """True if property is a list."""
    if not isinstance(property_, dict):
        return False
    if property_.get('type', None) != 'array':
        return False
    items = property_.get('items', None)
    if items is None:
        return False
    items = property_.get('items', {})
    return items.get('type', 'xxx')[0].isupper() or items.get('$ref', 'xxx')[0].isupper()


def _scalar_of_type(schema: dict, type_: str) -> dict:
    """type_ in a scalar field"""
    if 'properties' not in schema:
        return {}
    references = {
        k: v for k, v in schema['properties'].items() if
        isinstance(v, dict) and (v.get('type', None) == type_ or v.get('$ref', None) == f"{type_}.yaml")
    }
    return references


def _list_of_type(schema: dict, type_: str) -> dict:
    """type_ in an array."""
    if 'properties' not in schema:
        return {}
    references = {k: v
                  for k, v in schema['properties'].items() if _is_list_of_type(v, type_)
                  }
    return references


def _list_of_any_type(schema: dict) -> dict:
    """type_ in an array."""
    if 'properties' not in schema:
        return {}
    references = {k: v
                  for k, v in schema['properties'].items() if _is_list_of_any(v)
                  }
    return references


def _scalar_of_any_type(schema: dict) -> dict:
    """Embedded refs"""
    if 'properties' not in schema:
        return {}
    references = {
        k: v for k, v in schema['properties'].items() if
        isinstance(v, dict) and ('.yaml' in v.get('type', '') or '.yaml' in v.get('$ref', ''))
    }
    return references
