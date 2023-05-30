# http://build.fhir.org/specimen-example.json

import orjson
from fhir.resources.specimen import Specimen

from iceberg_tools.data.simplifier import simplify, _default_json_serializer, SimplifierContextManager

SPECIMEN = {
    "resourceType": "Specimen",
    "id": "101",
    "text": {
        "status": "generated",
        "div": "TEXT ..."
    },
    "identifier": [{
        "system": "http://ehr.acme.org/identifiers/collections",
        "value": "23234352356"
    }],
    "accessionIdentifier": {
        "system": "http://lab.acme.org/specimens/2011",
        "value": "X352356"
    },
    "status": "available",
    "type": {
        "coding": [{
            "system": "http://snomed.info/sct",
            "code": "122555007",
            "display": "Venous blood specimen"
        }]
    },
    "subject": {
        "reference": "Patient/example",
        "display": "Peter Patient"
    },
    "receivedTime": "2011-03-04T07:03:00Z",
    "request": [{
        "reference": "ServiceRequest/example"
    }],
    "collection": {
        "collector": {
            "reference": "Practitioner/example"
        },
        "collectedDateTime": "2011-05-30T06:15:00Z",
        "quantity": {
            "value": 6,
            "unit": "mL"
        },
        "method": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v2-0488",
                "code": "LNV"
            }]
        },
        "bodySite": {
            "concept": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "49852007",
                    "display": "Structure of median cubital vein (body structure)"
                }]
            }
        }
    },
    "container": [{
        "device": {
            "reference": "Device/device-example-specimen-container-green-gel-vacutainer"
        },
        "specimenQuantity": {
            "value": 3,
            "unit": "mL"
        }
    }],
    "note": [{
        "text": "Specimen is grossly lipemic"
    }],
    "processing": [{
        "description": "Acidify to pH < 3.0 with 6 N HCl.",
        "method": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v2-0373",
                "code": "ACID"
            }]
        },
        "additive": [{
            "reference": "Substance/CHEMBL1231821",
            "display": "6 N HCl"
        }],
        "timeDateTime": "2015-08-18T08:10:00Z"
    }],
}


def test_simplify():
    nested_objects = {
        'Specimen': ['processing.additive', 'processing.method', 'collection.method', 'collection.bodySite'],
        'DocumentReference': ['content.contentType', 'content.md5', 'content.size', 'content.url'],
        'Patient': ['address.postalCode']
    }
    specimen = Specimen(**SPECIMEN)
    with SimplifierContextManager():
        simplified, references = simplify(specimen, 'GEN3', nested_objects)

    print(orjson.dumps(simplified, default=_default_json_serializer,
                       option=orjson.OPT_APPEND_NEWLINE).decode())

    assert simplified['collection_method_coding'] == ["http://terminology.hl7.org/CodeSystem/v2-0488#LNV"]
    assert simplified['collection_method'] == ["LNV"]

    assert simplified['collection_bodySite'] == ["Structure of median cubital vein (body structure)"]
    assert simplified['collection_bodySite_coding'] == ["http://snomed.info/sct#49852007"]

    assert simplified['processing_additive'] == 'Substance/CHEMBL1231821'

    assert simplified['processing_method'] == ['ACID']
    assert simplified['processing_method_coding'] == ['http://terminology.hl7.org/CodeSystem/v2-0373#ACID']

    assert 'Patient/example' in references
    assert 'Substance/CHEMBL1231821' in references
