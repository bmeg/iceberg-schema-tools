import ndjson

input_file = "../mimic-iv-omop-data/visit_occurrence.json"
output_file = "new_format_visit_occurrence.json"

with open(input_file, "r") as f:
    data = ndjson.load(f)

for dictionary in data:
    dictionary_uppercase = {key.upper(): value for key, value in dictionary.items()}
    dictionary.clear()
    dictionary.update(dictionary_uppercase)

with open(output_file, "w") as f:
    ndjson.dump(data, f)