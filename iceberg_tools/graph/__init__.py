import importlib
import json
from string import Formatter
from typing import List, Iterator, Callable
from glom import glom, PathAccessError, flatten

import fastjsonschema
import jsonschema
import requests
import re
from jsonpointer import resolve_pointer

from iceberg_tools.schema import extract_schemas, BASE_URI

NESTED_OBJECTS_IGNORE = ['Identifier', 'Extension']


class RefFinder:
    """
    For returning a list of paths to schema refs

    Parameters:
        schema: the json schema object to be traversed
        refs: a flag that decides wether Reference.yaml refs will be collected
                or if every other ref will be collected
    Returns:
        list: A list of glom paths to schema refs
    """
    def __init__(self, schema, refs, nested_objects=None):
        self.schema = schema
        self.refs = refs
        self.nested_objects = nested_objects or []

    def getpath(self, data, path):
        """Reassign schema data dict to the new index path of every key in new_path"""
        for key in path:
            data = data[key]
        return data

    def traverse(self, path, data):
        """Traverse through a schema collecting a list of glom $ref paths"""
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = path + [key]
                if key == "$ref":
                    ref_value = self.getpath(self.schema, new_path[:-1])[key]
                    if (ref_value != "Reference.yaml" and not self.refs) or (ref_value == "Reference.yaml" and self.refs):
                        self.nested_objects.append(".".join(map(str, new_path)))
                self.traverse(new_path, value)
        elif isinstance(data, list):
            for index, value in enumerate(data):
                new_path = path + [index]
                self.traverse(new_path, value)

    def find_refs(self):
        """Calling function kickcs off schema traversal"""
        self.traverse([], self.schema)
        return self.nested_objects


def _extract_target_hints(schema_link):
    """Retrieve attributes from targetHints, using defaults."""
    target_hints = schema_link.get('targetHints', {})
    multiplicity = next(iter(target_hints.get('multiplicity', [])), 'has_many')
    directionality = next(iter(target_hints.get('directionality', [])), 'one')
    association = next(iter(target_hints.get('association', [])), False)
    return directionality, multiplicity, association


def _generate_links_from_fhir_references(schema, classes) -> List[dict]:
    """Generate links for a schema.

    Parameters
        schema: a schema dict
        classes: a list of types
    Returns:
        tuple: (links, nested_links)
    """

    # Direct links from {schema['title']}"
    links = []
    links.extend(_extract_links(schema, classes))

    # Nested links
    nested_links = []
    for nested_schema, path in _extract_nested_schemas(schema):
        if nested_schema['title'] in NESTED_OBJECTS_IGNORE:
            continue
        extracted_links = _extract_links(nested_schema, classes)
        if len(extracted_links) == 0:
            continue

        path_parts = path.split('.')
        parent_path = '.'.join(path_parts[1:-1]).replace('.items', '.-')

        for _ in extracted_links:
            _['$comment'] = f"From {nested_schema['title']}/{parent_path.replace('.-', '')}"
            _['templatePointers'] = {"id": f"/{parent_path.replace('.', '/')}{_['templatePointers'][tp]}" for tp in _['templatePointers']}
            _['rel'] = f"{parent_path.replace('.-', '')}_{_['rel']}"
        nested_links.extend(extracted_links)

    return links, nested_links


def _extract_nested_schemas(schema) -> Iterator[tuple[dict, str]]:
    """Extract $ref from elements in schema that are not `References`.

    Returns: (sub_schema, path) a tuple of the sub schema and the path to it in the passed schema
    """
    refs_finder = RefFinder(schema, refs=False)
    matches = sorted(refs_finder.find_refs())

    mod = importlib.import_module('fhir.resources')
    for match in matches:
        if match.startswith('properties.links') or match.startswith('links'):
            continue
        property_name = match.split('.')[1]
        if property_name.startswith('_'):
            continue

        property_ = schema['properties'][property_name]

        multiplicity = 'has_one'
        if 'items' in property_:
            multiplicity = 'has_many'

        if multiplicity == 'has_many':
            target = property_['items']['$ref'].split('.')[0]
        else:
            assert '$ref' in property_, ("TODO no $ref?", property_name, property_, match)
            target = property_['$ref'].split('.')[0]

        target_class = mod.get_fhir_model_class(target)
        sub_schemas = extract_schemas([target_class], BASE_URI)
        sub_schema = sub_schemas[target]

        yield sub_schema, match


def _extract_links(schema: dict, classes) -> List[dict]:
    """Extract Link Description Object (LDO) from a schema.

    see https://json-schema.org/draft/2019-09/json-schema-hypermedia.html#rfc.section.6
    """
    refs_finder = RefFinder(schema, refs=True)
    matches = sorted(refs_finder.find_refs())

    # filter out only the matches that link property references
    matches = [match for match in matches if match.startswith("properties.")]
    links = []
    for match in matches:
        direction = 'outbound'
        multiplicity = 'has_one'
        if 'items' in match:
            multiplicity = 'has_many'
        property_name = match.split('.')[1]
        property_ = schema['properties'][property_name]
        if 'enum_reference_types' not in property_:
            property_['enum_reference_types'] = ['__ANY__']
        append_postscript = len(property_['enum_reference_types']) > 1
        _path = '.'.join(match.split('.')[1:-1])
        _path = _path + '.reference'
        _path = _path.replace('.items', '.-')

        _class_names = [_.__name__ for _ in classes]

        for enum_reference_type in property_['enum_reference_types']:
            if enum_reference_type not in _class_names:
                print(f"DEBUG: {enum_reference_type} not in scope, skipping link {schema['$id']}->{enum_reference_type}")
                continue
            rel = f"{property_name}"
            if append_postscript:
                rel += f"_{enum_reference_type}"
            links.append(
                {
                    "rel": rel,
                    "href": f"{enum_reference_type}/{{id}}",
                    "templateRequired": ["id"],
                    "targetHints": {
                        "multiplicity": [multiplicity],
                        "direction": [direction],
                        'backref': [property_['backref']],
                    },
                    "templatePointers": {
                        'id': "/" + _path.replace('.', '/')
                    },
                    'targetSchema': {'$ref': enum_reference_type + '.yaml'},
                }
            )
    return links


def _load_schema(schema) -> dict:
    """Load JSON schema from dict or string."""
    if isinstance(schema, str):
        schema_ = requests.get(schema).json()
    elif isinstance(schema, dict):
        schema_ = schema
    else:
        raise ValueError("Schema must be a URL or a dict")
    return schema_


def fastjsonschema_compile(schema: dict, formats: dict = {}) -> Callable:
    """Compile a JSON schema, explicitly provide handlers."""

    def _handler(uri):
        """Resolve $ref to $id"""
        for _def in schema['$defs'].values():
            if _def['$id'] == uri:
                print(f"Found {uri}")
                return _def
        print(f"Could not find {uri}")

    def _https_handler(uri):
        # ‘https://json-schema.org/draft/2020-12/links’  hosted by cloudflare
        # see  https://github.com/IATI/IATI-Standard-Website/issues/230
        import urllib.request
        req = urllib.request.Request(
            uri,
            data=None,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            }
        )
        f = urllib.request.urlopen(req)
        _ = f.read().decode('utf-8')
        return json.loads(_)

    compiled_schema = fastjsonschema.compile(
        schema,
        formats=formats,
        handlers={'http': _handler, 'https': _https_handler},
    )
    return compiled_schema


class AssociationSchema:
    """A JSON schema for an association."""

    def __init__(self, schema):
        """Load and compile a JSON schema."""
        if isinstance(schema, str):
            self.schema = requests.get(schema).json()
        elif isinstance(schema, dict):
            self.schema = schema
        else:
            raise ValueError("Schema must be a URL or a dict")
        self.compiled_schema = fastjsonschema_compile(self.schema)

    def validate(self, instance: dict) -> dict:
        """Validate data against schema.

        Args:
            instance: instance of data to validate
        Returns:
            dict: potentially modified instance
        """
        return self.compiled_schema(instance)

    @classmethod
    def is_association(cls, schema: dict) -> bool:
        """Is this schema an association?"""
        if 'links' not in schema:
            return False
        for _ in schema['links']:
            _, _, association = _extract_target_hints(_)
            if association:
                return True
        return False

    @classmethod
    def validate_schema_conventions(cls, schema: dict) -> bool:
        """Validate schema."""
        assert 'links' in schema, 'Schema should have links'
        assert len(schema['links']) >= 2, "Association schema should have at least two links"
        assert cls.is_association(schema), "Schema links should be an association"
        assert 'title' in schema, "Schema should have a title"
        return True

    def validate_links(self, instance: dict):
        """Validate instance.links against schema.links"""

        # verify that all links in instance are in schema
        schema_relationships = [_['rel'] for _ in self.schema['links']]
        for link in instance['links']:
            assert link['rel'] in schema_relationships, f"Instance of this association should have links to {schema_relationships}"

        return instance


class AssociationInstance:

    def __init__(self, association_schema: AssociationSchema, instance: dict = None, vertex_a: dict = None, vertex_b: dict = None):
        """Operate on json document in the context of an association schema.

        Parameters:
            association_schema: an AssociationSchema object
            instance: an instance of a JSON document that should conform to the association schema
            vertex_a: a vertex that should be associated
            vertex_b: a vertex that should be associated
        """
        self.instance = instance
        self.association_schema = association_schema
        self.regexp_cache = {}
        self.href_keys_cache = {}
        if instance is None:
            assert vertex_a is not None and vertex_b is not None, "Must provide instance or vertex_a and vertex_b"
            self.instance = self._create_instance(vertex_a, vertex_b)

    def __repr__(self):
        """Return a string representation of the instance links of the form V(id).backref<--Title-->V(id).backref"""
        parts = self.edge_parts()
        label = parts['label']

        # formulate a representation of the edge's vertices
        rels = [_ for _ in parts if _ != 'label']
        msgs = []
        for rel in rels:
            _ = parts[rel]
            msgs.append(f"{_['targetSchema']}({_[_['id_name']]}).{rel}")

        return f"{msgs[0]}<-{label}->{msgs[1]}"

    def _create_instance(self, vertex_a, vertex_b):
        """Create an instance of an association from two vertices."""
        links = []
        for schema_link, vertex in list(zip(self.association_schema.schema['links'], [vertex_a, vertex_b])):
            keys = self._extract_href_keys(schema_link['href'])
            values = [resolve_pointer(vertex, _) for _ in schema_link['templatePointers'].values()]
            links.append(
                {
                    'rel': schema_link['rel'],
                    'href': schema_link['href'].format(**dict(zip(keys, values))),
                }
            )
        return {
            'links': links
        }

    def _extract_href_keys(self, href):
        """Extract the keys from the href template, cache the result."""
        keys = self.href_keys_cache.get(href, None)
        if not keys:
            keys = [_[1] for _ in Formatter().parse(href)]
            self.href_keys_cache[href] = keys
        return keys

    def _extract_id(self, schema_href, instance_href) -> str:
        """Read the id from the href template."""
        rexp = self.regexp_cache.get(schema_href, None)
        if rexp is None:
            _ = schema_href
            keys = self._extract_href_keys(schema_href)
            for key in keys:
                _ = _.replace(f"{{{key}}}", '(.*)')
            rexp = re.compile(_)
            self.regexp_cache[schema_href] = rexp
        m = rexp.match(instance_href)
        assert m is not None, f"Unable to find id in instance link {instance_href} given schema {schema_href}"
        return m.group(1), self._extract_href_keys(schema_href)[0]

    def edge_parts(self):
        """Decompose the edge into its parts."""

        title = self.association_schema.schema['title']
        parts = {'label': title}

        for link in self.association_schema.schema['links']:
            _ = self._extract_link_parts(link, self.instance)
            parts[_['rel']] = _

        return parts

    def _extract_link_parts(self, schema_link: dict, instance: dict) -> dict:
        """Extract the parts of a link from the schema and instance."""
        instance_link = next(iter([_ for _ in instance['links'] if _['rel'] == schema_link['rel']]), None)

        id_, id_name = self._extract_id(schema_link['href'], instance_link['href'])

        directionality, multiplicity, _ = _extract_target_hints(schema_link)

        return {
            id_name: id_,
            'rel': schema_link['rel'],
            'targetSchema': schema_link['targetSchema']['$ref'],
            'multiplicity': multiplicity,
            'directionality': directionality,
            'id_name': id_name,
        }


class VertexSchemaDecorator:
    """Adds links to vertex schema."""

    def __init__(self, schema: dict, classes: list):
        """Load and compile a JSON schema."""
        self.schema = _load_schema(schema)
        # add links property
        self.schema['properties']['links'] = {
            'links': {
                'type': 'array',
                'items': {
                    '$ref': 'https://json-schema.org/draft/2020-12/links'
                }
            }
        }
        # add links element
        links, nested_links = _generate_links_from_fhir_references(schema, classes)
        self.schema['links'] = links + nested_links
        # check schema
        jsonschema.Draft202012Validator.check_schema(schema)   # Draft202012Validator.check_schema(schema)


def cast_json_pointer_to_glom(_):
    """Convert a JSON pointer to a glom query.
    turn the pointer into a glom expression, note the leading dot and `-` for lists
    refer to https://glom.readthedocs.io/en/latest/api.html#glom.glom
    """
    _ = _.replace('/', '', 1).replace('/', '.').replace('-', '*')
    return _


class VertexLinkWriter:
    """Context manager for inserting links into vertices."""

    def __init__(self, schema: dict):
        """Initialize the context manager.

        Parameters:
            schema: a schema
        """
        self.vertex_schema = schema
        self.href_keys_cache = {}
        self.glom_cache = {}
        self.regexp_cache = {}

    def _extract_href_keys(self, href):
        """Extract the keys from the href template, cache the result."""
        keys = self.href_keys_cache.get(href, None)
        if not keys:
            keys = [_[1] for _ in Formatter().parse(href)]
            self.href_keys_cache[href] = keys
        return keys

    def __enter__(self):
        """Enter the context."""
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Exit the context."""
        pass

    def insert_links(self, vertex: dict) -> dict:
        """Insert links into a vertex.

        Parameters:
            vertex: a vertex
        Returns:
            dict: vertex with links inserted

        """
        links = []

        _schema = self.vertex_schema
        if isinstance(self.vertex_schema, VertexSchemaDecorator):
            _schema = self.vertex_schema.schema

        if 'links' not in _schema:
            return vertex

        for schema_link in _schema['links']:

            keys = self._extract_href_keys(schema_link['href'])

            values = self._extract_values(schema_link, vertex)

            if values is None or (isinstance(values, list) and len(values) == 1 and values[0] is None):
                continue

            for _ in values:
                if not isinstance(_, list):
                    _ = [_]
                if 'Resource' in schema_link['href']:  # Any resource
                    links.append(
                        {
                            'rel': schema_link['rel'],
                            'href': _[0],
                        }
                    )
                else:
                    links.append(
                        {
                            'rel': schema_link['rel'],
                            'href': schema_link['href'].format(**dict(zip(keys, _))),
                        }
                    )

        vertex['links'] = links
        return vertex

    def validate(self, vertex: dict):
        """Validate a vertex.

        Parameters:
            vertex: a vertex
        Returns:
            jsonschema.ValidationError if the vertex is invalid, True otherwise

        """
        jsonschema.validate(vertex, self.schema)
        return True

    def _extract_values(self, schema_link, vertex) -> list:
        """Extract values from a vertex given a link description object"""
        values = []
        for k, v in schema_link['templatePointers'].items():
            values_ = self.extract_json_pointer_via_glom(v, vertex)
            if len(values_) == 1:
                values_ = values_[0]

            if values_ is None or (isinstance(values_, list) and None in values_):
                #  Unable to resolve {schema_link['href']} {schema_link['templatePointers']}
                return [None]

            # disambiguate polymorphic references
            # if we have a FHIR polymorphic reference, we need to check that the target schema is in the list of values
            ref = schema_link['targetSchema']['$ref'].split('/')[-1]
            ref = ref.replace('.yaml', '')
            if ref != 'Resource':  # skip `Any` Resource
                if '/' in values_ and ref not in values_:
                    # Polymorphic reference {schema_link['targetSchema']['$ref']} {values} skipping
                    return [None]

            new_val = []
            if isinstance(values_, str):
                values_ = [values_]
            for _ in values_:
                if isinstance(_, list) and len(_) == 1:
                    _ = _[0]

                extracted_value = self._extract_value(schema_link['href'], _)[0]
                new_val.append(extracted_value)
            values.extend(new_val)

        return values

    def extract_json_pointer_via_glom(self, json_pointer, vertex):
        """Convert json pointer to glom query, cache the compiled and extract the value from the vertex. flatten nested lists."""
        if json_pointer not in self.glom_cache:
            glom_instance = cast_json_pointer_to_glom(json_pointer)
            self.glom_cache[json_pointer] = self.glom_cache.get(json_pointer, None) or glom_instance
        try:
            values_ = glom(vertex, self.glom_cache[json_pointer])
        except PathAccessError:
            return [None]
        # flatten nested lists
        if isinstance(values_, list) and len(values_) > 0 and isinstance(values_[0], list):
            values_ = flatten(values_)
        return values_

    def _extract_value(self, schema_href, instance_href) -> (str, str):
        """Read the value from instance href, strips fhir relative references.
        Returns: (instance_value, key)
            """
        # not a fhir relative reference
        if '/' not in instance_href:
            key = self._extract_href_keys(schema_href)[0]
            return instance_href, key

        # cache the regexp
        rexp = self.regexp_cache.get(schema_href, None)
        if rexp is None:
            _ = schema_href
            keys = self._extract_href_keys(schema_href)
            for key in keys:
                _ = _.replace(f"{{{key}}}", '(.*)')
            rexp = re.compile(_)
            self.regexp_cache[schema_href] = rexp

        _ = self._extract_href_keys(schema_href)[0]

        if 'Resource' in schema_href:  # Any Resource
            return instance_href, _

        m = rexp.match(instance_href)
        assert m is not None, f"Unable to find value in instance link {instance_href} given schema {schema_href}"
        return m.group(1), _


class SchemaLinkWriter:
    """Context manager for inserting links into schemas."""

    def __init__(self):
        """Initialize the context manager.
        """
        pass

    def __enter__(self):
        """Enter the context."""
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Exit the context."""
        pass

    @staticmethod
    def insert_links(schema, classes) -> dict:
        """Insert links into a schema.

        Parameters:
            schema: a schema dict or url
            classes: a list of types
        Returns:
            dict: schema with links inserted

        """
        schema = _load_schema(schema)
        links, nested_links = _generate_links_from_fhir_references(schema, classes)
        schema['links'] = links + nested_links
        schema['properties']['links'] = {
            'type': 'array',
            'items': {
                '$ref': 'https://json-schema.org/draft/2020-12/links'
            }
        }
        return schema

    @staticmethod
    def validate(schema: dict):
        """Validate a schema.

        Parameters:
            schema: a schema
        Returns:
            jsonschema.ValidationError if the schema is invalid, True otherwise

        """
        jsonschema.Draft202012Validator.check_schema(schema)
        return True
