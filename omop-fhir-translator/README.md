# FHIR to OMOP translator

## Startup

Setup python env
```
python3 -m venv venv ; source venv/bin/activate
pip install -r requirements.txt
```
### Setup Redivis API creds
EDIT: This step isn't needed anymore. The actual data that is 
used are the best files from 3 different datasets.

go to https://redivis.com/
make an account and generate an API token.

Store the token in extract/.env file. Use extract/.example_env as a template.

create the data folder and extract study data into it with:
```
mkdir data
cd extract
python extract/redivis_extract.py
```
downloads full tables  for concept, person, provider.

## Setup Go dependancies and packages: 
Install GO (at least Go 1.19): https://go.dev/dl/
 
### Sifter / Lathe
```
go install github.com/bmeg/sifter@main
go install github.com/bmeg/lathe@latest
```
### Iceberg Setup
make sure that your iceberg is updated to FHIR version 5. If it is not 
there will be validation errors. If it is updated, there might still be validation errors

### Update path
```
export PATH=$PATH:$HOME/go/bin
```
### clean redivis data
to get person.json files that are valid you need to run 
data_cleaner.py and take the outputed file and replace it with data/person.json

## Convert OMOP -> FHIR
Build Snakefile
```
lathe plan plan_omop_to_fhir.yaml
```
Run build
```
snakemake -j -4
```

## CONVERT FHIR -> OMOP
Build Snakefile 
```
lathe plan plan_fhir_to_omop.yaml
```
Run build
```
snakemake -j -4
```

## INIDIVIDUAL TRANSLATIONS

You can do an individual file translation of the data with a
```
sifter run [path to config.yaml file]
```