import json

import pyjq

from iceberg_tools.graph import cast_json_pointer_to_jq, VertexLinkWriter


def test_cast_json_pointer_to_jq():
    json_pointers = [
        "/foo",
        "/foo/bar",
        "/foo/bar/0",
        "/foo/bar/0/baz",
        "/foo/bar/0/baz/0",
        "/foo/bar/-/baz",
    ]
    jq_expressions = [
        ". | .foo",
        '. | .foo | .bar',
        '. | .foo | .bar | .[0]',
        '. | .foo | .bar | .[0] | .baz',
        '. | .foo | .bar | .[0] | .baz | .[0]',
        '. | .foo | .bar | .[]? | .baz',
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
        ["bar"],
        ["baz"],
        ["baz"],
        ["qux"],
        ["qux"],
        ["qux", "quux"],
    ]

    # test the underlying jsonpointer -> jq conversion and the pyjq extraction
    for json_pointer, expected_jq_expression, json_instance, expected_value in zip(json_pointers, jq_expressions, json_instances, expected_values):
        actual_jq_expression = cast_json_pointer_to_jq(json_pointer)
        assert actual_jq_expression == expected_jq_expression, (json_pointer, expected_jq_expression, actual_jq_expression)
        actual_value = pyjq.compile(actual_jq_expression).all(json_instance)
        assert expected_value == actual_value, (json_pointer, actual_jq_expression, json.dumps(json_instance), expected_value, actual_value)

    # test the VertexLinkWriter implementation in extract_json_pointer_via_jq
    vertex_link_writer = VertexLinkWriter({})
    for json_pointer, expected_value, json_instance in zip(json_pointers, expected_values, json_instances):
        actual_value = vertex_link_writer.extract_json_pointer_via_jq(json_pointer, json_instance)
        assert expected_value == actual_value, (json_pointer, actual_jq_expression, json.dumps(json_instance), expected_value, actual_value)
