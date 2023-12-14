from glom import glom

from iceberg_tools.graph import cast_json_pointer_to_glom


def test_nested_references(nested_references: list):
    """Test nested references"""
    glom_instance = cast_json_pointer_to_glom('/processing/-/additive/-/reference')

    """
    How is the third array supposed to have length 2 when each reference key value pair only has 1 element??
    tests/unit/link-description-object/test_nested_references.py
    1 [['Substance/sub-1']]
    2 [['Substance/sub-1'], ['Substance/sub-2']]
    2 [['Substance/sub-1', 'Substance/sub-2']]
    """
    for specimen in nested_references:
        print(specimen['_expected_reference_count'], glom(specimen, glom_instance))
        assert len(glom(specimen, glom_instance)) == specimen['_expected_reference_count'], ("Should have resolved reference", specimen)
