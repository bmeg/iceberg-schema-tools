import orjson
from fhir.resources.task import Task

from iceberg_tools.data.simplifier import simplify, _render_dialect, SimplifierContextManager


def test_simplify_task(distribution_schema):
    task = {
        "resourceType": "Task", "id": "857f89ab-2808-5592-a3e1-315466bc6181",
        "meta": {"versionId": "1", "lastUpdated": "2023-01-26T15:03:23.029+00:00",
                 "source": "#Vpgkq7bDayJaUwY1"}, "text": {"status": "generated",
                                                          "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">Autogenerated task. Inserted to make data model research friendly.</div>"},
        "status": "completed", "intent": "order",
        "focus": {"reference": "Specimen/c43eab49-c9d3-52fb-9265-9db6461b847c"},
        "for": {"reference": "Patient/1efc46e2-8aad-46be-8713-13d17e3eda83"}, "input": [
            {"type": {"coding": [{"code": "specimen"}]},
             "valueReference": {"reference": "Specimen/c43eab49-c9d3-52fb-9265-9db6461b847c"}}], "output": [
            {"type": {"coding": [{"code": "DocumentReference"}]},
             "valueReference": {"reference": "DocumentReference/64ca4c81-d466-5eb6-b57e-62238241c0e4"}}]
    }

    task = Task(**task)
    with SimplifierContextManager():

        simplified, references = simplify(task, dialect='GEN3')
        rendered = _render_dialect(simplified, references, 'GEN3', schemas=distribution_schema)

        print(orjson.dumps(rendered, option=orjson.OPT_INDENT_2).decode())

        assert len(rendered['relations']) > 0
        document_reference = next(iter([_ for _ in rendered['relations'] if _['dst_name'] == 'document_reference']), None)
        assert document_reference, "Should render DocumentReference relation"
