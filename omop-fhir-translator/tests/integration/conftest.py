import pathlib
from typing import List

import pytest


@pytest.fixture
def output_path() -> pathlib.Path:
    """Path to output data."""
    return pathlib.Path('output/')


@pytest.fixture
def expected_files() -> List[str]:
    return """visit_occurence_omop_to_fhir.Encounter.Encounter.json.gz 
    condition_occurance_omop_to_fhir.Condition.Condition.json.gz 
    device_exposure_omop_to_fhir.Procedure.Procedure.json.gz 
    drug_exposure_omop_to_fhir.MedicationRequest.MedicationRequest.json.gz 
    drug_exposure_omop_to_fhir.MedicationStatement.MedicationStatement.json.gz 
    measurement_omop_to_fhir.measurement.Observation.json.gz 
    observation_omop_to_fhir.observation.Observation.json.gz 
    patient_omop_to_fhir.Patient.Patient.json.gz 
    procedure_occurrence_omop_to_fhir.Procedure.Procedure.json.gz 
    specimen_omop_to_fhir.Anatomic_Site.BodyStructure.json.gz 
    specimen_omop_to_fhir.Specimen.Specimen.json.gz
    """.split()

@pytest.fixture
def test_uuids() -> List[str]:
    return """visit_occurence_omop_to_fhir.Encounter.Encounter.json.gz 
    condition_occurance_omop_to_fhir.Condition.Condition.json.gz 
    device_exposure_omop_to_fhir.Procedure.Procedure.json.gz 
    drug_exposure_omop_to_fhir.MedicationRequest.MedicationRequest.json.gz 
    drug_exposure_omop_to_fhir.MedicationStatement.MedicationStatement.json.gz 
    measurement_omop_to_fhir.measurement.Observation.json.gz 
    observation_omop_to_fhir.observation.Observation.json.gz 
    patient_omop_to_fhir.Patient.Patient.json.gz 
    procedure_occurrence_omop_to_fhir.Procedure.Procedure.json.gz 
    specimen_omop_to_fhir.Anatomic_Site.BodyStructure.json.gz 
    specimen_omop_to_fhir.Specimen.Specimen.json.gz
    """.split()

@pytest.fixture
def tested_edge_files() -> List[str]:
    return """
    observation_omop_to_fhir.observation.Observation.json.gz 
    patient_omop_to_fhir.Patient.Patient.json.gz 
    """.split()

@pytest.fixture
def test_encounter_edges() -> List[str]:
    return """visit_occurence_omop_to_fhir.Encounter.Encounter.json.gz
    patient_omop_to_fhir.Patient.Patient.json.gz
    """.split()

@pytest.fixture
def test_specimen_edges() -> List[str]:
    return """specimen_omop_to_fhir.Specimen.Specimen.json.gz
    patient_omop_to_fhir.Patient.Patient.json.gz
    """.split()