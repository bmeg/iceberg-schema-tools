import json
from glom import glom

from iceberg_tools.graph import VertexLinkWriter, cast_json_pointer_to_glom


def test_cast_json_pointer_to_glom():
    json_pointers = [
        "/foo",
        "/foo/bar",
        "/foo/bar/0",
        "/foo/bar/0/baz",
        "/foo/bar/0/baz/0",
        "/foo/bar/-/baz",
    ]
    glom_expressions = [
        "foo",
        'foo.bar',
        'foo.bar.0',
        'foo.bar.0.baz',
        'foo.bar.0.baz.0',
        'foo.bar.*.baz',
    ]

    json_instances = [
        {"foo": "bar"},
        {"foo": {"bar": "baz"}},
        {"foo": {"bar": ["baz"]}},
        {"foo": {"bar": [{"baz": "qux"}]}},
        {"foo": {"bar": [{"baz": ["qux"]}]}},
        {"foo": {"bar": [{"baz": "qux"}, {"baz": "quux"}]}},
    ]
    expected_values = [
        "bar",
        "baz",
        "baz",
        "qux",
        "qux",
        ["qux", "quux"]
    ]

    # test the underlying jsonpointer -> glom conversion and the glom extraction
    for json_pointer, expected_glom_expression, json_instance, expected_value in zip(json_pointers, glom_expressions, json_instances, expected_values):
        actual_glom_expression = cast_json_pointer_to_glom(json_pointer)
        assert actual_glom_expression == expected_glom_expression, (json_pointer, actual_glom_expression)
        actual_value = glom(json_instance, actual_glom_expression)
        assert expected_value == actual_value, (json_pointer, actual_glom_expression, json.dumps(json_instance), expected_value, actual_value)

    # test the VertexLinkWriter implementation in extract_json_pointer_via_glom
    vertex_link_writer = VertexLinkWriter({})
    for json_pointer, expected_value, json_instance in zip(json_pointers, expected_values, json_instances):
        actual_value = vertex_link_writer.extract_json_pointer_via_glom(json_pointer, json_instance)
        assert expected_value == actual_value, (json_pointer, actual_glom_expression, json.dumps(json_instance), expected_value, actual_value)
