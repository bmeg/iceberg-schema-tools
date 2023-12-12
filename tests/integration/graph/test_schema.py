import json

import fastjsonschema


def test_schema(fhir_schema):

    def _handler(uri):
        """Resolve $ref to $id"""
        for _def in fhir_schema['$defs'].values():
            if _def['$id'] == uri:
                print(f"Found {uri}")
                return _def
        print(f"Could not find {uri}")

    def _https_handler(uri):
        # ‘https://json-schema.org/draft/2020-12/links’  hosted by cloudflare
        # see  https://github.com/IATI/IATI-Standard-Website/issues/230
        import urllib.request
        req = urllib.request.Request(
            uri,
            data=None,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            }
        )
        f = urllib.request.urlopen(req)
        _ = f.read().decode('utf-8')
        return json.loads(_)

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
        handlers={'http': _handler, 'https': _https_handler},

    )
    assert compiled_schema
