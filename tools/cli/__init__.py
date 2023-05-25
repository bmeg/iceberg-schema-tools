import logging

import click

from tools.cli.data import cli as data
from tools.cli.schema import cli as schema
from tools.util import NaturalOrderGroup

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group(cls=NaturalOrderGroup)
def cli():
    """Manage FHIR based schemas and data."""
    pass


cli.add_command(schema)
cli.add_command(data)


if __name__ == '__main__':
    cli()
