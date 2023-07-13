import redivis
import os
from dotenv import load_dotenv
load_dotenv()

tables = redivis.user(os.environ['REDIVIS_USER']).\
                    dataset(os.environ['REDIVIS_PROJECT']).\
                    list_tables(max_results=100)

tables = [(str(table.name).lower().replace(" ","_") + \
           ":" +str(table.properties.get("id")).split("-")[0]) for table in tables]

tables = [str(table).replace("%", ":" ) for table in tables]
table_names = [table.split(":")[0] for table in tables]

full_tables = ["concept:w5gj:","person:cdwn", "provider:m1br"]
partial_tables = ["observation:xhj4"]

for table,table_name in zip(tables,table_names):
    print(table,table_name)
    amount = "LIMIT 100000"
    if table in full_tables:
        amount = "LIMIT 1000000000000000000000000"
    if table in partial_tables: 
        amount = "LIMIT 1000000"

    query = redivis.query(f"""
        SELECT * FROM {os.environ['REDIVIS_USER']}.{os.environ['REDIVIS_PROJECT']}.{table}
        {amount}
    """)

    df = query.to_dataframe()
    df.to_json(f"../data/{str(table_name)}.json", 
               orient="records",lines=True)
    



"""
query = redivis.query(f
    SELECT * FROM {os.environ['REDIVIS_USER']}.{os.environ['REDIVIS_PROJECT']}.observation:xhj4
    LIMIT 1000000
"""


