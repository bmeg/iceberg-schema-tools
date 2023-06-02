import pandas as pd

"""
df = pd.read_json("../mimic-iv-omop-data/measurement.json", lines=True)
bad_nums = [3037278.0,2000001020.0,None,
            3035995.0,3000099.0,3021200.0,
            3013721.0, 3009306.0, 3003709.0, 
            3035924.0, 3004410.0
]
for i in range(len(df)):
    
    if df['measurement_source_concept_id'][i] in bad_nums:
        df['measurement_source_concept_id'][i] = 2000001020

df.to_json("../mimic-iv-omop-data/measurement.json", orient='records', lines=True)
"""




