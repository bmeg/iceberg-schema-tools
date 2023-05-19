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
$ iceberg
Usage: iceberg [OPTIONS] COMMAND [ARGS]...

  Manage schemas.

Options:
  --help  Show this message and exit.

Commands:
  compile   Create aggregated json file from individual yaml schemas
  generate  Generate bmeg or gen3 FHIR based schemas
  publish   Copy dictionary to s3 (note:aws cli dependency)

```


## Testing

```
pip install -r requirements-dev.txt
pytest --cov
---
83%

```

## Contributing

```
pre-commit install
```
