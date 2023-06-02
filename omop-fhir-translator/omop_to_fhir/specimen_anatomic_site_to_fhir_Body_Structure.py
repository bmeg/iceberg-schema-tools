import logging
import sys
import orjson
import json
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# multiprocessing file IO adapted from https://stackoverflow.com/a/12293094
# will probably replace this with polars because it's faster

ACED_NAMESPACE = uuid.uuid3(uuid.NAMESPACE_DNS, 'aced-ipd.org')


def body_structure_uuid(input_str):
    return str(uuid.uuid5(ACED_NAMESPACE, input_str))


def build_concepts_from_observations(file_path):
    # this concept table comes directly from
    # https://athena.ohdsi.org/vocabulary/list
    # and is a download of every single concept in every single vocabulary in

    with open(file_path) as fp:
        observation_lines = fp.readlines()

        patient_ids = [str(orjson.loads(line)["person_id"])
                       for line in observation_lines]
        body_structure_ids = [str(orjson.loads(
            line)["anatomic_site_concept_id"]) for line in observation_lines]
        # print("THE VALUE OF BODY STRUCTURE IDS ",body_structure_ids)

        dates = []
        for line in observation_lines:
            spliot = str(orjson.loads(line)["specimen_datetime"]).split(" ")
            dates.append(spliot[0] + "T" + spliot[1] + "+00:00")

        # print("THE VALUE OF DATES ",dates)

        # not sure if intersections are needed since
        # these codes are coming from OMOP
        # intersections = set_values.intersection(body_structure_ids)
        for i, value in enumerate(list(body_structure_ids)):
            new_dict = {
                # id probably not unique enough
                "id": body_structure_uuid(str(patient_ids[body_structure_ids.index(
                          value)]) + "-" + value + "-" + str(dates[i])),
                "resourceType": "BodyStructure",
                "patient": {"reference": "Patient/" + str(
                             patient_ids[body_structure_ids.index(value)])},
                "includedStructure": [{
                    "structure": {
                        "coding": [{
                            "system": "http://snomed.info/sct"
                        }],
                    },
                }],
                "value":value
            }

            if value != "None":
                new_dict["includedStructure"][0]["structure"]["coding"][0]["code"] = str(
                    value)
                new_dict["includedStructure"][0]["structure"]["coding"][0]["display"] = str(
                    value)

            print(json.dumps(new_dict))


if __name__ == "__main__":
    build_concepts_from_observations(sys.argv[1])
