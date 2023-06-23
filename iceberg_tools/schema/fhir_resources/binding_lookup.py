import pathlib
from typing import Iterator, List
from zipfile import ZipFile

import orjson
import inflection
import sqlite3
import urllib.request
import logging

logger = logging.getLogger(__name__)


def _class_property(element_id):
    """Ensure type, property_name."""
    parts = element_id.split('.')
    if len(parts) == 2:
        return f"{parts[0]}.{parts[1]}"  # {'type': ''.join(parts[0]), 'property_name': parts[1]}
    else:
        klass = [inflection.camelize(_) for _ in parts[:-1]]
        return f"{''.join(klass)}.{parts[-1]}"  # {'type': ''.join(klass), 'property_name': parts[-1]}


def _profile_in_bundle(bundle) -> Iterator[dict]:
    """Generate profiles."""
    for e in bundle.get('entry', []):
        _ = e.get('resource', None)
        if _:
            yield _


def _profile_in_files(file_names: List[str]) -> dict:
    """Yield the elements with bindings."""
    zip_file = next(iter([_ for _ in file_names if _.endswith('zip')]), None)
    if zip_file:
        with ZipFile(zip_file) as myzip:
            for file_name in [_ for _ in file_names if not _.endswith('zip')]:
                with myzip.open(file_name) as fp:
                    for _ in _profile_in_bundle(orjson.loads(fp.read())):
                        yield _
    else:
        for file_name in file_names:
            with open(file_name) as fp:
                for _ in _profile_in_bundle(orjson.loads(fp.read())):
                    yield _


def _element_in_profile(profile: dict) -> dict:
    """Yield the elements with bindings."""
    snapshot = profile.get('snapshot', None)
    if snapshot:
        for element in snapshot.get('element', []):
            yield element


def _elements_in_files(file_names):
    """Yield the elements with bindings."""
    for profile in _profile_in_files(file_names):
        for element in _element_in_profile(profile):
            yield element


def _elements_with_bindings(file_names: List[str]) -> Iterator[dict]:
    """Elements with bindings, keyed by Class.property"""
    for element in _elements_in_files(file_names):
        if 'binding' not in element:
            continue
        if element['binding'].get('valueSet', None):
            yield {'key': _class_property(element['id']), 'element': element}


def create_fhir_definitions_lookup(iceberg_path: str = "~/.iceberg"):
    """Generate the element_bindings table."""

    path = pathlib.Path(iceberg_path).expanduser()
    path.mkdir(parents=True, exist_ok=True)

    zip_file_path = path / "5.0.0-definitions.json.zip"

    urllib.request.urlretrieve(
        "https://github.com/nazrulworld/hl7-archives/raw/0.4.0/FHIR/R5/5.0.0-definitions.json.zip",
        zip_file_path)

    generator = _elements_with_bindings(
        [str(zip_file_path), 'profiles-resources.json', 'profiles-others.json', 'profiles-types.json'])

    path = path / "element_bindings.sqlite"
    connection = sqlite3.connect(path)

    with connection:
        connection.execute(f'DROP table IF EXISTS element_bindings')
        connection.execute(f'CREATE TABLE if not exists element_bindings (id PRIMARY KEY, entity Text)')
        with connection:
            connection.executemany(f'INSERT OR REPLACE into element_bindings values (?, ?)',
                                   [(_['key'], orjson.dumps(_['element']).decode(),) for _ in generator])
        with connection:
            cursor = connection.cursor()
            cursor.execute('select count(*) from element_bindings;')
            logger.info(f'element_bindings inserted in {path} {cursor.fetchone()[0]}')


if __name__ == "__main__":
    create_fhir_definitions_lookup()
