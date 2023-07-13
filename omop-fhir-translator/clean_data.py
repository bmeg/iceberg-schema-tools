import csv
import json
import ndjson
import click
import pathlib
import os
import tqdm as tqdm
import ndjson

#should also write something that converts all fake floats like "876545676543.0" to ints 

#convert everything to lowercase keys and strip the whitesapce
def lowercase_keys_strip(data):
    if isinstance(data, dict):
        return {key.lower(): lowercase_keys_strip(str(value).strip()) if (value != "0" and value != "None" and value != None) else None for key, value in data.items()}
    if isinstance(data, list):
        return [lowercase_keys_strip(item) for item in data]
    return data

def run_lower_case_keys(input_file_path,output_file_path):
    with open(input_file_path, 'r') as file:
        ndjson_data = ndjson.load(file)
    lowercased_data = lowercase_keys_strip(ndjson_data)
    with open(output_file_path, 'w') as file:
        ndjson.dump(lowercased_data, file)

def convert_csv_to_ndjson(input_file_path,output_file_path):
    writefile = open(output_file_path, 'w')
    with open(input_file_path) as f:
        reader_list = csv.DictReader(f, delimiter=",")
        print(f"COUNTING TOTAL ROWS IN FILE {input_file_path}")
        totalrows = 0
        for row in reader_list:
            totalrows += 1
        print(f" TOTAL ROWS ARE {totalrows}")
        f.seek(0)
        reader_list = csv.DictReader(f, delimiter=",")
        for rorw in tqdm.tqdm(reader_list,total=totalrows):
            for elem in rorw.keys():
                if rorw[elem] == '':
                    rorw[elem] = "None"
            json.dump(rorw, writefile)
            writefile.write('\n')


# ex: python helper-script.py clean csv --input_path ../r_script_data/condition_occurrence.csv --output_path new_data.ndjson
@click.group()
def cli():
    """Manage schemas."""
    pass

@cli.group('clean')
def clean():
    """clean data"""
    pass

@clean.command('csv')
@click.option('--input_path', required=True,
              help='Path to input csv file')
@click.option('--output_path', required=True,
              help='Path to output ndjson file')
def clean_csv(input_path, output_path):
    input_path = pathlib.Path(input_path)
    assert input_path.is_file()
    convert_csv_to_ndjson(input_path,f'{input_path}.temp')
    run_lower_case_keys(f'{input_path}.temp',output_path)
    os.unlink(f'{input_path}.temp')

@clean.command('json')
@click.option('--input_path', required=True,
              help='Path to input csv file')
@click.option('--output_path', required=True,
              help='Path to output ndjson file')
def clean_json(input_path, output_path):
    input_path = pathlib.Path(input_path)
    assert input_path.is_file()
    run_lower_case_keys(input_path,output_path)


@clean.command("Jupper")
@click.option('--input_path', required=True,
              help='Path to input csv file')
@click.option('--output_path', required=True,
              help='Path to output ndjson file')
def JsonKeyUpper(input_path,output_path):
    with open(input_path, "r") as f:
        data = ndjson.load(f)

    for dictionary in data:
        dictionary_uppercase = {key.upper(): value for key, value in dictionary.items()}
        dictionary.clear()
        dictionary.update(dictionary_uppercase)

    with open(output_path, "w") as f:
        ndjson.dump(data, f)


@clean.command('directory')
@click.option('--directory_location', required=True,
              help='Path to directory of csvs')
def clean_DirectoryOfCsv(directory_location):
    directory_path = pathlib.Path(directory_location)
    assert directory_path.is_dir()
    for file_path in enumerate(os.listdir(directory_path)):
        clean_csv(file_path,f"{file_path}.cleaned.ndjson")

#for building a limited concept table to trim down the number of unnecessary columns
# and make it easier to work with
# ex: python clean_data.py build concepts --input_path ../data/MASTER_CONCEPT_TABLE.csv --output_path ../data/MASTER_CONCEPT_TABLE_NEW_TEST.json
@cli.group('build')
def build():
    """clean data"""
    pass

@build.command('concepts')
@click.option('--input_path', required=True,
              help='Path to input csv file')
@click.option('--output_path', required=True,
              help='Path to output ndjson file')
def build_concepts(input_path, output_path):
    writefile = open(output_path, 'w')
    with open(input_path) as f:
        reader_list = csv.DictReader(f, delimiter="\t")
        print(f"COUNTING TOTAL ROWS IN FILE {input_path}")
        totalrows = 0
        for row in reader_list:
            totalrows += 1
        print(f" TOTAL ROWS ARE {totalrows}")
        f.seek(0)
        for rorw in tqdm.tqdm(reader_list, total=totalrows):
            for elem in rorw.keys():
                if rorw[elem] == '':
                    rorw[elem] = None

            # change this to be whatever rows you want to include in your concept table
            mew = {
                "concept_id": rorw["concept_id"],
                "vocabulary_id": rorw["vocabulary_id"],
                "concept_name": rorw["concept_name"],
                "concept_class_id": rorw["concept_class_id"],
                "concept_code": rorw["concept_code"]
            }

            json.dump(mew, writefile)
            writefile.write('\n')


if __name__ == '__main__':
    cli()

