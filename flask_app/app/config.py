#!/usr/bin/env python3
from os import path

# path to result folder
conf = {
    "instance_folder": path.join(
        path.dirname(__file__), "..", "..", "instance"
    ),
    "example_query_id": "bacteria-70dadcb9-3a1c-477a-96c3-6f2300de8565"
}

conf["db_path"] = path.join(conf["instance_folder"], "result", "data.db")
conf["jobs_db_path"] = path.join(conf["instance_folder"], "bigfam_jobs.db")
conf["reports_folder"] = path.join(conf["instance_folder"], "reports")
conf["reports_db_path"] = path.join(conf["reports_folder"], "reports.db")
