#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
wget https://raw.githubusercontent.com/bmeg/iceberg/main/schemas/bmeg/aced-bmeg.json
python3 schema.py cytoscape --input_path aced-bmeg.json
npm i
npm start