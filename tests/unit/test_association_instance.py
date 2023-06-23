import json

import pytest

from iceberg_tools.graph import AssociationSchema, AssociationInstance


def test_init(schema: dict, instance: dict):
    """Test class init with an instance of the association."""
    association_schema = AssociationSchema(schema=schema)
    association_instance = AssociationInstance(association_schema=association_schema, instance=instance)
    assert association_instance.instance == instance
    assert association_instance.association_schema == association_schema


def test_failed_init(schema: dict):
    """Test class init, expect failure since neither instance or vertices provided."""
    association_schema = AssociationSchema(schema=schema)
    with pytest.raises(AssertionError):
        AssociationInstance(association_schema=association_schema, instance=None, vertex_a=None, vertex_b=None)


def test_repr(schema: dict, instance: dict):
    """Test class repr (to_string)."""
    association_schema = AssociationSchema(schema=schema)
    association_instance = AssociationInstance(association_schema=association_schema, instance=instance)
    expected = 'Foo(f81d4fae-7dec-11d0-a765-00a0c91e6bf6).bar<-FooBarAssociation->Bar(9a652678-4616-475d-af12-aca21cfbe06d).foo'
    assert repr(association_instance) == expected


def test_init_create_instance(schema: dict, foo: dict, bar: dict):
    """Test class init given two vertices."""
    association_schema = AssociationSchema(schema=schema)
    association_instance = AssociationInstance(association_schema=association_schema, vertex_a=foo, vertex_b=bar)
    assert association_instance.instance
    expected = 'Foo(f81d4fae-7dec-11d0-a765-00a0c91e6bf6).bar<-FooBarAssociation->Bar(9a652678-4616-475d-af12-aca21cfbe06d).foo'
    assert repr(association_instance) == expected


def test_init_bad_create_instance(schema: dict, bar: dict, bad_foo: dict):
    """Test class init given two vertices, expect failure."""
    association_schema = AssociationSchema(schema=schema)

    with pytest.raises(Exception):
        AssociationInstance(association_schema=association_schema, vertex_a=bad_foo, vertex_b=bar)


def test_write_edge(schema: dict, foo: dict, bar: dict):
    association_schema = AssociationSchema(schema=schema)
    association_instance = AssociationInstance(association_schema=association_schema, vertex_a=foo, vertex_b=bar)
    edge = association_instance.write_edge()
    expected = {"label": "FooBarAssociation",
                "bar": {"id": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6", "rel": "bar", "targetSchema": "Foo",
                        "multiplicity": "has_many", "directionality": "out"},
                "foo": {"id": "9a652678-4616-475d-af12-aca21cfbe06d", "rel": "foo", "targetSchema": "Bar",
                        "multiplicity": "has_many", "directionality": "out"}}

    print(json.dumps(edge))
    assert edge == expected
