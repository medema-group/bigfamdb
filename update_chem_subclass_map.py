from sys import argv, exit
from os import path

chem_class_map_tsv = argv[1]
result_data_db = argv[2]

# check if backup exists
if not path.exists(result_data_db + ".bak"):
    resp = input("data db backup doesn't exist ({})! do you want to continue? (y/n)".format(result_data_db + ".bak"))
    if resp != "y":
        exit(1)

import sqlite3
import pandas as pd
import numpy as np

parsed = pd.read_csv(chem_class_map_tsv, sep="\t", header=0)
parsed["class_subclass"] = parsed["bigslice_class"] + ":" + parsed["bigslice_subclass"]
parsed.index = parsed.apply(lambda row: (row["chem_code"], row["from"], row["bigslice_class"], row["bigslice_subclass"]), axis=1)

existing = pd.read_sql((
    "select class_source as chem_code, type_source as 'from', chem_class.name as bigslice_class, chem_subclass.name as bigslice_subclass"
    ", chem_subclass.id as subclass_id, chem_class.id as class_id"
    " from chem_subclass_map inner join chem_subclass on chem_subclass_map.subclass_id=chem_subclass.id"
    " inner join chem_class on chem_subclass.class_id=chem_class.id"),
    con=sqlite3.connect(result_data_db)
)
existing["class_subclass"] = existing["bigslice_class"] + ":" + existing["bigslice_subclass"]
existing.index = existing.apply(lambda row: (row["chem_code"], row["from"], row["bigslice_class"], row["bigslice_subclass"]), axis=1)

existing_subclasses = existing.groupby("class_subclass").apply(lambda rows: rows.iloc[0]["subclass_id"])
existing_classes = existing.groupby("bigslice_class").apply(lambda rows: rows.iloc[0]["class_id"])

parsed["subclass_id"] = existing_subclasses.reindex(parsed["class_subclass"]).fillna(-1).astype(int).values
parsed["class_id"] = existing_classes.reindex(parsed["bigslice_class"]).fillna(-1).astype(int).values

to_be_added = parsed[~parsed.index.isin(existing.index)]

# first, check classes to add
class_to_be_added = list(to_be_added[to_be_added["class_id"] == -1]["bigslice_class"].unique())
with sqlite3.connect(result_data_db) as con:
    cur = con.cursor()
    for class_name in class_to_be_added:
        cur.execute((
            "insert into chem_class (name) values (?)"
        ), (class_name,))
        to_be_added.loc[to_be_added[to_be_added["bigslice_class"] == class_name].index, "class_id"] = cur.lastrowid

# then, check subclasses to add
subclass_to_be_added = list(to_be_added[to_be_added["subclass_id"] == -1].apply(lambda row: (row["class_id"], row["bigslice_subclass"]), axis=1))
with sqlite3.connect(result_data_db) as con:
    cur = con.cursor()
    for class_id, subclass_name in subclass_to_be_added:
        cur.execute((
            "insert into chem_subclass (class_id, name) values (?,?)"
        ), (class_id, subclass_name))
        to_be_added.loc[to_be_added[
            np.logical_and(
                to_be_added["class_id"] == class_id,
                to_be_added["bigslice_subclass"] == subclass_name
            )
        ].index, "subclass_id"] = cur.lastrowid
        
# finally, add the chem_subclass_map entries
new_df = pd.DataFrame({
    "class_source": to_be_added["chem_code"].values,
    "type_source": to_be_added["from"].values,
    "subclass_id": to_be_added["subclass_id"].values
})
new_entries = new_df.to_sql("chem_subclass_map", sqlite3.connect(result_data_db), if_exists="append", index=False)

print("added {} new entries".format(new_entries))
