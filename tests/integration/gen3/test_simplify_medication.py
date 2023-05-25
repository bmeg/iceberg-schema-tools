import orjson
from fhir.resources.medicationadministration import MedicationAdministration

from iceberg_tools.data.simplifier import simplify, _render_dialect, SimplifierContextManager


def test_simplify_medication(distribution_schema):
    medication_administration = {
        "resourceType": "MedicationAdministration",
        "id": "97ac08a2-9c53-4a02-9035-04e42502a1d3",
        "meta": {"versionId": "1", "lastUpdated": "2023-01-26T14:31:45.031+00:00",
                 "source": "#l9MRe2cRjfS7IVVt"}, "status": "completed",
        "subject": {"reference": "Patient/74af22f2-a67d-4aa6-b932-30383fec846b"},
        "occurenceDateTime": "1997-10-02T16:08:23-04:00", "medication": {"concept": {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "1719286",
                        "display": "10 ML Furosemide 10 MG/ML Injection"}],
            "text": "10 ML Furosemide 10 MG/ML Injection"}},
        "encounter": {"reference": "Encounter/4e970fac-3cc1-43d3-ab26-0756037a58a1"},
        "reason": [
            {"reference": {"reference": "Condition/83d3ecf0-0ce7-473c-ac31-1f4be6c5780d"}}]
    }

    medication_administration = MedicationAdministration(**medication_administration)
    with SimplifierContextManager():

        simplified, references = simplify(medication_administration, dialect='GEN3')
        rendered = _render_dialect(simplified, references, 'GEN3', schemas=distribution_schema)

        print(orjson.dumps(rendered, option=orjson.OPT_INDENT_2).decode())

        assert 'medication' in rendered['object'], "Should render CodeableReference codeable"
        assert len(rendered['relations']) > 0
        condition = next(iter([_ for _ in rendered['relations'] if _['dst_name'] == 'condition']), None)
        assert condition, "Should render Condition relation"
