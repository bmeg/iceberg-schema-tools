import gzip
import importlib
import io
import pathlib
from typing import List
import random
import uuid

import orjson
from fhir.resources import FHIRAbstractModel
from fhir.resources.coding import Coding
from fhir.resources.identifier import Identifier

FHIR_MODULE = importlib.import_module('fhir.resources')


def test_expected_files(output_path: pathlib.Path, expected_files: List[str]):
    """Ensure file exists"""
    assert all(
        [pathlib.Path(output_path / expected_file).is_file() for expected_file in expected_files]
    )


def _is_ndjson(file_path: pathlib.Path) -> bool:
    """Open file, read all lines as json."""
    fp = _to_file(file_path)

    try:
        with fp:
            for line in fp.readlines():
                orjson.loads(line)
        return True
    except Exception as e:
        print(file_path, e)
        return False


def _to_file(file_path):
    """Open file appropriately."""
    if file_path.name.endswith('gz'):
        fp = io.TextIOWrapper(io.BufferedReader(gzip.GzipFile(file_path)))
    else:
        fp = open(file_path, "rb")
    return fp


def test_valid_ndjson(output_path: pathlib.Path, expected_files: List[str]):
    """Ensure each file is valid json."""
    assert all(
        [_is_ndjson(pathlib.Path(output_path / expected_file)) for expected_file in expected_files]
    )


def _is_fhir(file_path: pathlib.Path) -> bool:
    """Open file, read all lines as fhir."""

    fp = _to_file(file_path)
    try:
        with fp:
            for line in fp.readlines():
                _to_fhir(line)

        return True
    except Exception as e:
        print(file_path, e)
        return False


def _to_fhir(json_string: str) -> FHIRAbstractModel:
    """Parse string to fhir resource."""
    resource = orjson.loads(json_string)
    assert 'resourceType' in resource, f"No 'resourceType' in {resource}"
    klass = FHIR_MODULE.get_fhir_model_class(resource['resourceType'])
    return klass.parse_obj(resource)


def test_valid_fhir(output_path: pathlib.Path, expected_files: List[str]):
    """Ensure each file is valid fhir."""
    truth_matrix = [_is_fhir(pathlib.Path(output_path / expected_file)) for expected_file in expected_files]
    print(zip(expected_files, truth_matrix))
    # print(truth_matrix)
    assert all(truth_matrix)


def _are_fhir_conventions_ok(file_path: pathlib.Path) -> bool:
    """Collect all CodeableConcepts in resource, ensure they meet conventions."""

    resource = None
    # This function didn't seem to agree very well to the way that systems are setup right now

    def _assert_no_special_characters(value: str, name: str):
        msg = ("see https://build.fhir.org/codesystem.html#invs key: cnl-1 "
               f"{name} should not contain | or # - these characters make processing canonical references problematic")
        assert '#' not in value and "|" not in value, (msg, value)
        msg = f"{name} should be a simple url without uuencoding"
        assert "%" not in value, (msg, value)

    def _check_coding(self: Coding, *args, **kwargs):
        # note `self` is the Coding
        assert self.code, f"Missing `code` {resource.id} {self}"
        assert (not self.code.startswith("http")), f"`code` should _not_ be a url http {self.code}"
        assert ":" not in self.code, f"`code` should not contain ':' {self.code}"
        assert self.system, f"Missing `system` {resource.id} {self}"
        # _assert_no_special_characters(self.system,  'system')
        assert self.display, f"Missing `display` {resource.id} {self}"
        return orig_coding_dict(self, *args, **kwargs)

    def _check_identifier(self: Identifier, *args, **kwargs):
        # note `self` is the Identifier
        assert self.value, f"Missing `value` {resource.id} {self}"
        assert self.system, f"Missing `system` {resource.id} {self}"
        # _assert_no_special_characters(self.system,  'system')
        # _assert_no_special_characters(self.value,  'value')
        return orig_identifier_dict(self, *args, **kwargs)

    # monkey patch dict() methods
    orig_coding_dict = Coding.dict
    Coding.dict = _check_coding

    orig_identifier_dict = Identifier.dict
    Identifier.dict = _check_identifier

    fp = _to_file(file_path)
    try:
        with fp:
            for line in fp.readlines():
                resource = _to_fhir(line)
                # trigger object traversal
                resource.dict()
        return True
    except AssertionError as e:
        print(file_path, e, resource)
        return False
    finally:
        # restore patches
        Coding.dict = orig_coding_dict
        Identifier.dict = orig_identifier_dict


def test_fhir_conventions(output_path: pathlib.Path, expected_files: List[str]):
    """Ensure each resource in each file, assure that all codeable concepts are valid."""

    assert all(
        [
            _are_fhir_conventions_ok(pathlib.Path(output_path / expected_file))
            for expected_file in expected_files
        ]
    )


def test_uuids(output_path: pathlib.Path, expected_files: List[str]):
    """Ensure each resource in each file, assure that all codeable concepts are valid."""

    # for ex in expected_files:
    # assert(_are_uuids_valid(pathlib.Path(output_path / ex)))
    # print(ex,"           ",_are_uuids_valid(pathlib.Path(output_path / ex)))

    assert all(
        [
            _are_uuids_valid(pathlib.Path(output_path / expected_file))
            for expected_file in expected_files
        ]
    )


def _are_uuids_valid(file_path: pathlib.Path) -> bool:
    """Randomly check 20 id's from each output file to see if they are UUIDs"""
    fp = _to_file(file_path)
    fp_list = fp.readlines()
    rand_list = random.sample(fp_list, 20)
    for entry in rand_list:
        line = orjson.loads(entry)
        print(line["id"])
        try:
            uuid.UUID(line["id"])
        except ValueError:
            return False

        if "subject" in line and "reference" in line["subject"]:
            print(file_path, str(line["subject"]["reference"]).split("/")[-1])
            try:
                uuid.UUID(str(line["subject"]["reference"]).split("/")[-1])
            except ValueError:
                return False

        if "encounter" in line and "reference" in line["encounter"]:
            print(file_path, str(line["encounter"]["reference"]).split("/")[-1])
            try:
                uuid.UUID(str(line["encounter"]["reference"]).split("/")[-1])
            except ValueError:
                return False

    return True


def _reference_exists(file_path_one, file_path_two):
    """randomly check 20 references to see if their ids exist in the referenced file"""
    patient_lines = "".join(_to_file(file_path_one).readlines())
    fp = _to_file(file_path_two)
    fp_list = fp.readlines()
    rand_list = random.sample(fp_list, 20)
    for entry in rand_list:
        line = str(orjson.loads(entry)["subject"]).split("/")[-1]
        if patient_lines.find(line):
            print(f"{file_path_one}/{file_path_two} EDGE: {line} EXISTS")
            continue
        else:
            return False
    return True


def _are_observation_patient_linkages_ok(file_path_observation, file_path_patient):
    """check observation -> patient linkages only"""
    try:
        return _reference_exists(file_path_patient, file_path_observation)
    except Exception:
        return False


def _are_specimen_edges_ok(file_path_specimen, file_path_patient):
    """check specimen -> patient linkages only"""

    try:
        return _reference_exists(file_path_patient, file_path_specimen)
    except Exception:
        return False


def _are_encounter_edges_ok(file_path_encounter, file_path_patient):
    """check encounter cycles and encounter -> patinet linages"""
    try:
        fp = _to_file(file_path_encounter).readlines()
        encounter_lines = "".join(fp)
        rand_list = random.sample(fp, 20)
        for entry in rand_list:
            line = str(orjson.loads(entry))
            if "PRECEDING_VISIT_OCCURRENCE_ID" in line:
                if encounter_lines.find(str(line["PRECEDING_VISIT_OCCURRENCE_ID"]).split("/")[-1]):
                    print(f"ENCOUNTER/PATIENT EDGE: {line} EXISTS")
                    continue
                else:
                    return False

        pp = _to_file(file_path_patient).readlines()
        patient_lines = "".join(pp)
        rand_list = random.sample(fp, 20)
        for entry in rand_list:
            line = str(orjson.loads(entry)["subject"]).split("/")[-1]
            if patient_lines.find(line):
                print(f"ENCOUNTER/PATIENT EDGE: {line} EXISTS")
                continue
            else:
                return False
        return True
    except Exception:
        return False


def test_specimen_edges(output_path: pathlib.Path, tested_edge_files: List[str]):
    """top level function to gather file appropriate filepaths from conftest"""
    assert _are_specimen_edges_ok(pathlib.Path(output_path / tested_edge_files[0]), pathlib.Path(output_path / tested_edge_files[1]))


def test_encounter_edges(output_path: pathlib.Path, test_encounter_edges: List[str]):
    """top level function to gather file appropriate filepaths from conftest"""
    assert (_are_encounter_edges_ok(pathlib.Path(output_path / test_encounter_edges[0]), pathlib.Path(output_path / test_encounter_edges[1])))


def test_observation_patient_linkages(output_path: pathlib.Path, tested_edge_files: List[str]):
    """top level function to gather file appropriate filepaths from conftest"""
    assert _are_observation_patient_linkages_ok(pathlib.Path(output_path / tested_edge_files[0]), pathlib.Path(output_path / tested_edge_files[1]))
