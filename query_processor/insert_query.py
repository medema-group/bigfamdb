#!/usr/bin/env python3

from os import path
from sys import exit, argv
from sqlite3 import connect as db_open
from datetime import datetime


def main():

    antismash_jobid = argv[1]

    instance_folder = path.join(
        path.dirname(__file__),
        "..",
        "instance"
    )
    jobs_db = path.join(instance_folder, "bigfam_jobs.db")

    if not path.exists(jobs_db):
        print("creating jobs db ({})...".format(jobs_db))
        with db_open(jobs_db) as con:
            cur = con.cursor()
            schema_sql = path.join(
                path.dirname(__file__),
                "jobs_schema.sql"
            )
            with open(schema_sql, "r") as sql_script:
                cur.executescript(sql_script.read())
                con.commit()

    with db_open(jobs_db) as con:
        cur = con.cursor()
        # check if exist
        if cur.execute((
            "select count(name)"
            " from jobs"
            " where name like ?"
        ), (antismash_jobid, )).fetchall()[0][0] > 0:
            print("Job ID exists!")
            return 0
        else:
            cur.execute((
                "insert into jobs"
                " (name,submitted,status)"
                " values(?,?,?)"
            ), (
                antismash_jobid,
                datetime.now(),
                0
            ))
            con.commit()
            print("Inserted new job!")
    return 0


if __name__ == '__main__':
    exit(main())
