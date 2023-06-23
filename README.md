# iceberg-schema-tools
Create and maintain central iceberg schema.  Render and validate FHIR data.

## Overview

![image](https://github.com/bmeg/iceberg-schema-tools/assets/47808/cf5f544c-081f-470f-b1d8-27f16ad21b67)



Code that generates the base schema from FHIR goes here.  Additional tools are provided to lints, validates and visualize the schema.

Note: The actual schemas are stored in [iceberg](https://github.com/bmeg/iceberg)


## Setup

```
pip install iceberg-tools
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

$ iceberg data

Usage: iceberg data [OPTIONS] COMMAND [ARGS]...

  Project data (ResearchStudy, ResearchSubjects, Patient, etc.).

Options:
  --help  Show this message and exit.

Commands:
  simplify             Renders PFB friendly flattened records.
  validate             Check FHIR data for validity and conventions.
  validate-simplified  Check simplified data for validity and conventions.
  pfb                  Write simplified FHIR files to a PFB.
  migrate              Migrate from FHIR R4B to R5.0.
  report               Aggregate avro pfb files into a cytoscape tsv.

```

> Note: `pfb_fhir` and `iceberg` are synonymous in this context.

## Examples

The commands:
```commandline
pfb_fhir schema generate simplified
pfb_fhir data simplify --schema_path  iceberg/schemas/simplified/simplified-fhir.json tests/fixtures/simplify/study/ tmp/simplified
pfb_fhir data pfb tmp/simplified/ tmp/study.pfb
tree tmp

```

Will generate the following output:
```commandline
INFO:'Records with relationships': 59413
INFO:'Records': 59460
tmp
├── simplified
│   ├── Condition.ndjson
│   ├── DocumentReference.ndjson
│   ├── Encounter.ndjson
│   ├── MedicationAdministration.ndjson
│   ├── Observation.ndjson
│   ├── Patient.ndjson
│   ├── ResearchStudy.ndjson
│   ├── ResearchSubject.ndjson
│   ├── Specimen.ndjson
│   └── Task.ndjson
└── study.pfb

```

## Contributing
See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for developer notes.
