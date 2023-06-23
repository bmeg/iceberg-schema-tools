from fhir.resources.documentreference import DocumentReference
from fhir.resources.patient import Patient, PatientLink, PatientCommunication
from fhir.resources.task import Task

from iceberg_tools.schema import _find_fhir_classes, _extract_schemas, BASE_URI


def test_find_fhir_classes():
    """Assert we find classes descending from Patient."""
    classes = _find_fhir_classes({'dependency_order': ['Patient']})
    expected_classes = [Patient, PatientLink, PatientCommunication]
    for _ in expected_classes:
        assert _ in classes, ('No find', _)


def test_schemas():
    """Assert we find schemas descending from Patient."""
    classes = _find_fhir_classes({'dependency_order': ['Patient']})
    schemas = _extract_schemas(classes, BASE_URI)
    expected_classes = ['Patient', 'PatientLink', 'PatientCommunication']
    for _ in expected_classes:
        assert _ in schemas, ('No find expected class', _)

    patient = schemas['Patient']
    assert patient['$id'] == 'Patient'
    assert 'Disclaimer' not in patient['description'], "Did not edit vertex description"


def test_bindings():
    """Ensure bindings are attached to expected properties."""
    schemas = _extract_schemas([Patient], BASE_URI)
    patient = schemas['Patient']
    gender = patient['properties']['gender']
    expected_property_attributes = ['type', 'binding_strength', 'binding_description', 'binding_uri', 'enum_values']
    for _ in expected_property_attributes:
        assert _ in gender, ('Did not find binding. Missing attribute in Patient.gender', _)


def test_backref():
    """Test simple and itemized backref."""
    schemas = _extract_schemas([Task], BASE_URI)
    assert 'Task' in schemas, "Should have found Task"

    task = schemas['Task']
    expected_references_with_itemized_backref = ['focus', 'owner', 'requester']
    for _ in expected_references_with_itemized_backref:
        assert _ in task['properties'], task['properties'].keys()
        assert task['properties'][_]['backref'] == f'{_}_task', "Should have itemized backref"
    expected_references_with_simple_backref = ['location']
    for _ in expected_references_with_simple_backref:
        assert task['properties'][_]['backref'] == 'task', "Should have simple backref"


def test_backref_array():
    """Test simple and itemized backref."""
    schemas = _extract_schemas([DocumentReference], BASE_URI)
    assert 'DocumentReference' in schemas, "Should have found DocumentReference"

    document_reference = schemas['DocumentReference']
    # select property that is a list of references.
    author = document_reference['properties']['author']
    print(author)
    assert 'backref' in author, "lists of References should have a backref"


def test_task():
    """Test CodeableReference."""
    schemas = _extract_schemas([Task], BASE_URI)
    assert 'Task' in schemas, "Should have found Task"

    task = schemas['Task']
    # select property that is a CodeableReference.
    requested_performer = task['properties']['requestedPerformer']
    print(requested_performer)
    assert 'backref' in requested_performer, "requested_performer should have a backref"
