import fastjsonschema


def test_schema(fhir_schema):

    def _handler(uri):
        """Resolve $ref to $id"""
        for _def in fhir_schema['$defs'].values():
            if _def['$id'] == uri:
                return _def

    compiled_schema = fastjsonschema.compile(
        fhir_schema,
        formats={
            'time': r'^(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$',
            'date': r'^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])?$',
            'binary': r'^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$',
            "date-time": r'^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$',
            "uri": r'\w+:(\/?\/?)[^\s]+',
            "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        handlers={'http': _handler},

    )
    assert compiled_schema
