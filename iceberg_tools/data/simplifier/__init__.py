import decimal
import importlib
import logging
import pathlib
import threading
from typing import Dict, List

import click
import inflection
import orjson
import requests
from fhir.resources import FHIRAbstractModel  # noqa
from fhir.resources.attachment import Attachment
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.coding import Coding
from fhir.resources.core.utils import is_primitive_type
from fhir.resources.documentreference import DocumentReferenceContent, DocumentReference
from fhir.resources.extension import Extension
from fhir.resources.identifier import Identifier
from fhir.resources.observation import Observation
from fhir.resources.reference import Reference
from fhir.resources.task import Task

from iceberg_tools.util import EmitterContextManager, directory_reader
from iceberg_tools.data.simplifier.oid_lookup import get_oid

# Latest FHIR version by default
FHIR_CLASSES = importlib.import_module('fhir.resources')

LOGGED_ALREADY = []
logger = logging.getLogger(__name__)

# create a local instance
THREAD_LOCAL = threading.local()


def _simple_coding_dict(self: Coding, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render Coding."""
    display = self.display
    if not display:
        display = self.code
    return [
        {'__value__': f"{self.system}#{self.code}", "__name__": "coding"},
        {'__value__': display},
    ]


def _simple_codeable_concept_dict(self: CodeableConcept, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render CodeableConcept."""
    codeable_concept = []
    if self.text:
        codeable_concept.append(
            {'__value__': [self.text], "__name__": "text"},
        )
    if self.coding is not None:
        codings = [_simple_coding_dict(_) for _ in self.coding]
        # flatten
        codings = [item for sublist in codings for item in sublist]
        codeable_concept.extend(
            [
                {'__value__': [_['__value__'] for _ in codings if _.get('__name__', None) == 'coding'], "__name__": "coding"},
                {'__value__': [_['__value__'] for _ in codings if '__name__' not in _]},
            ]
        )
    return codeable_concept


def _simple_codeable_reference_dict(self: CodeableReference, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render CodeableReference."""
    codeable_reference = []
    if self.reference:
        _ = self.reference.dict()
        _['__value__'] = [_['__value__']]
        codeable_reference.extend([_])
    if self.concept:
        codeable_reference.extend(self.concept.dict())
    return codeable_reference


def _simple_identifier_dict(self: Identifier, *args, **kwargs):
    """MonkeyPatch replacement for dict(), lookup urn:oid values, render Identifier."""
    name = _ensure_identifier_system(self)
    value = _ensure_identifier_value(self)
    identifier = [
        {'__value__': f"{name}#{value}", '__name__': 'identifier'},
        {'__value__': f"{self.system}#{self.value}", '__name__': 'identifier_coding'},
    ]
    if self.type:
        if self.type.text:
            {'__name__': f"{name}_text", '__value__': f"{self.type.text}"}
        if self.type.coding and len(self.type.coding) > 0:
            identifier.append(
                {'__name__': "identifier_text_coding",
                 '__value__': f"{self.type.coding[0].system}#{self.type.coding[0].code}"}
            )
    return identifier


def _ensure_identifier_value(self):
    """Lookup urn: style values. dependent on oid_lookup."""
    value = self.value
    if value:
        if 'urn:oid' in value:
            value_, content = get_oid(value.split('urn:oid:')[-1])
            if not value_:
                _debug_once(('get_oid failed', value, content))
            else:
                value = value_
    return value


def _ensure_identifier_system(self):
    """Ensure identifier `system` simplified."""
    name = None
    if self.system:
        if 'urn:oid' in self.system:
            name, content = get_oid(self.system.split('urn:oid:')[-1])
            if not name:
                _debug_once(('get_oid failed', self.system, content))
        elif 'urn:ietf:rfc:3986' in self.system:
            name = 'uri'
        else:
            name = self.system.split('/')[-1].replace('-', '_')
    if not name:
        name = ''
    return name


def _simple_observation_dict(self: Observation, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render Observation."""
    observation = _simple_resource_dict(self)
    # TODO extend for specific observations
    if 'category' not in observation or observation['category'] == [None]:
        observation['category'] = ['laboratory']
        observation['category_coding'] = ['http://terminology.hl7.org/CodeSystem/observation-category#laboratory']
    return observation


def _simple_extension_dict(self: Extension, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render Extension."""
    # note `self` is the Extension
    # stop traversal here
    alias_maps = self.get_alias_mapping()
    for prop_name in self.elements_sequence():
        field_key = alias_maps[prop_name]
        is_value = field_key.startswith('value')
        if is_value:
            v = self.__dict__.get(field_key, None)
            if v is not None:
                is_fhir = issubclass(type(v), FHIRAbstractModel)
                _name = self.url
                if _name:
                    _name = _name.split('/')[-1]
                _name = _name.replace('-', '_')
                if is_fhir:
                    v = v.dict()
                _ = {'__value__': v}
                if _name:
                    _['__name__'] = _name
                return _


def _simple_reference_dict(self: Reference, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render Reference."""
    # note `self` is the Reference
    # stop traversal here
    THREAD_LOCAL.references.append(self.reference)
    return {'__value__': self.reference}


def _simple_attachment_dict(self: Attachment, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render Attachment."""
    attachment = _render_extensions(self)
    attachment.update(_render_primitives(self))
    return attachment


def _simple_document_reference_content_dict(self: DocumentReferenceContent, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render DocumentReferenceContent."""
    document_reference_content = _render_extensions(self)
    document_reference_content.update(_render_primitives(self))
    document_reference_content.update(self.attachment.dict())
    return document_reference_content


def _simple_document_reference_dict(self: DocumentReference, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render DocumentReference."""
    # defaults
    document_reference = _simple_resource_dict(self)
    # # sub-resource
    # _render_sub_resources(document_reference, self)

    return document_reference


def _simple_task_dict(self: Task, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render Observation."""
    task = _simple_resource_dict(self)
    # go through outputs to collect references
    for _ in self.output:
        _.dict()
    return task


def _render_sub_resources(resource: FHIRAbstractModel) -> dict:
    """Render sub-resources with keys "{sub_resource}_{if list index}_{property_name}: simple_value" """
    config = {
        'DocumentReference': {
            'lists': {
                'content': {'limit': 1, 'properties': ['contentType', 'md5', 'size', 'url']}
            },
            'scalars': {}
        },
        'Patient': {
            'lists': {
                'address': {'limit': 1, 'properties': ['postalCode']}
            },
            'scalars': {}
        }
    }
    # render lists to scalar
    simplified = {}
    if resource.resource_type not in config:
        return simplified

    lists = config[resource.resource_type].get('lists', {})
    scalars = config[resource.resource_type].get('scalars', {})

    # add values to simplified resource

    # lists
    for resource_property_name in lists:  # sub_resource's property name
        assert hasattr(resource, resource_property_name), f"{resource.resource_type} has no property named {resource_property_name}"
        resource_property = getattr(resource, resource_property_name)
        if not resource_property:
            continue
        limit = lists[resource_property_name].get('limit', 1)
        properties = lists[resource_property_name].get('properties', [])
        count = 0
        for item in resource_property:
            _ = item.dict()
            # only add index in name if > 0
            separator = '_'
            if count > 0:
                separator = f"_{count}_"
            for k, v in _.items():
                if k in properties:
                    simplified[f"{resource_property_name}{separator}{k}"] = v
            count += 1
            if count == limit:
                break
            # warn if data had more than limit
            if len(resource.content) > limit:
                logger.warning(f"{resource.resource_type}/{resource.id} {resource_property_name}"
                               f" had {len(resource.content)} items limit was {limit}")

    # scalars
    for resource_property_name in scalars:  # sub_resource's property name
        assert hasattr(resource, resource_property_name), f"{resource.resource_type} has no property named {resource_property_name}"
        resource_property = getattr(resource, resource_property_name)
        if not resource_property:
            continue
        _ = resource_property.dict()
        for k, v in _.items():
            simplified[f"{resource_property_name}_{k}"] = v

    return simplified


def _simple_resource_dict(self: FHIRAbstractModel, *args, **kwargs):
    """MonkeyPatch replacement for dict(), render generic Resource."""
    # override this with a specialization
    simplified = _render_extensions(self)
    simplified.update(_render_primitives(self))
    simplified.update(_render_codings(self))
    simplified.update(_render_identifiers(self))
    simplified.update(_render_references(self))
    simplified.update(_render_sub_resources(self))
    return simplified


def _render_primitives(self: FHIRAbstractModel, *args, **kwargs) -> Dict:
    """Utility, create a dict of the primitive keys in a resource"""
    alias_maps = self.get_alias_mapping()
    resource_primitives = {}
    for prop_name in self.elements_sequence():
        field_key = alias_maps[prop_name]
        is_primitive = is_primitive_type(self.__fields__[field_key])
        v = self.__dict__.get(field_key, None)
        if v is not None and is_primitive:
            resource_primitives[field_key] = v
    if 'resourceType' not in resource_primitives:
        resource_primitives['resourceType'] = self.resource_type
    return resource_primitives


def _render_references(self: FHIRAbstractModel, *args, **kwargs) -> Dict:
    """Utility, create a dict of the references in a resource."""
    alias_maps = self.get_alias_mapping()
    references = {}
    for prop_name in self.elements_sequence():
        field_key = alias_maps[prop_name]
        v = self.__dict__.get(field_key, None)
        if v is not None and isinstance(v, Reference):
            references[field_key] = v.dict()['__value__']
    return references


def _render_extensions(self: FHIRAbstractModel, *args, **kwargs) -> Dict:
    """Utility, create a dict of the extensions in a resource."""
    extensions = {}
    if hasattr(self, 'extension') and self.extension:
        for extension in self.extension:
            ext_dict = extension.dict()
            if ext_dict:
                ext_val_as_list = ext_dict['__value__']
                if not isinstance(ext_dict['__value__'], list):
                    ext_val_as_list = [ext_dict['__value__']]
                ext_name = ext_dict['__name__']
                for item in ext_val_as_list:
                    # more than one name
                    compound_name = ext_name

                    if not isinstance(item, dict):
                        extensions[compound_name] = item
                        continue

                    if '__name__' in item:
                        compound_name = f"{compound_name}_{item['__name__']}"
                    compound_name = compound_name.replace('-', '_')

                    if compound_name not in extensions:
                        extensions[compound_name] = []

                    if '__value__' in item:
                        extensions[compound_name].extend(item['__value__'])
                    else:
                        for k, v in item.items():
                            extensions[f"{compound_name}_{k}"] = v

                    # if only one value, make it scalar
                    if len(extensions[compound_name]) == 1:
                        extensions[compound_name] = extensions[compound_name][0]
    # cleanup no data
    extensions = {k: v for k, v in extensions.items() if (v is not None and v != [])}
    return extensions


def _render_codings(self: FHIRAbstractModel, *args, **kwargs) -> Dict:
    """Utility, create a dict of the codings in a resource."""
    codings = {}
    alias_maps = self.get_alias_mapping()
    for prop_name in self.elements_sequence():
        field_key = alias_maps[prop_name]
        v = self.__dict__.get(field_key, None)
        is_scalar = not isinstance(v, list)

        if v is not None:
            v_as_list = v
            if not isinstance(v_as_list, list):
                v_as_list = [v_as_list]
            if len(v_as_list) == 0:
                continue
            if type(v_as_list[0]) not in [CodeableConcept, Coding, CodeableReference]:
                continue
            for v in v_as_list:
                codings_as_list = v.dict()
                if not isinstance(codings_as_list, list):
                    codings_as_list = [codings_as_list]
                for _ in codings_as_list:
                    compound_name = field_key
                    if '__name__' in _:
                        compound_name = f"{compound_name}_{_['__name__']}"
                    compound_name = compound_name.replace('-', '_')
                    if compound_name not in codings:
                        codings[compound_name] = []
                    codings[compound_name].extend(_['__value__'])
                    if is_scalar:
                        codings[compound_name] = codings[compound_name][0]
    return codings


def _render_identifiers(self: FHIRAbstractModel, *args, **kwargs) -> Dict:
    """Utility, create a dict of the identifiers in a resource."""

    identifiers = {}

    if hasattr(self, 'identifier') and self.identifier:

        # treat as a list, Per FHIR most are, some are not
        identifier_list = self.identifier
        if not isinstance(self.identifier, list):
            identifier_list = [self.identifier]

        # render as {k:[]}
        rendered_identifiers = []
        for _ in identifier_list:
            rendered_identifiers.extend(_simple_identifier_dict(_))
        keys = [_['__name__'] for _ in rendered_identifiers]
        for k in keys:
            identifiers[k] = [_['__value__']for _ in rendered_identifiers if _['__name__'] == k]

    return identifiers


def validate_simplified_value(v) -> bool:
    """Is a field valid in a simplified model?"""
    if v is None:
        return True
    if isinstance(v, list) and len(v) == 0:
        return True
    if isinstance(v, list) and issubclass(type(v[0]), FHIRAbstractModel):
        return False
    if isinstance(v, list) and isinstance(v[0], dict):
        return False
    if issubclass(type(v), FHIRAbstractModel):
        return False
    if isinstance(v, dict):
        return False
    # if isinstance(v, bytes):
    #     return False
    return True


def _gen3_scaffolding_document_reference(simplified: dict, resource: FHIRAbstractModel) -> dict:
    """Add Gen3 boiler plate"""

    if simplified['resourceType'] != 'DocumentReference':
        return simplified

    if 'content_url' not in simplified:
        logger.warning(f"Missing content_url in simplified {simplified['resourceType']} {simplified['id']}")
        suffix = None
        file_name = None
    else:
        content_url = pathlib.Path(simplified['content_url'])
        suffix = content_url.suffix
        file_name = content_url.name

    if suffix:
        suffix = suffix.replace('.', '')
    simplified['data_type'] = suffix
    if suffix in ['csv']:
        simplified['data_format'] = 'variants'
    if suffix in ['dcm', 'tif']:
        simplified['data_format'] = 'imaging'
    if suffix in ['txt']:
        simplified['data_format'] = 'note'
    if suffix in ['out', 'log']:
        simplified['data_format'] = 'log'
    if suffix in ['m']:
        simplified['data_format'] = 'matlab'
    if suffix in ['sh']:
        simplified['data_format'] = 'script'

    simplified['file_name'] = file_name
    if 'content_md5' in simplified:
        simplified['md5sum'] = simplified['content_md5']
    if 'content_size' in simplified:
        simplified['file_size'] = simplified['content_size']
    simplified['object_id'] = simplified['id']

    return simplified


def _gen3_references(simplified: dict, resource: FHIRAbstractModel) -> dict:

    pass


def _ensure_dialect(simplified: dict, resource: FHIRAbstractModel, dialect: str) -> dict:
    """Enforce dialect rules, update simplified dict.
    In practice, it toggles between GEN3 and plain FHIR.
    Gen3 dialect injects Gen3 properties and harvests edges.
    """
    if dialect != 'GEN3':
        return simplified
    simplified = _gen3_scaffolding_document_reference(simplified, resource)
    return simplified


def _render_dialect(simplified: dict, references: List[str], dialect: str, schemas) -> dict:
    """Render as Gen3 record ready for import
    """
    if dialect != 'GEN3':
        return simplified

    labels = [_['title'] for _ in schemas.values() if 'title' in _]

    gen3_links = []
    for _ in references:
        if len(_.split('/')) != 2:
            logger.warning(f"Unexpected reference format {_} in {simplified['resourceType']} {simplified['id']}")
            continue
        label, id_ = _.split('/')
        if label not in labels:
            continue
        gen3_links.append({"dst_id": id_, "dst_name": inflection.underscore(label)})

    return {'id': simplified['id'], 'name': inflection.underscore(simplified['resourceType']), 'relations': gen3_links, 'object': simplified}


def simplify(resource: FHIRAbstractModel, dialect: str) -> (Dict, List[str]):
    """Create a Gen3 friendly resource. Returns simplified resource and associated references."""
    # most of the heavy lifting done in dict() overrides
    THREAD_LOCAL.references = []
    simplified = resource.dict()
    # cleanup goes here...
    simplified = _ensure_dialect(simplified, resource, dialect)
    return simplified, THREAD_LOCAL.references


def check_simplified_schemas(simplified: dict, schemas: dict):
    """Compare simplified fields vs schema."""
    resource_type = inflection.underscore(simplified['resourceType'])
    assert resource_type in schemas, f"{resource_type} not in schemas"
    extra_fields = [k for k in simplified if k not in schemas[resource_type]['properties']]
    assert len(extra_fields) == 0, ('extra_fields_not_in_schema', resource_type, extra_fields)


def _default_json_serializer(obj):
    """JSON Serializer, render decimal and bytes types."""
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.decode()

    raise TypeError


class SimplifierContextManager:
    """Monkey patch FHIR classes, restore when complete"""
    def __enter__(self):
        # print("Monkey patching FHIR", file=sys.stderr)
        self.orig_resource_dict = FHIRAbstractModel.dict
        self.orig_coding_dict = Coding.dict
        self.orig_identifier_dict = Identifier.dict
        self.orig_reference_dict = Reference.dict
        self.orig_extension_dict = Extension.dict
        self.orig_attachment_dict = Attachment.dict
        self.orig_document_reference_content_dict = DocumentReferenceContent.dict
        # self.orig_document_reference_dict = DocumentReference.dict
        self.orig_observation_dict = Observation.dict
        self.orig_codeable_concept_dict = CodeableConcept.dict
        self.orig_codeable_reference_dict = CodeableReference.dict
        self.orig_task_dict = Task.dict

        FHIRAbstractModel.dict = _simple_resource_dict
        Coding.dict = _simple_coding_dict
        Identifier.dict = _simple_identifier_dict
        Reference.dict = _simple_reference_dict
        Extension.dict = _simple_extension_dict
        Attachment.dict = _simple_attachment_dict
        DocumentReferenceContent.dict = _simple_document_reference_content_dict
        # DocumentReference.dict = _simple_document_reference_dict
        Observation.dict = _simple_observation_dict
        CodeableConcept.dict = _simple_codeable_concept_dict
        CodeableReference.dict = _simple_codeable_reference_dict
        Task.dict = _simple_task_dict

    def __exit__(self, exc_type, exc_value, exc_tb):
        # print("Restoring original FHIR classes", file=sys.stderr)
        FHIRAbstractModel.dict = self.orig_resource_dict
        Coding.dict = self.orig_coding_dict
        Identifier.dict = self.orig_identifier_dict
        Reference.dict = self.orig_reference_dict
        Extension.dict = self.orig_extension_dict
        Attachment.dict = self.orig_attachment_dict
        DocumentReferenceContent.dict = self.orig_document_reference_content_dict
        # DocumentReference.dict = self.orig_document_reference_dict
        Observation.dict = self.orig_observation_dict
        CodeableConcept.dict = self.orig_codeable_concept_dict
        CodeableReference.dict = self.orig_codeable_reference_dict
        Task.dict = self.orig_task_dict


def simplify_directory(input_path, pattern, output_path, schema_path, dialect):
    """Reads directory of FHIR, renders simple, data frame friendly flattened records."""

    input_path = pathlib.Path(input_path)
    assert input_path.is_dir(), f"{input_path} not a directory"
    dialect = dialect.upper()

    if pathlib.Path(schema_path).is_file():
        with open(schema_path, "rb") as fp_:
            schemas = orjson.loads(fp_.read())
    else:
        schemas = requests.get(schema_path).json()
    assert schemas, f"No schema found at {schema_path}"

    with SimplifierContextManager():
        with EmitterContextManager(output_path) as emitter:
            for parse_result in directory_reader(directory_path=input_path, pattern=pattern,
                                                 validate=False):
                if parse_result.exception is not None:
                    if 'resourceType' not in str(parse_result.exception):
                        logger.error(f"{parse_result.path} has exception {parse_result.exception}")
                    continue
                resource = parse_result.resource

                simplified, references = simplify(resource, dialect)
                try:
                    check_simplified_schemas(simplified, schemas)
                except (TypeError, AssertionError) as e:
                    _debug_once(str(e))

                assert simplified, ("Should have simplified", resource.resource_type, resource.id)
                all_ok = all([validate_simplified_value(_) for _ in simplified.values()])
                _assert_all_ok(all_ok, parse_result, resource, simplified)

                simplified = _render_dialect(simplified, references, dialect, schemas)
                fp = emitter.emit(resource.resource_type)
                fp.write(orjson.dumps(simplified, default=_default_json_serializer,
                                      option=orjson.OPT_APPEND_NEWLINE).decode())


def _debug_once(msg):
    if msg not in LOGGED_ALREADY:
        LOGGED_ALREADY.append(msg)
        logger.debug(msg)


def _assert_all_ok(all_ok, parse_result, resource, simplified):
    """Utility, log simplified check problems."""
    if not all_ok:
        reference = f"{resource.resource_type}/{resource.id}"
        logger.warning(f"{parse_result.path} {reference} {parse_result.offset}")
        logger.warning(f"\t{simplified}")
        logger.warning({k: validate_simplified_value(v) for k, v in simplified.items()})
    assert all_ok


@click.command('simplify')
@click.argument('path')
@click.argument('output_path')
@click.option('--pattern', required=True, default="**/*.*", show_default=True,
              help='File name pattern')
@click.option('--schema_path', required=True,
              default='https://aced-public.s3.us-west-2.amazonaws.com/aced.json',
              show_default=True,
              help='Path to gen3 schema json.  (Accepts file path for schema development)'
              )
@click.option('--dialect',
              default='GEN3',
              type=click.Choice(['FHIR', 'GEN3'], case_sensitive=False),
              help='GEN3: adds common properties, FHIR: passthrough'
              )
def cli(path, pattern, output_path, schema_path, dialect):
    """Renders Gen3 friendly flattened records.

    PATH: Path containing bundles (*.json) or resources (*.ndjson)
    OUTPUT_PATH: Path where simplified resources will be stored
    """
    simplify_directory(path, pattern, output_path, schema_path, dialect)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    cli()
