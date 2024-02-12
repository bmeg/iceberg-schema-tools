
from glom import glom, flatten

from iceberg_tools.graph import cast_json_pointer_to_glom


def test_nested_references(nested_references: list):
    """Test nested references"""
    glom_instance = cast_json_pointer_to_glom('/processing/-/additive/-/reference')

    for specimen in nested_references:
        print(specimen['_expected_reference_count'], glom(specimen, glom_instance))

        assert len(flatten(glom(specimen, glom_instance))) == specimen['_expected_reference_count'], ("Should have resolved reference", specimen)
        assert len(glom(specimen, glom_instance)) == specimen['_expected_reference_count'], ("Should have resolved reference", specimen)
