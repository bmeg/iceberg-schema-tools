#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
wget https://raw.githubusercontent.com/bmeg/iceberg/main/schemas/bmeg/aced-bmeg.json
mkdir public/data
python3 schema.py onefile --input_path aced-bmeg.json
npm i
npm start