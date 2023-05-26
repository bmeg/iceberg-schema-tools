from collections import defaultdict
from typing import Dict

import pathlib

import inflection
from fastavro import reader
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def recursive_default_dict() -> Dict:
    """Recursive default dict."""
    return defaultdict(recursive_default_dict)


def aggregate_edges(path, output_path, pattern):
    """Aggregate avro pfb files into a cytoscape friendly tsv."""
    aggregated_node_counts = defaultdict(dict)
    aggregated_edge_counts = recursive_default_dict()

    path = Path(path)
    for file_path in path.glob(pattern):
        with open(file_path, 'rb') as fo:
            logger.info(f"Reading {file_path}")
            avro_reader = reader(fo)
            for record in avro_reader:
                # skip metadata
                if record['name'] == 'Metadata':
                    continue

                if record['name'] not in aggregated_node_counts[file_path]:
                    aggregated_node_counts[file_path][record['name']] = 0
                aggregated_node_counts[file_path][record['name']] += 1

                for relation in record['relations']:
                    if relation['dst_name'] not in aggregated_edge_counts[record['name']]:
                        aggregated_edge_counts[record['name']][relation['dst_name']] = set()
                    aggregated_edge_counts[record['name']][relation['dst_name']].add(str(file_path))

    fn = pathlib.Path(output_path) / "aggregated_edge_counts.tsv"
    with open(fn, "w") as fp:
        print("source\ttarget\tsource_count\tedge_count", file=fp)
        for source in aggregated_edge_counts:
            for target in aggregated_edge_counts[source]:
                print(
                    f"{source}\t{target}\t{len(aggregated_edge_counts[source][target])}\t{len(aggregated_node_counts[source])}",
                    file=fp)
    logger.info(f"Wrote {fn}")

    fn = pathlib.Path(output_path) / "aggregated_node_counts.tsv"
    with open(fn, "w") as fp:
        print("file_path\tentity\tcount", file=fp)
        for file_path in aggregated_node_counts:
            for entity, count in aggregated_node_counts[file_path].items():
                print(f"{file_path}\t{entity}\t{count}", file=fp)
    logger.info(f"Wrote {fn}")

    pivot_aggregated_node_counts = defaultdict(dict)
    entity_names = set()
    file_names = set()
    for file_path in aggregated_node_counts:
        for entity, count in aggregated_node_counts[file_path].items():
            entity = inflection.camelize(entity)
            entity_names.add(entity)
            file_names.add(file_path.stem)
            pivot_aggregated_node_counts[entity][file_path.stem] = count

    entity_names = sorted(entity_names)
    file_names = sorted(file_names)
    rows = defaultdict(dict)
    for entity_name in entity_names:
        for file_name in file_names:
            if file_name not in pivot_aggregated_node_counts[entity_name]:
                rows[entity_name][file_name] = ''
            else:
                rows[entity_name][file_name] = pivot_aggregated_node_counts[entity_name][file_name]

    fn = pathlib.Path(output_path) / "pivoted_aggregated_node_counts.tsv"
    with open(fn, "w") as fp:
        headers = '\t'.join(['entity'] + file_names)
        print(headers, file=fp)
        for entity_name in rows:
            row = '\t'.join([entity_name] + [str(rows[entity_name][file_name]) for file_name in file_names])
            print(row, file=fp)
    logger.info(f"Wrote {fn}")
