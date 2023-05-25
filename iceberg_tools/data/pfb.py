import logging
import pathlib
import subprocess
from collections import defaultdict
from typing import List, Iterator, Any

from fastavro import reader
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def run_cmd(command_line) -> str:
    """Run a command line, return stdout."""
    try:
        logger.debug(command_line)
        return subprocess.check_output(command_line, shell=True).decode("utf-8").rstrip()
    except Exception as exc:
        logger.error(exc)
        raise exc


class EdgeSummary(BaseModel):
    """Summary of edge in PFB."""

    src: str = None
    dst: str = None
    count: int = 0


class EntitySummary(BaseModel):
    """Summary of entity in PFB."""

    name: str = None
    count: int = 0
    relationships: dict[str, EdgeSummary] = {}


class InspectionResults(BaseModel):
    """Results of PFB inspection."""

    errors: List[str] = []
    warnings: List[str] = []
    info: List[str] = []
    counts: dict[str, EntitySummary] = {}


def inspect_pfb(file_name) -> InspectionResults:
    """Show details of the pfb."""
    # TODO - simplify
    results = InspectionResults()
    # raw records
    records = []
    # TODO - should this be a generator?
    with open(file_name, 'rb') as fo:
        records = [record for record in reader(fo)]

    # ensure loaded in the correct order

    def recursive_default_dict():
        """Recursive default dict."""
        return defaultdict(recursive_default_dict)

    seen_already = set()

    def log_first_occurrence(obj_):
        seen_already.add(obj_['name'])

    def check_links(obj_, graph_) -> Iterator[str]:
        """Make sure relations from obj exist in graph."""
        assert 'relations' in obj_
        for r in obj_['relations']:
            if not graph_[r['dst_name']][r['dst_id']]:
                yield f"{r['dst_name']}.{r['dst_id']} referenced from {obj_['name']}.{obj_['id']} not found in Graph"

    graph = recursive_default_dict()

    for obj in records:
        log_first_occurrence(obj)
        graph[obj['name']][obj['id']] = obj
        for error in check_links(obj, graph):
            results.errors.append(error)

    # ensure no duplicates
    seen_already = set()

    def check_duplicates(obj_):
        if obj_['id'] in seen_already:
            yield f"Duplicate {obj_['name']}/{obj_['id']}"
        seen_already.add(obj_['id'])

    for obj in records:
        for error in check_duplicates(obj):
            results.errors.append(error)

    with_relations = [r for r in records if len(r['relations']) > 0]
    results.info.append(f"'Records with relationships': {len(with_relations)}")
    results.info.append(f"'Records': {len(records)}")

    assert len(records) > 1, f"Should have more than just metadata {file_name}"
    if len(with_relations) == 0:
        results.warnings.append("No records have relationships.")

    for obj in records:
        if obj['name'] not in results.counts:
            results.counts[obj['name']] = EntitySummary(name=obj['name'])
        summary = results.counts[obj['name']]
        summary.count += 1
        for r in obj['relations']:
            if r['dst_name'] not in summary.relationships:
                summary.relationships[r['dst_name']] = EdgeSummary(src=summary.name, dst=r['dst_name'])
            edge_summary = summary.relationships[r['dst_name']]
            edge_summary.count += 1

    return results


DEFAULT_DEPENDENCY_ORDER = """
_definitions.yaml
_terms.yaml
Program
Project
ResearchStudy
Patient
ResearchSubject
Substance
Specimen
Encounter
Observation
Condition
Medication
MedicationAdministration
DocumentReference
Task
FamilyMemberHistory
BodyStructure
""".split()


class SimplePFBWriter:
    """Create a PFB."""

    def __init__(self, schema_path: str, output_path: Any,
                 dependency_order: list[str] = DEFAULT_DEPENDENCY_ORDER):
        """Add schema to pfb file.

        see https://github.com/uc-cdis/pypfb/blob/d7cbb64813a9f1b9006a1ec0f92aa86962df2709/src/pfb/importers/gen3dict.py#L15
        """
        self.schema_path = schema_path

        if isinstance(output_path, str):
            output_path = pathlib.Path(output_path)
        output_path = output_path.expanduser()
        assert output_path.parent.is_dir(), f"{output_path.parent} is not a directory"
        self.output_path = output_path

        self.schema_written = False

        self.dependency_order = dependency_order

    def write_schema(self):
        """Create pfb file with the schema."""
        cmd = f"pfb from -o {self.output_path} dict {self.schema_path}"
        logger.info(f"Creating pfb file {self.output_path}  with schema read from: {self.output_path}")
        self.schema_written = True
        # TODO - We need to shell out to do this,  _from_dict is not public
        #  https://github.com/uc-cdis/pypfb/blob/master/src/pfb/importers/gen3dict.py#L29
        return run_cmd(cmd)

    def write(self, ndjson_file: str) -> str:
        """Add data to pfb file."""

        if not self.schema_written:
            self.write_schema()

        cmd = f"pfb add -i {ndjson_file} {self.output_path}"
        logger.info(f"Adding {ndjson_file}")
        # TODO - We need to shell out to do this,  _from_dict is not public
        #  https://github.com/uc-cdis/pypfb/blob/master/src/pfb/importers/gen3dict.py#L29
        return run_cmd(cmd)

    def inspect(self) -> InspectionResults:
        """Show details of the pfb."""
        return inspect_pfb(self.output_path)

    def transform_directory(self, input_path: Any) -> Iterator[str]:
        """Write json files from directory in order."""
        if isinstance(input_path, str):
            input_path = pathlib.Path(input_path)
        assert input_path.exists() and input_path.is_dir(), f"{input_path} should be a directory"
        write_order = []
        files = [_ for _ in input_path.glob('*.ndjson')]
        for _ in self.dependency_order:
            file = next(iter([n for n in files if f"{_}.ndjson" in str(n)]), None)
            if file:
                write_order.append(file)
        for file in write_order:
            yield self.write(file)
