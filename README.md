# iceberg-schema-tools
Create and maintain central iceberg schema.

## Overview

![image](https://user-images.githubusercontent.com/47808/233504556-498adff7-428d-4fa3-b534-937802cb6af4.png)


Code that generates the base schema from FHIR goes here.  Additional tools are provided to lints, validates and visualize the schema.

Note: The actual schemas are stored in [iceberg](https://github.com/bmeg/iceberg)


## Setup

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```


## Use

```
$ iceberg schema
Usage: iceberg schema [OPTIONS] COMMAND [ARGS]...

  Manage bmeg or gen3 schemas from FHIR resources.

Options:
  --help  Show this message and exit.

Commands:
  generate  Generate from FHIR resources.
  compile   Create aggregated json file from individual yaml schemas
  publish   Copy dictionary to s3 (note:aws cli dependency)

$ iceberg data

Usage: iceberg data [OPTIONS] COMMAND [ARGS]...

  Project data (ResearchStudy, ResearchSubjects, Patient, etc.).

Options:
  --help  Show this message and exit.

Commands:
  simplify       Renders Gen3 friendly flattened records.
  validate       Check FHIR data for validity and ACED conventions.
  validate-gen3  Check Gen3 data for validity and ACED conventions.
  pfb            Write simplified FHIR files to a PFB.
  migrate        Migrate from FHIR R4B to R5.0.

```


## Testing

```
pip install -r requirements-dev.txt
pytest --cov
---
86%

```

## Contributing

```
pre-commit install
```

## Distribution

- PyPi

```
# update pypi

# pypi credentials - see https://twine.readthedocs.io/en/stable/#environment-variables

export TWINE_USERNAME=  #  the username to use for authentication to the repository.
export TWINE_PASSWORD=  # the password to use for authentication to the repository.

# this could be maintained as so: export $(cat .env | xargs)

rm -r dist/
python3  setup.py sdist bdist_wheel
twine upload dist/*
```
