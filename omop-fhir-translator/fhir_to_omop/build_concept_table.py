import gzip
import logging
import sys
import orjson
import csv
import os
import multiprocessing as mp
import polars as pl
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# multiprocessing file IO adapted from https://stackoverflow.com/a/12293094
# will probably replace this with polars because it's faster

GENDER_MAPPINGS = {
    "female":"8532",
    "male":"8507",
    "unknown":"8551",
    "other":"8521"
}
RACE_MAPPINGS = {
    "1002-5":"8657",
    "2028-9":"8515",
    "2054-5":"8516",
    "2076-8":"8557",
    "2106-3":"8527"
}
ETHNICITY_MAPPINGS = {
    "2135-2":"38003563",
    "2186-5":"38003564"
}

def processfile(file, start=0, stop=0):
    with open(file, 'r') as fh:
        fh.seek(start)  # specify a stop
        lines = fh.readlines(stop - start)
        reader_list = csv.DictReader(
            lines,
            delimiter="\t",
            fieldnames=(
                "concept_id",
                "concept_name",
                "domain_id",
                "vocabulary_id",
                "concept_class_id",
                "standard_concept",
                "concept_code",
                "valid_start_date",
                "valid_end_date",
                "invalid_reason"))

        reader_list = [rlist for rlist in reader_list]
        set_values = {row["concept_id"]
                      for row in reader_list if "concept_id" in row}

    return set_values


def driver(filepath):
    filesize, split_size = os.path.getsize(filepath), 100 * 1024 * 1024
    if filesize > split_size:
        pool, total, cursor, results = mp.Pool(15), set(), 0, []
        with open(filepath, 'r') as fh:
            for chunk in range(filesize // split_size):
                if cursor + split_size > filesize:
                    end = filesize
                else:
                    end = cursor + split_size

                fh.seek(end)
                fh.readline()
                end = fh.tell()
                proc = pool.apply_async(
                    processfile, args=[
                        filepath, cursor, end])
                results.append(proc)
                cursor = end + 1

        pool.close()
        pool.join()
        for proc in results:
            processfile_result = proc.get()
            total.update(processfile_result)

        return total


def build_concepts_from_observations(
        file_path,
        file_path_two,
        file_path_three,
        file_path_four):
    # this concept table comes directly from
    # https://athena.ohdsi.org/vocabulary/list
    # and is a download of every single concept in every single vocabulary in

    with gzip.open(file_path) as fp, \
            gzip.open(file_path_two) as wp, \
            gzip.open(file_path_three) as tp, \
            gzip.open(file_path_four) as bl:

        observation_lines = fp.readlines()
        condition_lines = wp.readlines()
        patient_lines = tp.readlines()
        body_structure_lines = bl.readlines()

        set_values = driver("../data/MASTER_CONCEPT_TABLE.csv")
        #print(len(set_values))
        #print("SET VALUSE ",len(set_values))
       # print("NEW LEN ",len(list(set(set_values))))

        #pl.Config.set_tbl_rows(10000)
        """
        df = pl.scan_csv(
            "../data/MASTER_CONCEPT_TABLE.csv",
            separator="\t",
            new_columns=[
                "concept_id",
                "concept_name",
                "domain_id",
                "vocabulary_id",
                "concept_class_id",
                "standard_concept",
                "concept_code",
                "valid_start_date",
                "valid_end_date",
                "invalid_reason"])
        
        #new_val = pl.col("concept_id").collect()
        val  = df.select("concept_name").collect()
        print("POLARS LEN ",len(val))
        #values = df.select(pl.col(["concept_id"])).collect()
        #values = list(values)[0]
        #print("NEW _SET VALUES ",list(values)[0])
        exit()
        """
        observation_type_concept_ids = {orjson.loads(line.decode(
            'utf-8'))["category"][0]["coding"][0]["code"]
            for line in observation_lines}

        observation_concept_ids = {orjson.loads(line.decode(
            'utf-8'))["code"]["coding"][0]["code"]
            for line in observation_lines}

        observation_source_concept_ids = {orjson.loads(line.decode(
            'utf-8'))["category"][1]["coding"][0]["code"]
            for line in observation_lines}

        condition_type_concept_ids = {orjson.loads(line.decode(
            'utf-8'))["code"]["extension"][0]["valueString"]
            for line in condition_lines}

        condition_concept_ids = {orjson.loads(line.decode(
            'utf-8'))["code"]["coding"][0]["code"]
            for line in condition_lines}

        condition_source_concept_ids = {str(orjson.loads(line.decode('utf-8'))["extension"])
                                        .split("condition_source_concept_id', 'valueString': '")
                                        [-1].split("'}]")[0] for line in condition_lines}

        gender_ids = {str(orjson.loads(line.decode('utf-8'))
                          ["gender"]) for line in patient_lines}
        mapped_ethnicity_concept_ids = [GENDER_MAPPINGS[value] for value in gender_ids]

        ethnicity_concept_ids = {str(orjson.loads(line.decode(
            'utf-8'))["extension"][1]["extension"][0]["valueCoding"]["code"]) for line in patient_lines}
        mapped_ethnicity_concept_ids = [ETHNICITY_MAPPINGS[value] for value in ethnicity_concept_ids]
        
        race_concept_ids = {str(orjson.loads(line.decode(
            'utf-8'))["extension"][0]["extension"][0]["valueCoding"]["code"]) for line in patient_lines}
        mapped_race_concept_ids = [RACE_MAPPINGS[value] for value in race_concept_ids]

        body_structure_lines = {orjson.loads(line.decode(
            'utf-8'))["includedStructure"][0]["structure"]["coding"][0]["code"]
            for line in body_structure_lines}

        #TODO: need to write codes for measurement table reconstructions

        


        aggregated_id_list = [
            body_structure_lines,
            mapped_race_concept_ids,
            mapped_ethnicity_concept_ids,
            mapped_ethnicity_concept_ids,
            observation_type_concept_ids,
            observation_concept_ids,
            observation_source_concept_ids,
            condition_type_concept_ids,
            condition_concept_ids,
            condition_source_concept_ids]

        big_list = []
        for id_list in aggregated_id_list:
            #print(len(id_list), len(list(set_values.intersection(id_list))))
            big_list = big_list + list(set_values.intersection(id_list))

        df = pl.scan_csv(
            "../data/MASTER_CONCEPT_TABLE.csv",
            separator="\t",
            new_columns=[
                "concept_id",
                "concept_name",
                "domain_id",
                "vocabulary_id",
                "concept_class_id",
                "standard_concept",
                "concept_code",
                "valid_start_date",
                "valid_end_date",
                "invalid_reason"])

        dataframes = []

        new_val = df.filter(
            (pl.col("concept_id").cast(pl.Utf8).is_in(big_list))
        ).collect()
        if new_val is not None:
            dataframes.append(new_val)

        new_dataframes = pl.concat(dataframes)
        dict_repr = new_dataframes.to_dicts()

        for elem in dict_repr:
            print(json.dumps(elem))


if __name__ == "__main__":
    build_concepts_from_observations(
        sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
