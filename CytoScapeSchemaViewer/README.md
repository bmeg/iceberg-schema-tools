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

## FHIR-BMEG Unified schema viewer:

The schema.py file is currently setup to generate a graph for the unified schema.
Run the below commands to view the schema. Note: python schema.py yaml_dir looks at the ACED_BMEG_Unified to generate a
output file that is read by the cytoscape schema viewer in public/data/graph.json
```
cd CytoScapeSchemaViewer
python schema.py yaml_dir
export NODE_OPTIONS=--openssl-legacy-provider
npm i
npm start
```

## BMEG schema viewer update steps
These commands aren't needed since the ACED_BMEG_Unified directory got committed
```
wget https://github.com/bmeg/bmeg-etl/archive/refs/heads/develop.zip
unzip develop.zip
mkdir yaml_schemas
mv bmeg-etl-develop/schema/* yaml_schemas
rm -rf bmeg-etl-develop
rm -f develop.zip
```

# Development:

The schema viewer looks for a file at:
CytoScapeSchemaViewer/public/data/graph.json
