
import json
import click
import pathlib
import orjson
import yaml
import glob
import os

ALL_ACED_NODES = """
    Organization
    Location
    Practitioner
    PractitionerRole
    ResearchStudy
    Patient
    ResearchSubject
    Substance
    Specimen
    Encounter
    Observation
    DiagnosticReport
    Condition
    Medication
    MedicationAdministration
    Procedure
    DocumentReference
    Task
    FamilyMemberHistory
    BodyStructure
    Immunization
    """.strip().split()

MAIN_ACED_NODES = """MedicationAdministration
    DocumentReference
    FamilyMemberHistory
    Observation
    Patient
    Substance
    DiagnosticReport
    Task
    Condition
    Encounter
    BodyStructure
    ResearchStudy
    Specimen
    Medication
    ResearchSubject""".strip().split()

ALL_BMEG_NODES = """
    Program
    Project
    Aliquot
    Allele
    AlleleEffect
    Case
    Command
    Compound
    CopyNumberAlteration
    DrugResponse
    Exon
    File
    Gene
    GeneExpression
    GeneOntologyTerm
    GenePhenotypeAssociation
    GeneSet
    GenomicFeature
    Interaction
    Methylation
    MethylationProbe
    Pathway
    Phenotype
    Protein
    ProteinCompoundAssociation
    ProteinStructure
    Publication
    Reference
    Sample
    SomaticCallset
    SomaticVariant
    Transcript
    TranscriptExpression""".strip().split()


def is_edge(name, schema) -> bool:
    return "backref" in str(schema) and\
           "enum_reference_types" in str(schema) and\
           name is not None


def recursive_items(dictionary):
    for key, value in dictionary.items():
        if isinstance(value, dict):
            yield from recursive_items(value)
        else:
            yield (key, value)


def convert_file_to_title(file):
    file = file.split('.yaml')[0]
    if "_" in file:
        file = file.split("_")
        for i, _ in enumerate(file):
            file[i] = file[i].title()
        file = "".join(file)
    else:
        file = file.capitalize()

    return file

@click.group()
def cli():
    pass


@cli.command('onefile')
@click.option('--input_path', required=True,
              default='generate-json-schema/coherent.json',
              show_default=True,
              help='Path to schema files'
              )
@click.option('--output_path', required=True,
              default='public/data',
              show_default=True,
              help='Path to cytoscape files'
              )
def onefile(input_path, output_path):
    """Extract a .json file that works with Cytoscape JS package"""
    # python3 schema.py onefile --input_path aced-bmeg.json

    input_path = pathlib.Path(input_path)
    output_path = pathlib.Path(output_path)
    assert input_path.is_file()
    assert output_path.is_dir()

    with open(input_path) as fp:
        schema = json.load(fp)

    edges = [(name, edge) for name, edge in schema["$defs"].items() if is_edge(name, edge)]
    nodes = [{"data": {"id": elem}} for elem in MAIN_ACED_NODES]
    fn = output_path / pathlib.Path('graph.json')

    with open(fn, 'wb') as tsv_file:
        tsv_file.write(b"[")

        for name, edge in edges:
            if name in ALL_ACED_NODES:
                name_dict = [item for item in nodes if item["data"]["id"] == name][0]
                name_dict["data"]["properties"] = list(edge["properties"].keys())
                tsv_file.write(orjson.dumps(name_dict))
                tsv_file.write(b",")

            for key, value in recursive_items(edge):
                if "enum_reference_types" in key:
                    for elem in value:
                        if name in ALL_ACED_NODES and elem in ALL_ACED_NODES:
                            tsv_file.write(orjson.dumps({"data": {"source": name, "target": elem}}))
                            tsv_file.write(b",")

        tsv_file.seek(-1, 2)
        tsv_file.truncate()
        tsv_file.write(b"]")


@cli.command('yaml_dir')
@click.option('--input_path', required=True,
              default='generate-json-schema/coherent.json',
              show_default=True,
              help='Path to schema files directory'
              )
@click.option('--output_path', required=True,
              default='public/data',
              show_default=True,
              help='Path to cytoscape files directory'
              )
def yaml_dir(input_path, output_path):
    """
    Extract a SIF file for import into cytoscape.
    python schema.py cytoscape --input_path aced-bmeg.json --output_path output
    JS expects the resultant schema file to be placed in public/data
    """

    input_path = pathlib.Path(input_path)
    output_path = pathlib.Path(output_path)
    assert input_path.is_dir()
    assert output_path.is_dir()

    paths = [file for file in glob.glob(os.path.join(input_path, "*.yaml")) if file.split("/")[-1][0] != "_"]
    nodes = [{"data": {"id": elem}} for elem in ALL_BMEG_NODES]
    fn = output_path / pathlib.Path('graph.json')

    with open(fn, 'wb') as tsv_file:
        tsv_file.write(b"[")
        for path in paths:
            with open(path, "r") as file:
                schema = yaml.safe_load(file)
                if "links" in schema:
                    edges = [edge for edge in schema["links"]]
                # print("EDGES", edges, "VERTEX  NAME", schema["$id"])
                if schema["title"] in ALL_BMEG_NODES:
                    name_dict = [item for item in nodes if item["data"]["id"] == schema["title"]][0]
                    #print("NAME DICT", name_dict)
                    edge = list(schema["properties"].keys())
                    #print("EDGE: ", edge, "TYPE EDGE", type(edge))
                    name_dict["data"]["properties"] = edge
                    tsv_file.write(orjson.dumps(name_dict))
                    tsv_file.write(b",")

                for edge in edges:
                    print("ENTERING EDGE GENERATION FOR EDGE: ", edge)
                    for key, value in recursive_items(edge):
                        print("KEY: ", key, "VALUE: ", value)
                        if "$ref" in key:
                            if schema["title"] in ALL_BMEG_NODES:
                                tsv_file.write(orjson.dumps({"data": {"source": schema["title"], "target": convert_file_to_title(value)}}))
                                tsv_file.write(b",")

        tsv_file.seek(-1, 2)
        tsv_file.truncate()
        tsv_file.write(b"]")


if __name__ == '__main__':
    cli()
