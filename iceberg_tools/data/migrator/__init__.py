import gzip
import io
import logging

import orjson

from iceberg_tools.util import parse_obj

logger = logging.getLogger(__name__)


def _is_bundle(resource):
    """Return True if resource is a bundle."""
    return resource['resourceType'] == 'Bundle'


def _is_fhir_resource(resource):
    """Return True if resource is a FHIR resource."""
    return 'resourceType' in resource


def migrate_resource(resource: dict) -> dict:
    """Apply migrations.

    We solely focus on migrating the necessary migrations for the encountered data, without undertaking a comprehensive migration process.

    :param resource: FHIR resource expecting  https://hl7.org/fhir/r4b/<lower-case-resource-name>
    :return: migrated FHIR resource 5.0 see https://build.fhir.org/<lower-case-resource-name>

    """
    assert 'resourceType' in resource, ('missing resourceType', orjson.dumps(resource).decode())

    resource_type = resource['resourceType']

    migrate_encounter(resource, resource_type)
    migrate_document_reference(resource, resource_type)
    migrate_observation(resource, resource_type)
    migrate_medication_administration(resource, resource_type)
    migrate_research_subject(resource, resource_type)
    migrate_research_study(resource, resource_type)
    migrate_practitioner_role(resource, resource_type)
    migrate_specimen(resource, resource_type)
    migrate_organization(resource, resource_type)

    return resource


def migrate_organization(resource, resource_type):
    """Migrate Organization resource to 5.0"""
    if resource_type == "Organization":
        contact_0 = {}
        if 'address' in resource:
            contact_0['address'] = resource['address'][0]
            del resource['address']
        if 'telecom' in resource:
            contact_0['telecom'] = resource['telecom']
            del resource['telecom']
        if len(contact_0.keys()) > 0:
            resource['contact'] = [contact_0]


def migrate_specimen(resource, resource_type):
    """Migrate Specimen resource to 5.0"""
    if resource_type == "Specimen":
        if 'collection' in resource:
            if 'bodySite' in resource['collection']:
                resource['collection']['bodySite'] = {
                    'coding': [resource['collection']['bodySite']]
                }
            del resource['collection']


def migrate_practitioner_role(resource, resource_type):
    """Migrate PractitionerRole resource to 5.0"""
    if resource_type == "PractitionerRole":
        if 'telecom' in resource:
            resource['contact'] = [{'telecom': resource['telecom']}]
            del resource['telecom']


def migrate_encounter(resource, resource_type):
    """Migrate Encounter resource to 5.0"""
    if resource_type == "Encounter":
        resource['class'] = [
            {
                'coding': [resource['class']]
            }
        ]
        for _ in resource['participant']:
            _['actor'] = _['individual']
            del _['individual']
        resource['actualPeriod'] = resource['period']
        del resource['period']
        if 'reasonCode' in resource:
            resource['reason'] = [{'use': resource['reasonCode']}]
            del resource['reasonCode']
        if 'hospitalization' in resource:
            resource['admission'] = resource['hospitalization']
            del resource['hospitalization']


def migrate_document_reference(resource, resource_type):
    """Migrate DocumentReference resource to 5.0"""
    if resource_type == "DocumentReference":
        for _ in resource['content']:
            if 'format' in _:
                del _['format']
        if 'context' in resource and 'encounter' in resource['context']:
            del resource['context']['period']
            resource['context'] = resource['context']['encounter']
        if 'context' in resource and 'related' in resource['context']:
            resource['subject'] = resource['context']['related'][0]
            del resource['context']


def migrate_observation(resource, resource_type):
    """Migrate Observation resource to 5.0"""
    if resource_type == "Observation":
        _ = resource.get('valueSampledData', None)
        if _:
            _['intervalUnit'] = '/s'
            _['interval'] = _['period']
            del _['period']
        if 'status' not in resource:
            resource['status'] = 'final'


def migrate_medication_administration(resource, resource_type):
    """Migrate MedicationAdministration resource to 5.0"""
    if resource_type == "MedicationAdministration":
        resource['occurenceDateTime'] = resource['effectiveDateTime']
        del resource['effectiveDateTime']

        resource['medication'] = {
            'concept': resource['medicationCodeableConcept']
        }
        del resource['medicationCodeableConcept']

        resource['encounter'] = resource['context']
        del resource['context']

        if 'reasonReference' in resource:
            resource['reason'] = [{'reference': _} for _ in resource['reasonReference']]
            del resource['reasonReference']


def migrate_research_subject(resource, resource_type):
    """Migrate ResearchSubject resource to 5.0"""
    if resource_type == "ResearchSubject":
        if 'individual' in resource:
            resource['subject'] = resource['individual']
            del resource['individual']


def migrate_research_study(resource, resource_type):
    """Migrate ResearchStudy resource to 5.0"""
    if resource_type == "ResearchStudy":

        if 'category' in resource:
            resource['classifier'] = resource['category']
            del resource['category']

        if 'principalInvestigator' in resource:

            if 'associatedParty' not in resource:
                resource['associatedParty'] = []
            resource['associatedParty'].append(
                {
                    'role': {
                        'coding': [
                            {
                                'system': 'http://hl7.org/fhir/ValueSet/research-study-party-role',
                                'code': 'primary-investigator',
                                'display': 'primary-investigator'
                            }
                        ],
                        'text': 'primary-investigator'
                    },
                    'party': resource['principalInvestigator']
                }
            )
            del resource['principalInvestigator']

        if 'status' not in resource:
            resource['status'] = 'active'

        if 'focus' in resource:
            resource['condition'] = resource['focus']
            del resource['focus']

        if 'enrollment' in resource:
            resource['recruitment'] = resource['enrollment']
            del resource['enrollment']

        # example:
        # "sponsor": {
        #   "reference": "Organization/NLM",
        #   "type": "Organization",
        #   "display": "National Library of Medicine"
        # },
        if 'sponsor' in resource:
            if 'associatedParty' not in resource:
                resource['associatedParty'] = []
            resource['associatedParty'].append(
                {
                    'role': {
                        "coding": [
                            {
                                "system": "http://hl7.org/fhir/ValueSet/research-study-party-role",
                                "code": "sponsor",
                                "display": "sponsor"
                            }
                        ],
                        "text": "sponsor"
                    },
                    'party': {'reference': resource['sponsor']['reference']},
                    'name': 'sponsor'
                }
            )
            del resource['sponsor']

        # example:
        # "recruitment": [
        #   {
        #     "reference": "Group/phs002409.v1.p1-all-subjects"
        #   }
        # ],
        if 'recruitment' in resource:
            resource['recruitment'] = {
                'actualGroup': resource['recruitment'][0]
            }
            del resource['recruitment']


def _is_resource(resource):
    """Return True if resource is a FHIR resource."""
    return 'resourceType' in resource


def migrate_bundles(output_path, path, validate):
    """Migrate bundles."""
    for input_file in path.glob('**/*.json'):   # TODO: see util directory_reader
        with open(input_file, "rb") as fp:
            resource = orjson.loads(fp.read())
            if not _is_resource(resource):
                logger.warning(f"Not a FHIR resource {input_file}")
                continue
            if not _is_bundle(resource):
                continue
            bundle_ = resource
            if 'entry' not in bundle_:
                print(f"No 'entry' in bundle {input_file} ")
                continue
        for entry in bundle_['entry']:
            resource = entry['resource']
            _ = migrate_resource(resource)
            logging_validator(_, input_file, validate)

        output_file = output_path / input_file.name
        with open(output_file, "wb") as fp:
            fp.write(orjson.dumps(bundle_))
        logger.info(f'Migrated {input_file} to {output_file}')


def migrate_resources(output_path, path, validate):
    """Migrate single resource per file."""
    for input_file in path.glob('**/*.json'):  # TODO: see util directory_reader
        with open(input_file, "rb") as fp:
            resource = orjson.loads(fp.read())
            if not _is_resource(resource):
                logger.warning(f"Not a FHIR resource {input_file}")
                continue
            if _is_bundle(resource):
                continue
            _ = migrate_resource(resource)
            logging_validator(_, input_file, validate)

        output_file = output_path / input_file.name
        with open(output_file, "wb") as fp:
            fp.write(orjson.dumps(_))
        logger.info(f'Migrated {input_file} to {output_file}')


def logging_validator(_, input_file, validate):
    """Log validation errors."""
    if validate:
        parse_result = parse_obj(_)
        if parse_result.exception is not None:
            if 'resourceType' not in str(parse_result.exception):
                logger.warning(f"{input_file} has exception {parse_result.exception}")


def migrate_ndjson(output_path, path, validate):
    """Migrate ndjson files, not expecting bundles."""
    for input_file in path.glob('**/*.ndjson'):  # TODO: see util directory_reader
        with open(input_file, "r") as fp:
            output_file = output_path / input_file.name
            with open(output_file, "wb") as out_fp:
                for line in fp.readlines():
                    resource = orjson.loads(line)
                    _ = migrate_resource(resource)
                    logging_validator(_, input_file, validate)

                    out_fp.write(orjson.dumps(_, option=orjson.OPT_APPEND_NEWLINE))
        logger.info(f'Migrated {input_file} to {output_file}')


def migrate_json_gz(output_path, path, validate):
    """Migrate *json.gz files."""
    for input_file in path.glob('*.*json.gz'):  # TODO: see util directory_reader

        with io.TextIOWrapper(io.BufferedReader(gzip.GzipFile(input_file))) as fp:
            output_file = output_path / input_file.name
            with gzip.open(output_file, 'wb') as out_fp:
                for line in fp.readlines():
                    resource = orjson.loads(line)
                    try:
                        _ = migrate_resource(resource)
                        logging_validator(_, input_file, validate)

                        out_fp.write(orjson.dumps(_, option=orjson.OPT_APPEND_NEWLINE))
                    except Exception as e:
                        print('\t', str(e))
                        break
        logger.info(f'Migrated {input_file} to {output_file}')


def migrate_directory(path, output_path, validate):
    """Migrate all files in a directory."""
    # single resources per file
    migrate_bundles(output_path, path, validate)
    migrate_resources(output_path, path, validate)

    # multiple resources per file
    migrate_ndjson(output_path, path, validate)
    migrate_json_gz(output_path, path, validate)
