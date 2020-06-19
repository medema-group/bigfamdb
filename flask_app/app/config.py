#!/usr/bin/env python3
from os import path

# path to result folder
conf = {
    "instance_folder": path.join(
        path.dirname(__file__), "..", "..", "instance"
    )
}

conf["db_path"] = path.join(conf["instance_folder"], "data.db")
