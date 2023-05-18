

def test_individual_yaml(data_dictionary_from_yaml):
    """Test individual yaml files are OK."""
    assert data_dictionary_from_yaml, "Should have loaded yaml files."
