#!/usr/bin/env python3
from os import path

# path to result folder
conf = {
    "instance_folder": path.join(
        path.dirname(__file__), "..", "..", "instance"
    ),
    "example_query_id": "bacteria-3db13cf8-3367-4428-b305-6a3ce6d8bb0e"
}

conf["db_path"] = path.join(conf["instance_folder"], "result", "data.db")
conf["precalc_db_path"] = path.join(conf["instance_folder"], "precalculated.db")
conf["linkage_db_path"] = path.join(conf["instance_folder"], "linkage.db")
conf["jobs_db_path"] = path.join(conf["instance_folder"], "bigfam_jobs.db")
conf["reports_folder"] = path.join(conf["instance_folder"], "reports")
conf["reports_db_path"] = path.join(conf["reports_folder"], "reports.db")
