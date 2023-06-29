import pyjq

from iceberg_tools.graph import cast_json_pointer_to_jq


def test_nested_references(nested_references: list):
    """Test nested references"""
    jq = pyjq.compile(cast_json_pointer_to_jq('/processing/-/additive/-/reference'))

    for specimen in nested_references:
        assert len(jq.all(specimen)) == specimen['_expected_reference_count'], ("Should have resolved reference", specimen)
