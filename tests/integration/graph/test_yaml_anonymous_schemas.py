import pathlib
import yaml
from jsonschema.validators import Draft202012Validator


def test_yaml_anonymous_schemas(bmeg_dir):
    """Check individual anonymous schemas"""
    for file_name in pathlib.Path('').glob("*.yaml"):
        with open(file_name) as fp:
            schema = yaml.load(fp, yaml.SafeLoader)
            Draft202012Validator.check_schema(schema)
            description = schema.get('description', None)
            assert description is not None, f"Missing description in {file_name}"
            assert '[See' in description, f"Missing [See ...] in {file_name}"
            # test to ensure See only appears once
            assert description.count('[See') == 1, f"Multiple [See ...] in {file_name}"
