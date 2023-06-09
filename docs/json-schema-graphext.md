
# JSON Schema Graph Extensions

The Graph Extension for JSON Schema is designed to provide a mapping of structured JSON data to a property graph. 
The property graph is assumed to have the following properties:
 - Nodes have a unique string based identifier that must be defined
 - Nodes have a type label. By default it is the title of the JSON schema object definition
 - Nodes may have an attach nested JSON document
 - Edges may have defined unique string based identifiers, but if one is not defined it may be randomly generated at a later date
 - Edges may have an attached nested JSON document
 - Edges have a type label. By default it is the name of the property field that defines the edge.
 - Edges have directionality, i.e. a to and from field. These must be defined during validation
 - Edges may have multiplicity constraints, ie one-to-many or many-to-one. However, in many cases this cannot be validated during record based validation, but can only be done during data integration. 


# Object Link Declaration
An object link is an edge that emerges from a parent vertex, and does not exist by itself. In most cases it is represented by a field 
with a string reference to an ID of another object. 

String form:
```json
{
    "parentObject" : "parentID_1"
}
```

Dictionary form
```json
{
    "parentObject" : {"id" : "parentID_1"}
}
```


## Declaring an object link

Object Link Extension Schema:
```yaml
	properties:
		targets:
			type: array
			items:
			    type: object
				properties:
					type:
                        type: object
						properties:
							$ref:
								type: string
					backref:
						type: string
```

The array of `targets` list the possible target types of the link field. The `$ref` field points to the object declaration in JSON
schema. The `backref` describes how back pointing edges will be generated. 


### Example Object Link
```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"

id: "sample"

properties:
  case:
    targets: 
      - type: 
          $ref: case.yaml
        backref: samples
    type: object
        additionalProperties: True
        properties:
            id:
                type: string
            submitter_id:
                type: string
```


