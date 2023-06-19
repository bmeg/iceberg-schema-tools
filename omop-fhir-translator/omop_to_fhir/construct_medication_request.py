import aiofiles
import json
import gzip
import asyncio
import sys
import uuid 

ACED_NAMESPACE = uuid.uuid3(uuid.NAMESPACE_DNS, 'aced-ipd.org')

def person_uuid(input_str):
    return str(uuid.uuid5(ACED_NAMESPACE, input_str))

def is_int(num):
    try:
        int(num)
        return True
    except ValueError:
        return False

async def get_files(input_file):
   # async with aiofiles.open(output_file,mode="w") as w:
    async with aiofiles.open(input_file, mode='r') as f:
        async for line in f:
            out = formulate_med_req(json.loads(line))
            if out == None:
                continue
            print(json.dumps(out))
            #await w.write(str(json.dumps(out)))
            #await w.write("\n")
            #await w.flush()


def formulate_med_req(row):
    if not (("sig" in row and row["sig"] is not None) or\
        ("route_concept_id" in row and row["route_concept_id"] is not None) or\
        ("refills" in row and row["refills"] is not None) or\
        ("quanitity" in row and row["quantity"] is not None) or\
        ("days_supply" in row and row["days_supply"] is not None) or\
        ("verbatim_end_date" in row and row["verbatim_end_date"] is not None)):
        return None
    
    out = {
        "id": str(str(row["drug_exposure_id"])),
        "identifier":[
            { 
            "system": "https://redivis.com/datasets/ye2v-6skh7wdr7/tables",
            "value": "MedicationRequest/" + str(row["drug_exposure_id"])
            },
            { 
            "system": "https://redivis.com/datasets/ye2v-6skh7wdr7/tables",
            "value": "Patient/" + str(row["person_id"])
            }

        ],
          #this is for uuid setup later
        "resourceType": "MedicationRequest",
        "status": "stopped", #don't think there is anything for this in the OMOP structure
        "subject": {"reference":"Patient/" + person_uuid(str(row["person_id"]))},
        "intent": "order", # Not sure what to put here
        "drug_concept_id":row["drug_concept_id"]

    }

    if (("sig" in row and row["sig"] is not None) or ("route_concept_id" in row and row["route_concept_id"] is not None)):
        out["dosageInstruction"] = []
        if (("sig" in row and row["sig"] is not None) and ("route_concept_id" in row and row["rout_concept_id"] is not None)):
            out["dosageInstruction"].append({
                "text":row["sig"],
                "route":{
                "coding":[{
                    "display":"filler",
                    "code":row["route_concept_id"],
                    "system":"filler"
                }],
                "text":"filler"
                }
            })
        elif ("sig" in row and row["sig"] is not None):
            out["dosageInstruction"].append({
            "text":row["sig"]
            })
        elif ("route_concept_id" in row and row["route_concept_id"] is not None):
            out["dosageInstruction"].append({
                "route":{
                "coding":[{
                    "display":"filler",
                    "code":row["route_concept_id"],
                    "system":"filler"
                }],
                "text":"filler"
                }
            })
    if (("refills" in row and row["refills"] is not None) or ("quanitity" in row and row["quantity"] is not None) or ("days_supply" in row and row["days_supply"] is not None)):
        if ("refills" in row and row["refills"] is not None):
            out["dispenseRequest"]["numberOfRepeatsAllowed"] = int(row["refills"])
        if ("quantity" in row and row["quantity"] is not None):
            out["dispenseRequest"] = {}
            out["dispenseRequest"]["quantity"] = row["quantity"]
        if ("days_supply" in row and row["days_supply"] is not None):
            out["dispenseRequest"] = {}
            out["dispenseRequest"]["expectedSupplyDuration"] = {"value": row["days_supply"]}
    
    if "provider_id" in row and row["provider_id"] is not None:
        if(is_int(row["provider_id"])):
            out["requester"] = [{"reference":"Practitioner/" + str(int(row["provider_id"]))}]
        else:
            out["requester"] = [{"reference":"Practitioner/" + str(row["provider_id"])}]
    
    #TODO: reformat the date to something that passes FHIR. This is an optional field so might just bake it
    # into this code
    if "verbatim_end_date" in row and row["verbatim_end_date"] is not None:
        out["validityPeriod"] = {
            "end": row["verbatim_end_date"]
        }

    return out


asyncio.run(get_files(sys.argv[1]))
#output/drug_exposure_omop_to_fhir.MedicationStatement.MedicationStatement.json