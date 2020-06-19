#!/usr/bin/env python3
from os import path

# path to result folder
conf = {
    "instance_folder": path.join(
        path.dirname(__file__), "..", "..", "instance"
    ),
    "example_query_id": "bacteria-7595694e-09aa-4fc3-8902-59e6d11c1a4a"
}

conf["db_path"] = path.join(conf["instance_folder"], "result", "data.db")
conf["jobs_db_path"] = path.join(conf["instance_folder"], "bigfam_jobs.db")
