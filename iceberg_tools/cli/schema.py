import json
import logging
import pathlib

import click
import yaml
from yaml import SafeLoader

from iceberg_tools.schema import _find_fhir_classes, BASE_URI, _extract_schemas
from iceberg_tools.schema.graph import _bundle_schemas
from iceberg_tools.schema.simplified import _simplify_schemas
from iceberg_tools.util import NaturalOrderGroup

logger = logging.getLogger(__name__)


@click.group('schema', cls=NaturalOrderGroup)
def cli():
    """Manage graph or simplified schemas from FHIR resources."""
    pass


@cli.group('generate')
def generate():
    """Generate from FHIR resources."""
    pass


@generate.command('graph')
@click.option('--output_path', required=True,
              default='iceberg/schemas/graph',
              show_default=True,
              help='Path to generated schema files'
              )
@click.option('--config_path',
              default='config.yaml',
              show_default=True,
              help='Path to config file.')
@click.option('--stats/--no-stats', default=False, is_flag=True, show_default=True,
              help="Log statistics about the FHIR classes found.")
def generate_bmeg(output_path, config_path, stats):
    """Create BMEG schemas."""

    output_path = pathlib.Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    config_path = pathlib.Path(config_path)
    assert output_path.is_dir()
    assert config_path.is_file()
    with open(config_path) as fp:
        gen3_config = yaml.load(fp, SafeLoader)

    classes = _find_fhir_classes(gen3_config, log_stats=stats)
    schemas = _extract_schemas(classes, BASE_URI)

    output_path.mkdir(parents=True, exist_ok=True)

    for klass, schema in schemas.items():
        with open(output_path / pathlib.Path(klass + ".yaml"), "w") as fp:
            yaml.dump(schema, fp)
    logger.info(f"Individual yaml schemas written to {output_path}/*.yaml")

    path = _bundle_schemas(output_path, BASE_URI)
    logger.info(f"Aggregated json schema written to {path}")


@generate.command('simplified')
@click.option('--output_path', required=True,
              default='iceberg/schemas/simplified',
              show_default=True,
              help='Path to generated schema files'
              )
@click.option('--config_path',
              default='config.yaml',
              show_default=True,
              help='Path to config file.')
@click.option('--gen3_fixtures',
              default='resources/static_gen3_fixtures',
              show_default=True,
              help='Path to gen3 static data dictionary files.')
@click.option('--stats/--no-stats', default=False, is_flag=True, show_default=True,
              help="Log statistics about the FHIR classes found.")
def generate_simplified(output_path, config_path, gen3_fixtures, stats):
    """Create simplified schemas."""

    output_path = pathlib.Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    config_path = pathlib.Path(config_path)
    gen3_fixtures = pathlib.Path(gen3_fixtures)
    assert gen3_fixtures.is_dir()
    assert output_path.is_dir()
    assert config_path.is_file()
    with open(config_path) as fp:
        gen3_config = yaml.load(fp, SafeLoader)

    classes = _find_fhir_classes(gen3_config, log_stats=stats)
    schemas = _extract_schemas(classes, BASE_URI)
    schemas = _simplify_schemas(gen3_config, gen3_fixtures, schemas, log_stats=stats)

    # also write out yaml files
    for k, v in schemas.items():

        fn = k
        if not k.startswith('_') and 'id' in v:
            fn = v['id']
        if "yaml" not in fn:
            fn += ".yaml"

        with open(output_path / pathlib.Path(fn), "w") as fp:
            v['$schema'] = "http://json-schema.org/draft-04/schema#"
            yaml.dump(v, fp)

    logger.info(f"Simplified individual yaml schemas written to {output_path}/*.yaml")

    compile_gen3_schemas(output_path)

    logger.info(f'Simplified schema written to {output_path / pathlib.Path("simplified-fhir.json")}')


def compile_gen3_schemas(output_path):
    """create uber schema of all yaml"""
    from dictionaryutils import dump_schemas_from_dir
    with open(output_path / pathlib.Path("simplified-fhir.json"), "w") as fp:
        json.dump(dump_schemas_from_dir(output_path), fp, indent=2, sort_keys=False)


@cli.group('compile')
def compile_():
    """Create aggregated json file from individual yaml schemas"""
    pass


@compile_.command('simplified')
@click.option('--output_path', required=True,
              default='iceberg/schemas/simplified',
              show_default=True,
              help='Path to generated schema files'
              )
def compile_simplified(output_path):
    """Compile simplified schemas."""
    output_path = pathlib.Path(output_path)
    compile_gen3_schemas(output_path)
    logger.info(f'Simplified schemas written to {output_path / pathlib.Path("simplified-fhir.json")}')
