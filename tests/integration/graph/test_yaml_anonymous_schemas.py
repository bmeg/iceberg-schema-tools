import pathlib
import yaml
from jsonschema.validators import Draft202012Validator


def test_yaml_anonymous_schemas(bmeg_dir):
    """Check individual anonymous schemas"""
    for file_name in pathlib.Path('').glob("*.yaml"):
        with open(file_name) as fp:
            Draft202012Validator.check_schema(yaml.load(fp, yaml.SafeLoader))
