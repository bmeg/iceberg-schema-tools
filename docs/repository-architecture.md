# Repository Architecture Guide

This guide documents `iceberg-schema-tools` as three documentation tracks that align to the project’s major delivery targets.

- **Track A:** simplified use cases (`gen3`, `pfb`)
- **Track B:** vertex and edge graphs
- **Track C:** JSON Hypermedia links

## System Map

At a high level, the repository converts FHIR resources into schema artifacts and then uses those artifacts to transform data.

1. **Schema generation** (`iceberg schema ...`) creates either graph-oriented or simplified schemas.
2. **Data projection** (`iceberg data ...`) validates, simplifies, migrates, and exports data (including PFB).
3. **Graph/link semantics** are represented in schema links and consumed by downstream graph/ETL use cases.

Primary CLI groups:

- `iceberg schema` for schema lifecycle operations.
- `iceberg data` for runtime data projection and export operations.

---

## Track A — Simplified Use Cases (`gen3`, `pfb`)

### Purpose

The simplified track is for teams that want a flattened, implementation-friendly representation of FHIR data and compatible outputs for Gen3/PFB ecosystems.

### Core flow

1. Generate simplified schemas from FHIR and project config.
2. Compile aggregated schema (`simplified-fhir.json`).
3. Simplify source FHIR resources into NDJSON.
4. Validate simplified data.
5. Export simplified data to PFB.

Representative commands:

```bash
iceberg schema generate simplified --config_path config.yaml --output_path <schemas_dir>
iceberg schema compile simplified --output_path <schemas_dir>
iceberg data simplify --schema_path <schemas_dir>/simplified-fhir.json <fhir_input_dir> <simplified_output_dir>
iceberg data validate-simplified --schema_path <schemas_dir>/simplified-fhir.json <simplified_output_dir>
iceberg data pfb --schema_path <schemas_dir>/simplified-fhir.json --config_path config.yaml <simplified_output_dir> <output.pfb>
```

### Design notes

- `config.yaml` governs:
  - dependency order for parent-before-child writing (important for PFB writes),
  - nested-object plucking/denormalization,
  - extension behavior,
  - link limiting and extra target properties.
- Simplification behavior is implemented in `iceberg_tools.data.simplifier` and intentionally flattens selected structured FHIR fields.
- PFB export relies on simplified outputs and dependency ordering.

### Key modules

- `iceberg_tools/cli/schema.py` — simplified schema generation + compile commands.
- `iceberg_tools/cli/data.py` — simplify/validate-simplified/pfb commands.
- `iceberg_tools/data/simplifier/__init__.py` — flattening and reference extraction pipeline.
- `iceberg_tools/data/pfb.py` — `SimplePFBWriter` export path.
- `resources/static_gen3_fixtures/` — static dictionary fixtures used by simplified schema generation.

### Typical outputs

- YAML schema set for simplified resources (plus Gen3 scaffolding artifacts).
- Aggregated JSON schema (`simplified-fhir.json`).
- Simplified NDJSON per resource type.
- PFB file.

---

## Track B — Vertex and Edge Graphs

### Purpose

The graph track is for teams modeling data as typed vertices connected by typed edges. This track preserves graph semantics directly in generated schema link definitions.

### Core flow

1. Generate graph schemas from FHIR classes.
2. Inject graph links into each vertex schema.
3. Bundle individual YAML schemas into an aggregated JSON schema.

Representative command:

```bash
iceberg schema generate graph --config_path config.yaml --output_path <graph_schema_dir>
```

### Graph semantics in this repository

- A **vertex** is a resource schema (e.g., Patient, ResearchStudy, Specimen).
- An **edge** is represented as a link relation between source and target schema types.
- Link generation uses resource reference fields, project config constraints, and dependency order hints.

### Key modules

- `iceberg_tools/cli/schema.py` — `generate graph` command entry point.
- `iceberg_tools/graph/` — graph link writing logic (`SchemaLinkWriter`).
- `iceberg_tools/schema/graph.py` — schema bundling.
- `tests/fixtures/swapi/` — fixture set that demonstrates vertex/edge style graph data and link files.

### Operational guidance

- Use the graph track when downstream consumers want explicit relationship traversals.
- Keep `config.yaml` link constraints aligned with intended graph traversals to avoid unexpected edge fan-out.

---

## Track C — JSON Hypermedia Links

### Purpose

This track defines the hypermedia conventions used to express graph edges as JSON link objects, grounded in JSON Hyper-Schema link description objects.

### Canonical reference in this repo

- `docs/link-data-object.md` documents the project’s adapted link vocabulary.

### Implementation conventions

- `rel` names the edge semantics (and may include type suffixes for polymorphic references).
- `targetSchema` identifies target vertex/resource type.
- `href` defines target URI template.
- `templatePointers` maps source-instance values into `href` variables.
- `targetHints` carries traversal/cardinality conventions (`has_one`/`has_many`, directionality, backref).

### Why this matters

- It unifies schema-level link declarations with runtime graph transformations.
- It supports polymorphic FHIR references while keeping edge typing explicit.
- It allows relationship construction from source instance data via template pointer resolution.

### Practical rule of thumb

If you are designing or reviewing relationship behavior, start with `docs/link-data-object.md` first, then verify generated schema output from `iceberg schema generate graph` and `iceberg schema generate simplified` for consistency.

---

## Repository Capability Matrix

| Need | Preferred track | Primary command family |
|---|---|---|
| Gen3-compatible flattened dictionaries | Simplified (`gen3`) | `iceberg schema generate simplified` |
| PFB package creation from FHIR-derived data | Simplified (`pfb`) | `iceberg data simplify` + `iceberg data pfb` |
| Explicit typed graph schemas | Vertex/Edge Graph | `iceberg schema generate graph` |
| Link semantics / hypermedia modeling | JSON Hypermedia Links | `docs/link-data-object.md` + graph generation |

## Suggested Team Workflow (Agile)

1. **Architecture definition:** choose track(s) per product need.
2. **Schema sprint:** generate schema artifacts and review deltas.
3. **Data sprint:** run simplify/validate/export against fixture datasets.
4. **Graph sprint:** validate relationship semantics and traversals.
5. **Release gate:** package artifacts and publish generated schemas.

This split lets different squads iterate independently while sharing one source of truth for schema generation and relationship semantics.
