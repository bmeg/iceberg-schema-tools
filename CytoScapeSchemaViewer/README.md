# Shell Setup:
Make sure you have Node Package Manager (npm) installed:
```
brew install node
```
or download and install at:
https://nodejs.org/en/download

The below shell command runs a tutorial schema viewer script that relies on an aggregated FHIR schema definition file

```
bash start_example_viewer.sh
```
## Python Setup
to run the simplified schema generation code:

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Python schema generation commands
Commands only tested with FHIR schema data.

The below command will generate a FHIR graph from 1 aggregated FHIR schema file
```
python schema.py one_file --input_path aced-bmeg.json
```

Below are some commands to fetch the data and setup the schemas for graph visualization

```
wget https://github.com/bmeg/iceberg/archive/feature/itemize-gen3.zip
unzip itemize-gen3.zip
mkdir yaml_schemas
mv iceberg-feature-itemize-gen3/schemas/bmeg/* yaml_schemas
rm -rf iceberg-feature-itemize-gen3 
rm -f itemize-gen3.zip
```

The below command will generate a FHIR graph from however many schema.yaml files are in the directory specified:
```
python3 schema.py yaml_dir --input_path yaml_schemas
```

this will generate a json file at:
CytoScapeSchemaViewer/public/data/graph.json 

# Development:
A copy of the current schema can be retrieved from:
https://raw.githubusercontent.com/bmeg/iceberg/main/schemas/bmeg/aced-bmeg.json

To build and start the schema viewer run the below commands inside the CytoScapeSchemaViewer directory:
```
npm i
npm start
```
The schema viewer looks for a file at:
CytoScapeSchemaViewer/public/data/graph.json
