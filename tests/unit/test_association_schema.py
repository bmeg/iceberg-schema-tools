import fastjsonschema
import pytest

from iceberg_tools.graph import AssociationSchema


def test_class_init(schema: dict, instance: dict):
    """Test class init."""
    # create class
    cls = AssociationSchema(schema=schema)

    # verify class properties
    assert cls.schema == schema, "Schema property should be set"
    assert cls.compiled_schema is not None, "Compiled schema property should be set"


def test_is_association(schema: dict, not_an_association_schema: dict):
    """Test class identifies association schemas."""

    assert AssociationSchema(schema=schema), "Should be able to create class from valid schema"
    assert AssociationSchema.is_association(schema) is True, "Schema should be an association"
    assert AssociationSchema.validate_schema_conventions(schema) is True, "Schema should be an association"

    with pytest.raises(Exception):
        AssociationSchema(schema=not_an_association_schema)
    assert AssociationSchema.is_association(not_an_association_schema) is False, "Schema should not be an association"
    with pytest.raises(Exception):
        assert AssociationSchema.validate_schema_conventions(not_an_association_schema) is False, "Schema should not be an association"


def test_validate(schema: dict, instance: dict, bad_instance: dict, bad_links: dict):
    """Test class validates instance."""

    cls = AssociationSchema(schema=schema)

    # validate instance
    assert cls.validate(instance=instance), "Instance properties should validate"
    assert cls.validate_links(instance=instance), "Instance links should validate"

    with pytest.raises(fastjsonschema.exceptions.JsonSchemaException):
        cls.validate(bad_instance)

    with pytest.raises(fastjsonschema.exceptions.JsonSchemaException):
        cls.validate(bad_links)
