# Shell Setup:
Make sure you have Node Package Manager (npm) installed:
```
brew install node
```
or download and install at:
https://nodejs.org/en/download

Then run the below command to fetch the schema, run the python commands to transform the schema, and then setup and run the react frontend schema visualizer:

```
bash start_viewer.sh
```
## Python Setup
to run the simplified schema generation code:

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python schema.py cytoscape --input_path aced-bmeg.json
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
