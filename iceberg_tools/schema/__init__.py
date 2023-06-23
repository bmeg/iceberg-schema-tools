import copy
import importlib
import logging
import pathlib
import sqlite3
from collections import defaultdict
from typing import List

import inflection
import orjson
from fhir.resources.core.utils.common import get_fhir_type_name
from fhir.resources.fhirprimitiveextension import FHIRPrimitiveExtension

from iceberg_tools.schema.fhir_resources.binding_lookup import create_fhir_definitions_lookup


logger = logging.getLogger(__name__)

path = pathlib.Path("~/.iceberg").expanduser()
path.mkdir(parents=True, exist_ok=True)
path = path / "element_bindings.sqlite"
if not path.is_file():
    create_fhir_definitions_lookup()
if not path.is_file():
    logger.error(f"Unable to find fhir bindings at {path}")
    exit(2)

ELEMENT_DB = sqlite3.connect(path)
BASE_URI = 'http://graph-fhir.io/schema/0.0.2'


def _find_fhir_classes(gen3_config, log_stats=True) -> List[type]:
    """Based on config, expand dependencies."""

    class_names = [c for c in gen3_config['dependency_order'] if not c.startswith('_')]
    class_names = [c for c in class_names if c not in ['Program', 'Project']]

    subclass_depth = gen3_config.get('subclass_depth', 3)

    mod = importlib.import_module('fhir.resources')
    classes = set()
    for class_name in class_names:
        classes.add(mod.get_fhir_model_class(class_name))

    # find subclasses N levels deep
    # maintain statistics
    stats = defaultdict(int)

    for _ in range(subclass_depth):
        embedded_classes = set()
        for klass in classes:

            for p in klass.element_properties():
                try:

                    embedded_class = mod.get_fhir_model_class(get_fhir_type_name(p.type_))
                    embedded_classes.add(embedded_class)

                    _update_stats(stats, klass, embedded_class)

                except KeyError:
                    pass

        classes.update(embedded_classes)
    classes.add(FHIRPrimitiveExtension)

    if log_stats:
        logger.info(f"Class statistics number of nested objects:\n{_summarize_stats(stats)}")

    return classes


def _summarize_stats(stats: dict) -> str:
    """Summarize stats, counts of subclasses."""
    summary = {}
    for _ in stats:
        parts = _.split('.')
        klass_name = parts[0]
        if klass_name in ['Meta', 'Extension']:
            continue
        nested_class_count = len(parts[1:])
        total_property_counts = stats[_]
        summary[klass_name] = {'nested_class_count': nested_class_count, 'total_property_counts': total_property_counts}

    stats_table = '\n  '.join(sorted([f'{k}: {v}' for k, v in summary.items()]))
    return '  ' + stats_table


def _update_stats(stats: dict, klass, embedded_class):
    """Update stats for class and embedded class."""
    if embedded_class.__name__ in ['Meta', 'Extension']:
        return
    stat_property = f"{klass.__name__}.{embedded_class.__name__}"
    existing_stat_property = next(iter([k for k in stats.keys() if klass.__name__ in k]), None)
    if existing_stat_property:
        if embedded_class.__name__ not in existing_stat_property:
            property_count = stats[existing_stat_property]
            del stats[existing_stat_property]
            existing_stat_property += f".{embedded_class.__name__}"
            stats[existing_stat_property] = property_count + len(list(embedded_class.element_properties()))
    else:
        stats[stat_property] += 1


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

        schema['description'] += f" [See https://hl7.org/fhir/R5/{schema['title']}.html]"

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
