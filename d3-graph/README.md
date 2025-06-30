## Schema Graph Viewer

An interactive D3.js app for visualizing schema relationships from JSON data.

### 1. Install dependencies
```bash
  npm install
```
### 2. Run the app locally
```bash
  npm start
```

This will launch the development server at http://localhost:3000

### Folder Structure
- **src/**: Contains the React/D3 graph viewer code

- **public/graph.json**: Input data file used to render the graph. This JSON file is generated using the `extract_schemas` utility logic.
```bash 
    python extract_schema.py \
    --input-dir bmeg-etl/schema \
    --base-uri http://graph-fhir.io/schema/0.0.2 \
    --output bmeg-graph.json
```