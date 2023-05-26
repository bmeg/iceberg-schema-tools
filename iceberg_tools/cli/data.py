import logging
import pathlib
import threading
import uuid

import click
import yaml
from fhir.resources import FHIRAbstractModel  # noqa
from yaml import SafeLoader

from iceberg_tools.data.report import aggregate_edges
from iceberg_tools.data.migrator import migrate_directory
from iceberg_tools.data.pfb import SimplePFBWriter
from iceberg_tools.data.simplifier import cli as simplifier
from iceberg_tools.schema.gen3_validator import directory_reader as gen3_directory_reader
from iceberg_tools.util import NaturalOrderGroup, directory_reader

LINKS = threading.local()
CLASSES = threading.local()
IDENTIFIER_LIST_SIZE = 8

ACED_NAMESPACE = uuid.uuid3(uuid.NAMESPACE_DNS, 'aced-ipd.org')
logger = logging.getLogger(__name__)


@click.group(name="data", cls=NaturalOrderGroup)
def cli():
    """Project data (ResearchStudy, ResearchSubjects, Patient, etc.)."""
    pass


cli.add_command(simplifier)


@cli.command('validate')
@click.argument('path')
@click.option('--pattern', required=True, default="*.*", show_default=True,
              help='File name pattern')
def _validate(path, pattern):
    """Check FHIR data for validity and ACED conventions.

    PATH: Path to FHIR files.
    """
    ok = True
    for result in directory_reader(pathlib.Path(path), pattern):
        if result.exception:
            ok = False
            print('file:', result.path)
            print('\toffset:', result.offset)
            print('\tresource_id:', result.resource_id)
            msg = str(result.exception).replace('\n', '\n\t\t')
            print('\texception:', msg)
    if ok:
        print('OK, all resources pass')


@cli.command('validate-gen3')
@click.argument('path')
@click.option('--schema_path', required=True,
              default='iceberg/schemas/gen3/aced.json',
              show_default=True,
              help='Path to gen3 schema json, a file path or url'
              )
def _validate_gen3(path, schema_path):

    """Check Gen3 data for validity and ACED conventions.

    PATH: Path to Gen3 ndjson files.
    """
    ok = True
    for result in gen3_directory_reader(pathlib.Path(path), schema_path):
        if result.exception:
            ok = False
            print('file:', result.path)
            print('\toffset:', result.offset)
            print('\tresource_id:', result.resource_id)
            msg = str(result.exception).replace('\n', '\n\t\t')
            print('\texception:', msg)
    if ok:
        print('OK, all resources pass')


@cli.command('pfb')
@click.argument('path')
@click.argument('output_path')
@click.option('--schema_path', required=True,
              default='iceberg/schemas/gen3/aced.json',
              show_default=True,
              help='Path to gen3 schema json, a file path or url'
              )
@click.option('--config_path',
              default='config.yaml',
              show_default=True,
              help='Path to config file.')
def pfb(path, output_path, schema_path, config_path):

    """Write simplified FHIR files to a PFB.

    \b
    PATH: Directory path to simplified FHIR ndjson files.
    OUTPUT_PATH: File path where to write the PFB.
    """
    path = pathlib.Path(path)
    output_path = pathlib.Path(output_path)
    config_path = pathlib.Path(config_path)
    assert output_path.is_dir(), f"Path {output_path} is not a directory"
    assert config_path.is_file(), f"Path {config_path} is not a file"
    assert path.is_file(), f"Path {path} is not a file"

    with open(config_path) as fp:
        gen3_config = yaml.load(fp, SafeLoader)
    dependency_order = gen3_config['dependency_order']

    pfb_writer = SimplePFBWriter(schema_path=schema_path,
                                 output_path=output_path,
                                 dependency_order=dependency_order
                                 )

    # this is a generator, needs to be consumed
    [_ for _ in pfb_writer.transform_directory(path)]

    inspection = pfb_writer.inspect()
    if len(inspection.errors) > 0:
        logger.error(inspection.warnings)
    if len(inspection.warnings) > 0:
        logger.warning(inspection.warnings)
    if len(inspection.info) > 0:
        for _ in inspection.info:
            logger.info(_)


@cli.command('migrate')
@click.argument('path')
@click.argument('output_path')
@click.option('--validate/--no-validate', default=True, is_flag=True, show_default=True,
              help="Validate after migration")
@click.option('--pattern', required=True, default="**/*.*json", show_default=True,
              help='File name pattern')
def migrate(path, output_path, validate, pattern):
    """Migrate from FHIR R4B to R5.0.


    We solely focus on migrating the necessary migrations for the encountered data, without undertaking a comprehensive migration process.
    Please refer to repository for more details: https://github.com/bmeg/iceberg-schema-tools

    PATH: Path containing bundles (*.json) or resources (*.ndjson)
    OUTPUT_PATH: Path where migrated resources will be stored
    """

    path = pathlib.Path(path)
    output_path = pathlib.Path(output_path)
    assert path.is_dir(), f"Path {path} is not a directory"

    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)

    assert output_path.is_dir(), f"Path {output_path} is not a directory"

    migrate_directory(path, output_path, validate, pattern)


@cli.command()
@click.argument('path')
@click.argument('output_path')
@click.option('--pattern', default='**/*.avro', help='Search pattern', show_default=True)
def report(path: str,  output_path: str,  pattern: str):
    """Aggregate avro pfb files into a cytoscape friendly tsv.

    \b
    PATH: Directory path to search for pfb files
    OUTPUT_PATH: Directory path to write the report TSVs
    """
    assert pathlib.Path(path).is_dir(), f"Path {path} is not a directory"
    assert pathlib.Path(output_path).is_dir(), f"Path {output_path} is not a directory"
    aggregate_edges(path, output_path, pattern)


if __name__ == '__main__':
    cli()
