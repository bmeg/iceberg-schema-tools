import logging
import sys
import orjson
import json
import uuid
import aiofiles
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
ACED_NAMESPACE = uuid.uuid3(uuid.NAMESPACE_DNS, 'aced-ipd.org')


def body_structure_uuid(input_str):
    return str(uuid.uuid5(ACED_NAMESPACE, input_str))


async def build_anatomic_site_table(file_path):
    async with aiofiles.open(file_path) as fp:
        async for line in fp:

            augmented_line = orjson.loads(line)
            body_structure_id = str(augmented_line["anatomic_site_concept_id"])
            if body_structure_id == "None":
                continue

            person_id = str(augmented_line["person_id"])
            spliot = str(augmented_line["specimen_datetime"]).split(" ")
            date = spliot[0] + "T" + spliot[1] + "+00:00"

            new_dict = {
                # id probably not unique enough
                "id": body_structure_uuid(person_id + "-" + body_structure_id + "-" + date),
                "identifier": [
                    {
                        "system": "https://redivis.com/datasets/ye2v-6skh7wdr7/tables",
                        "value": "Procedure/" + str(person_id)
                    }
                ],
                "resourceType": "BodyStructure",
                "patient": {"reference": "Patient/" + person_id},
                "includedStructure": [{
                    "structure": {
                        "coding": [{
                            "system": ""
                        }],
                    },
                }],
                "value": body_structure_id
            }

            print(json.dumps(new_dict))


if __name__ == "__main__":
    asyncio.run(build_anatomic_site_table(sys.argv[1]))
