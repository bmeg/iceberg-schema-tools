import decimal
import importlib
import logging
import pathlib
import threading
import uuid
from typing import Dict, List

import click
import inflection
import orjson
import requests
import yaml

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
from yaml import SafeLoader

from iceberg_tools.util import EmitterContextManager, directory_reader
from iceberg_tools.data.simplifier.oid_lookup import get_oid

# Latest FHIR version by default
FHIR_CLASSES = importlib.import_module('fhir.resources')

LOGGED_ALREADY = []
logger = logging.getLogger(__name__)

# create a local instance
THREAD_LOCAL = threading.local()

ICEBERG_NAMESPACE = uuid.uuid3(uuid.NAMESPACE_DNS, 'ICEBERG')

class Getter:
    """A getter for a FHIR resource."""

    def __init__(self, path: str):
        """Initialize Getter."""
        self.path_str = 'this.' + path

    def _traverse_path(self, resource: FHIRAbstractModel, path_to_search: str = None):
        """Traverse the path, return the last element ,traverse 1st element in list."""
        target = resource
        path_to_search = path_to_search or str(self.path_str)
        path_to_search = path_to_search.replace('this.', '')
        for path in path_to_search.split('.'):
            _ = f"this.{path}"
            _ = eval(_, {}, {'this': target})
            if _ is None:
                break
            if isinstance(_, list):
                target = _[0]
            else:
                target = _
        return _

    def get(self, resource: FHIRAbstractModel):
        """Get the value from the resource, including extensions."""
        if 'extension' in self.path_str:
            prefix, extension_name = self.path_str.split('.extension.')
            val = self._traverse_path(resource, path_to_search=prefix)
            if val:
                extension_list = getattr(val, 'extension', None)
                for extension in extension_list or []:
                    if extension_name in extension.url:
                        return extension.dict()['__value__']
            return None

        return self._traverse_path(resource)


def _get_nested_object(resource: FHIRAbstractModel, path: str):
    """Pluck a value from a resource, using path."""
    return Getter(path).get(resource)


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

    # read config
    nested_objects = THREAD_LOCAL.nested_objects
    # render lists to scalar
    simplified = {}

    if resource.resource_type not in nested_objects:
        return simplified

    paths = nested_objects[resource.resource_type]
    for path in paths:
        nested_object_value = _get_nested_object(resource=resource, path=path)
        nested_object_name = '_'.join(path.split('.'))

        # # fyi:resource.schema() caches results
        # parent_property_name = path.split('.')[0]
        # parent_property_schema = resource.schema()['properties'][parent_property_name]

        is_array = nested_object_value is not None and isinstance(nested_object_value, list)

        if is_array and nested_object_value is not None:

            count = 0
            for item in nested_object_value:
                _ = item.dict()

                # only add index in name if > 0
                separator = '_'

                value = _['__value__']
                name = _.get('__name__', None)
                if name:
                    name = separator + name
                else:
                    name = ''

                if f"{nested_object_name}{name}" not in simplified:
                    simplified[f"{nested_object_name}{name}"] = []
                simplified[f"{nested_object_name}{name}"].append(value)

                count += 1

        else:
            # scalar
            if nested_object_value is not None:
                if hasattr(nested_object_value, 'dict'):
                    name_value_list = nested_object_value.dict()
                    if not isinstance(name_value_list, list):
                        name_value_list = [name_value_list]
                    for item in name_value_list:
                        value = item['__value__']
                        name = item.get('__name__', None)
                        if name:
                            name = '_' + name
                        else:
                            name = ''
                        if isinstance(value, list):
                            value = value[0]
                        simplified[f"{nested_object_name}{name}"] = value
                else:
                    if isinstance(nested_object_value, list):
                        nested_object_value = nested_object_value[0]
                    simplified[f"{nested_object_name}"] = nested_object_value

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
                _populate_extensions(ext_dict, extensions)
            else:
                parent_name = extension.url.split('/')[-1].replace('-', '_')
                for child_extension in extension.extension:
                    ext_dict = child_extension.dict()
                    if ext_dict:
                        _populate_extensions(ext_dict, extensions, parent_name)

    # cleanup no data
    extensions = {k: v for k, v in extensions.items() if (v is not None and v != [])}
    return extensions


def _populate_extensions(ext_dict, extensions, parent_name=None):
    """Utility, populate extensions dict with values from a single extension."""
    ext_val_as_list = ext_dict['__value__']
    if not isinstance(ext_dict['__value__'], list):
        ext_val_as_list = [ext_dict['__value__']]
    ext_name = ext_dict['__name__']
    if parent_name:
        ext_name = f"{parent_name}_{ext_name}"

    compound_name = None
    for item in ext_val_as_list:
        # more than one name
        compound_name = ext_name

        if not isinstance(item, dict):
            extensions[compound_name] = item
            continue

        if '__name__' in item and item['__name__'] != ext_name:
            compound_name = f"{compound_name}_{item['__name__']}"
        compound_name = compound_name.replace('-', '_')

        compound_name = compound_name.replace('_text', '')

        if compound_name not in extensions:
            extensions[compound_name] = []

        if '__value__' in item:
            extensions[compound_name].append(item['__value__'])
        else:
            for k, v in item.items():
                extensions[f"{compound_name}_{k}"] = v

    # if only one value, make it scalar
    if isinstance(extensions[compound_name], list) and len(extensions[compound_name]) == 1:
        extensions[compound_name] = extensions[compound_name][0]


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

    if 'content_attachment_url' not in simplified:
        logger.debug(f"Missing content_attachment_url in simplified {simplified['resourceType']} {simplified['id']}")
        suffix = None
        file_name = None
    else:
        content_url = pathlib.Path(simplified['content_attachment_url'])
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
    if 'content_attachment_extension_md5' in simplified:
        simplified['md5sum'] = simplified['content_attachment_extension_md5']
    if 'content_size' in simplified:
        simplified['file_size'] = simplified['content_attachment_size']
    simplified['object_id'] = simplified['id']

    return simplified


def _gen3_references(simplified: dict, resource: FHIRAbstractModel) -> dict:

    pass


def _ensure_dialect(simplified: dict, resource: FHIRAbstractModel, dialect: str) -> dict:
    """Enforce dialect rules, update simplified dict.
    In practice, it toggles between PFB and plain FHIR.
    PFB dialect injects Gen3 properties and harvests edges.
    """
    if dialect != 'PFB':
        return simplified
    simplified = _gen3_scaffolding_document_reference(simplified, resource)
    return simplified


def _render_dialect(simplified: dict, references: List[str], dialect: str, schemas: dict, limit_links: dict = {}) -> dict:
    """Render as PFB record ready for import
    """
    if dialect != 'PFB':
        return simplified

    labels = [_['title'] for _ in schemas.values() if 'title' in _]

    permitted_destinations = None
    if simplified['resourceType'] in limit_links:
        permitted_destinations = limit_links[simplified['resourceType']]

    gen3_links = []
    for _ in references:
        if len(_.split('/')) != 2:
            logger.warning(f"Unexpected reference format {_} in {simplified['resourceType']} {simplified['id']}")
            continue
        label, id_ = _.split('/')
        if label not in labels:
            continue
        if permitted_destinations is not None and label not in permitted_destinations:
            continue
        gen3_links.append({"dst_id": id_, "dst_name": inflection.underscore(label)})

    return {'id': simplified['id'], 'name': inflection.underscore(simplified['resourceType']), 'relations': gen3_links, 'object': simplified}


def new_id(transform_ids, id_):
    """Create a new UUID based on the original id and the seed."""
    _study_uuid = uuid.uuid5(ICEBERG_NAMESPACE, transform_ids)
    return str(uuid.uuid5(_study_uuid, id_))


def simplify(resource: FHIRAbstractModel, dialect: str, nested_objects: dict = {}, transform_ids=None) -> (Dict, List[str]):
    """Create a PFB friendly resource. Returns simplified resource and associated references.
    Most of the heavy lifting done in dict() overrides of FHIRAbstractModel.dict()
    """
    # filled in by _simple_reference_dict
    THREAD_LOCAL.references = []
    # read by _render_sub_resources
    THREAD_LOCAL.nested_objects = nested_objects
    simplified = resource.dict()
    # cleanup goes here...
    simplified = _ensure_dialect(simplified, resource, dialect)
    if transform_ids:
        simplified['id'] = new_id(transform_ids, simplified['id'])
        transformed_references = []
        for reference in THREAD_LOCAL.references:
            type_, id_ = reference.split('/')
            id_ = new_id(transform_ids, id_)
            transformed_references.append(f"{type_}/{id_}")
        THREAD_LOCAL.references = transformed_references
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
        return float(obj)
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

        self.orig_observation_dict = Observation.dict
        self.orig_codeable_concept_dict = CodeableConcept.dict
        self.orig_codeable_reference_dict = CodeableReference.dict

        self.orig_task_dict = Task.dict

        FHIRAbstractModel.dict = _simple_resource_dict
        Coding.dict = _simple_coding_dict
        Identifier.dict = _simple_identifier_dict
        Reference.dict = _simple_reference_dict
        Extension.dict = _simple_extension_dict

        # Attachment.dict = _simple_attachment_dict
        # DocumentReferenceContent.dict = _simple_document_reference_content_dict

        Observation.dict = _simple_observation_dict
        CodeableConcept.dict = _simple_codeable_concept_dict
        CodeableReference.dict = _simple_codeable_reference_dict

        Task.dict = _simple_task_dict    # TODO - do we still need this?

    def __exit__(self, exc_type, exc_value, exc_tb):
        # print("Restoring original FHIR classes", file=sys.stderr)
        FHIRAbstractModel.dict = self.orig_resource_dict
        Coding.dict = self.orig_coding_dict
        Identifier.dict = self.orig_identifier_dict
        Reference.dict = self.orig_reference_dict
        Extension.dict = self.orig_extension_dict

        Attachment.dict = self.orig_attachment_dict
        DocumentReferenceContent.dict = self.orig_document_reference_content_dict

        Observation.dict = self.orig_observation_dict
        CodeableConcept.dict = self.orig_codeable_concept_dict
        CodeableReference.dict = self.orig_codeable_reference_dict

        Task.dict = self.orig_task_dict


def simplify_directory(input_path, pattern, output_path, schema_path, dialect, config_path, transform_ids=None):
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

    with open(config_path) as fp:
        gen3_config = yaml.load(fp, SafeLoader)
    limit_links = gen3_config['limit_links']
    nested_objects = gen3_config['nested_objects']

    with SimplifierContextManager():
        with EmitterContextManager(output_path) as emitter:
            for parse_result in directory_reader(directory_path=input_path, pattern=pattern,
                                                 validate=False):
                if parse_result.exception is not None:
                    if 'resourceType' not in str(parse_result.exception):
                        logger.error(f"{parse_result.path} has exception {parse_result.exception}")
                    continue
                resource = parse_result.resource

                simplified, references = simplify(resource, dialect, nested_objects, transform_ids)
                try:
                    check_simplified_schemas(simplified, schemas)
                except (TypeError, AssertionError) as e:
                    _debug_once(str(e))

                assert simplified, ("Should have simplified", resource.resource_type, resource.id)
                all_ok = all([validate_simplified_value(_) for _ in simplified.values()])
                _assert_all_ok(all_ok, parse_result, resource, simplified)

                simplified = _render_dialect(simplified, references, dialect, schemas, limit_links)
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
              show_default=True,
              help='Path to simplified schema json.  (Accepts url or file path)'
              )
@click.option('--dialect',
              default='PFB',
              type=click.Choice(['FHIR', 'PFB'], case_sensitive=False),
              help='PFB: adds common properties, FHIR: passthrough'
              )
@click.option('--config_path',
              default='config.yaml',
              show_default=True,
              help='Path to config file.')
@click.option('--transform_ids',
              default=None,
              show_default=True,
              help='Transform ids based on this seed')

def cli(path, pattern, output_path, schema_path, dialect, config_path, transform_ids):
    """Renders PFB friendly flattened records.

    PATH: Path containing bundles (*.json) or resources (*.ndjson)
    OUTPUT_PATH: Path where simplified resources will be stored
    """
    simplify_directory(path, pattern, output_path, schema_path, dialect, config_path, transform_ids)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    cli()
