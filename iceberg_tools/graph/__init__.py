from typing import Callable

import fastjsonschema
import requests
import re


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
        self.validate_schema_conventions(self.schema)
        self.compiled_schema = fastjsonschema.compile(self.schema)


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


def _extract_target_hints(schema_link):
    """Retrieve attributes from targetHints, using defaults."""
    target_hints = schema_link.get('targetHints', None)
    multiplicity = next(iter(target_hints.get('multiplicity', [])), 'has_many')
    directionality = next(iter(target_hints.get('directionality', [])), 'one')
    association = next(iter(target_hints.get('association', [])), False)
    return directionality, multiplicity, association


class AssociationInstance:

    def __init__(self, association_schema: AssociationSchema, instance: dict = None, vertex_a: dict = None, vertex_b: dict = None):
        """Operate on json document in the context of an association schema.

        Parameters:
            association_schema: an AssociationSchema object
            instance: an instance of a JSON document that should conform to the association schema
            vertex_a: a vertex that should be associated with vertex_b
            vertex_b: a vertex that should be associated with vertex_a
        """
        self.instance = instance
        self.association_schema = association_schema
        self.regexp_cache = {}
        if instance is None:
            assert vertex_a is not None and vertex_b is not None, "Must provide instance or vertex_a and vertex_b"
            self.instance = self._create_instance(vertex_a, vertex_b)

    def __repr__(self):
        """Return a string representation of the instance links of the form V(id).backref<--Title-->V(id).backref"""
        parts = self.write_edge()
        label = parts['label']

        # formulate a representation of the edge's vertices
        rels = [_ for _ in parts if _ != 'label']
        msgs = []
        for rel in rels:
            _ = parts[rel]
            msgs.append(f"{_['targetSchema']}({_['id']}).{rel}")

        return f"{msgs[0]}<-{label}->{msgs[1]}"

    def _create_instance(self, vertex_a, vertex_b):
        """Create an instance of an association from two vertices."""
        vertex_a_link = self.association_schema.schema['links'][0]
        vertex_b_link = self.association_schema.schema['links'][1]
        return {
            'links': [
                {
                    'rel': vertex_a_link['rel'],
                    'href': vertex_a_link['href'].replace('{id}', vertex_a['id'])
                },
                {
                    'rel': vertex_b_link['rel'],
                    'href': vertex_b_link['href'].replace('{id}', vertex_b['id'])
                }
            ]
        }

    def _extract_id(self, schema_href, instance_href) -> str:
        """Read the id from the href template."""
        rexp = self.regexp_cache.get(schema_href, None)
        if rexp is None:
            rexp = re.compile(schema_href.replace('{id}', '(.*)'))
            self.regexp_cache[schema_href] = rexp
        m = rexp.match(instance_href)
        assert m is not None, f"Unable to find id in instance link {instance_href} given schema {schema_href}"
        return m.group(1)

    def write_edge(self):
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

        id_ = self._extract_id(schema_link['href'], instance_link['href'])

        directionality, multiplicity, _ = _extract_target_hints(schema_link)

        return {
            'id': id_,
            'rel': schema_link['rel'],
            'targetSchema': schema_link['targetSchema']['$ref'],
            'multiplicity': multiplicity,
            'directionality': directionality
        }
