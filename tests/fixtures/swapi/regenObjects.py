import json
import pandas as pd
import polars as pl
import yaml

vdf = pd.read_json('swapi.vertices', lines=True)
edf = pd.read_json('swapi.edges', lines=True)

vjsons = vdf.to_dict('records')
ejsons = edf.to_dict('records')

vertices = {}
schemas = {}


def typeStr(x):
    if type(x) is int:
        return 'integer'
    elif type(x) is float:
        return 'number'
    elif type(x) is str:
        return 'string'
    elif x is None:
        return '\'null\''
    elif type(x) is list:
        return 'array'
    else:
        return 'object'


pedf = pedf = pl.from_pandas(edf)
fromMaxMult = pedf.with_columns(pl.col('from').str.replace(r"\:\d+", "").alias("sourceType")).groupby(
    by=["label", "from", "sourceType"]).count().groupby(by=["label", "sourceType"]).max().with_columns(
    pl.col('count').eq(1).alias('fromMultiple'))
toMaxMult = pedf.with_columns(pl.col('from').str.replace(r"\:\d+", "").alias("sourceType")).groupby(
    by=["label", "to", "sourceType"]).count().groupby(by=["label", "sourceType"]).max().with_columns(
    pl.col('count').eq(1).alias('toMultiple'))
multTable = fromMaxMult.join(toMaxMult, on=['label', 'sourceType'])

for j in vjsons:
    j['id'] = j['gid'].split(':')[1]
    if 'system' in j['data'] and type(j['data']['system']) is dict:
        j['created_datetime'] = j['data']['system']['created']
        j['edited_datetime'] = j['data']['system']['edited']
        j['data'].pop('system', None)
    for k in j['data']:
        j[k] = j['data'][k]
    if j['label'] not in vertices:
        vertices[j['label']] = {}
        schemas[j['label']] = {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': j['label'].lower(),
            'title': j['label'],
            'type': 'object',
            'required': ['gid', 'id', 'label'],
            'uniqueKeys': [['gid'], ['label', 'id']],
            'links': [],
            'properties': {
                'links': {
                    'type': 'array',
                    'items': {'$ref': 'https://json-schema.org/draft/2020-12/links'}
                }
            }
        }
    j.pop('data', None)
    vertices[j['label']][j['id']] = j

for j in ejsons:
    if type(j['data']) is not dict:
        floc = j['from'].split(':')
        tloc = j['to'].split(':')
        #  adding links "to"
        if j['label'] not in vertices[floc[0]][floc[1]]:
            vertices[floc[0]][floc[1]][j['label']] = [{'id': tloc[1]}]
        else:
            vertices[floc[0]][floc[1]][j['label']].append({'id': tloc[1]})

    else:  # if it contains information that can't really go in either object:
        if j['label'] not in vertices:
            vertices[j['label']] = {}
            schemas[j['label']] = {
                "'$schema'": 'https://json-schema.org/draft/2020-12/schema',
                "'$id'": j['label'].lower(),
                'title': j['label'],
                'type': 'object',
                'links': [],
                'properties': {
                    'links': {
                        'type': 'array',
                        'items': {'$ref': 'https://json-schema.org/draft/2020-12/links'}
                    }
                }
            }
        for k in j['data']:
            j[k] = j['data'][k]
        j.pop('data', None)
        for target in ['from', 'to']:
            loc = j[target].split(':')
            j[loc[0].lower()] = loc[1]
            if loc[0].lower() not in [x['rel'] for x in schemas[j['label']]['links']]:
                schemas[j['label']]['links'].append({
                    'rel': loc[0].lower(),
                    'href': loc[0].lower() + '/{id}',
                    'templateRequired': ['id'],
                    'targetSchema': {'$ref': loc[0].lower() + '.yaml'},
                    'templatePointers': 'id',
                    'targetHints': {
                        'directionality': 'outbound',
                        'multiplicity': 'has_one',
                        'association': True
                    }
                })
        j.pop('from', None)
        j.pop('to', None)
        vertices[j['label']][j['gid']] = j
#  at this point all of the edges are inside the vertices and the edge objects are treated as vertices for now

for j in vjsons:
    for k in j:
        if k not in schemas[j['label']]['properties']:
            schemas[j['label']]['properties'][k] = {'type': [typeStr(j[k])]}
        elif typeStr(j[k]) not in schemas[j['label']]['properties'][k]['type']:
            schemas[j['label']]['properties'][k]['type'].append(typeStr(j[k]))

for r in multTable.iter_rows(named=True):
    targetType = r['to'].split(':')[0]
    schemas[r['sourceType']]['links'].append({
        'rel': r['label'].lower(),
        'href': targetType.lower() + '/{id}',
        'templateRequired': ['id'],
        'targetSchema': {'$ref': targetType.lower() + '.yaml'},
        'templatePointers': '/id',
        'targetHints': {
            'directionality': 'outbound',
            'multiplicity': 'has_many' if r["toMultiple"] else 'has_many',
            'backref': r['sourceType'].lower() + ('s' if r['fromMultiple'] and r['sourceType'][-1] != 's' else "")
        }
    })
for vset in vertices:
    with open('swapi_' + vset.lower() + '.json', 'w') as outFile:
        with open(vset.lower() + '.yaml', 'w') as outYaml:
            for k in vertices[vset]:
                outFile.write(json.dumps(vertices[vset][k]) + '\n')
            outYaml.write(yaml.dump(schemas[vset], sort_keys=False).replace("'''", '"'))
