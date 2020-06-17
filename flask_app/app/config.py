#!/usr/bin/env python3
from os import path

# path to result folder
conf = {
    "result_folder": path.join(path.dirname(__file__), "..", "result")
}

conf["db_path"] = path.join(conf["result_folder"], "data.db")