const fs = require('fs');

//const schema = JSON.parse(fs.readFileSync('iceberg/schemas/graph3/graph-fhir.json', 'utf8'));
const path = process.argv[2];
if (!path) {
  console.error('usage: node extract_data.js path/to/graph.json > data.json');
  process.exit(1);
}

const schema = JSON.parse(fs.readFileSync(path, 'utf8'));

const allNodes = new Set();
const allEdges = [];
const minimalNodes = new Set();
const minimalEdges = [];

const mainFHIRResources = [
  'Patient', 'Practitioner', 'PractitionerRole', 'Organization', 'Group',
  'Observation', 'Condition', 'Specimen', 'Device', 'Medication', 'MedicationAdministration', 
  'MedicationStatement', 'MedicationRequest', 'ServiceRequest', 'Task', 'DocumentReference',
  'ImagingStudy', 'ResearchStudy', 'ResearchSubject', 'Citation', 'BodyStructure',
  'Substance', 'SubstanceDefinition'
].filter(resource => schema.$defs[resource]);

console.error('main FHIR Resources found:', mainFHIRResources);
console.error('total entities in schema:', Object.keys(schema.$defs).length);

Object.entries(schema.$defs).forEach(([entityName, entityDef]) => {
  allNodes.add(entityName);

  if (mainFHIRResources.includes(entityName)) {
    minimalNodes.add(entityName);
  }
  
  if (entityDef.links) {
    entityDef.links.forEach(link => {
      const target = link.targetSchema?.$ref?.split('/').pop();
      
      if (target && schema.$defs[target]) {
        // skip nested relationships
        const isNestedRelationship = link.rel.includes('_authorReference_') ||
          link.rel.includes('_note_') ||
          link.rel.includes('attachment_') ||
          link.rel.startsWith('note_') ||
          link.rel.includes('_identifier_') ||
          link.rel.includes('_extension_');
        
        if (!isNestedRelationship) {
          allEdges.push({
            source: entityName,
            target: target,
            relationship: link.rel
          });
          
          if (mainFHIRResources.includes(entityName) && mainFHIRResources.includes(target)) {
            minimalEdges.push({
              source: entityName,
              target: target,
              relationship: link.rel
            });
          }
        }
      }
    });
  }
});
// group is reserved for potential use in styling or grouping nodes
const graphData = {
  full: {
    nodes: Array.from(allNodes).map(id => ({id, group: 1})),
    links: allEdges
  },
  minimal: {
    nodes: Array.from(minimalNodes).map(id => ({id, group: 1})),
    links: minimalEdges
  }
};

console.log(JSON.stringify(graphData, null, 2));