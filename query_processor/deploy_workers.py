#!/usr/bin/env python3

from os import path, listdir
from subprocess import run, DEVNULL
from shutil import copytree
from tempfile import TemporaryDirectory
from sys import exit, argv
from sqlite3 import connect as db_open
from time import sleep
from datetime import datetime
from multiprocessing import cpu_count


def fetch_pending_jobs(jobs_db):
    with db_open(jobs_db) as con:
        cur = con.cursor()
        return [row[0] for row in cur.execute((
            "select name"
            " from jobs"
            " where status=0"
            " order by submitted asc"
        )).fetchall()]


def deploy_jobs(pending, jobs_db, instance_folder, num_threads):
    inputs_folder = path.join(instance_folder, "query_inputs")
    for name in pending:
        # update status to "DOWNLOADING"
        with db_open(jobs_db) as con:
            cur = con.cursor()
            cur.execute((
                "update jobs"
                " set status=?, started=?"
                " where name like ?"
            ), (1, datetime.now(), name))
            con.commit()

        # download antiSMASH result
        query_input = path.join(
            inputs_folder,
            name
        )
        print("downloading {}...".format(query_input))
        with TemporaryDirectory() as temp_dir:
            if name.startswith("bacteria-"):
                as_type = "antismash"
            elif name.startswith("fungi-"):
                as_type = "fungismash"
            else:
                # update status to "FAILED"
                with db_open(jobs_db) as con:
                    cur = con.cursor()
                    cur.execute((
                        "update jobs"
                        " set status=?, finished=?,"
                        " comment=?"
                        " where name like ?"
                    ), (-1, datetime.now(), "unknown_as_type", name))
                    con.commit()
                print("unknown job id!")
                return 1
            antismash_url = (
                "https://{}.secondarymetabolites.org/upload/{}/"
            ).format(as_type, name)
            commands = [
                "wget",
                "-nd",
                "-r",
                "-A",
                "*.region*.gbk",
                antismash_url
            ]
            is_failed = True
            if run(commands, cwd=temp_dir).returncode == 0:  # success
                # check if file exists at all
                file_exists = False
                for fname in listdir(temp_dir):
                    print(fname)
                    if fname.endswith(".gbk"):
                        file_exists = True
                        break
                if file_exists and not path.exists(query_input):
                    copytree(temp_dir, query_input)
                    is_failed = False

            if is_failed:  # failed
                # update status to "FAILED"
                with db_open(jobs_db) as con:
                    cur = con.cursor()
                    cur.execute((
                        "update jobs"
                        " set status=?, finished=?,"
                        " comment=?"
                        " where name like ?"
                    ), (-1, datetime.now(), "download_failed", name))
                    con.commit()
                print("download failed!")
                return 1
            else:
                # update status to "PROCESSING"
                with db_open(jobs_db) as con:
                    cur = con.cursor()
                    cur.execute((
                        "update jobs"
                        " set status=?"
                        " where name like ?"
                    ), (2, name))
                    con.commit()
                is_failed = False

        # run BiG-SLICE query
        commands = [
            "bigslice",
            "-t",
            str(num_threads),
            "--query",
            query_input,
            "--query_name",
            name,
            instance_folder
        ]
        print("processing {}...".format(query_input))
        # if run(commands, stdout=DEVNULL) == 0:  # success
        if run(commands).returncode == 0:  # success
            # update status to "PROCESSED"
            with db_open(jobs_db) as con:
                cur = con.cursor()
                cur.execute((
                    "update jobs"
                    " set status=?, finished=?"
                    " where name like ?"
                ), (3, datetime.now(), name))
                con.commit()
        else:  # failed
            # update status to "FAILED"
            with db_open(jobs_db) as con:
                cur = con.cursor()
                cur.execute((
                    "update jobs"
                    " set status=?, finished=?,"
                    " comment=?"
                    " where name like ?"
                ), (-1, datetime.now(), "query_failed", name))
                con.commit()
            print("run failed!")
            return 1
    return 0


def main():

    if len(argv) > 1:
        num_threads = int(argv[1])
    else:
        num_threads = cpu_count()

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

    print("workers are running...")
    while(True):
        pending = fetch_pending_jobs(jobs_db)
        if len(pending) > 0:
            print("deploying {} jobs...".format(
                len(pending)
            ))
            deploy_jobs(pending, jobs_db, instance_folder, num_threads)

        sleep(5)

    return 0


if __name__ == '__main__':
    exit(main())
