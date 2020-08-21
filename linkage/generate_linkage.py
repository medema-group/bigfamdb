from os import path, getpid
from sys import exit, argv, stderr
from multiprocessing import Pool, cpu_count
import subprocess
from sqlite3 import connect as db_open
import re


def fetch_pool(num_threads: int):
    pool = Pool(processes=num_threads)

    try:
        # set cores for the multiprocessing pools
        all_cpu_ids = set()
        for i, p in enumerate(pool._pool):
            cpu_id = str(cpu_count() - (i % cpu_count()) - 1)
            subprocess.run(["taskset",
                            "-p", "-c",
                            cpu_id,
                            str(p.pid)], check=True)
            all_cpu_ids.add(cpu_id)

        # set core for the main python script
        subprocess.run(["taskset",
                        "-p", "-c",
                        ",".join(all_cpu_ids),
                        str(getpid())], check=True)

    except FileNotFoundError:
        pass  # running in OSX?

    return pool


def parse_bgc_gbk(args):
    gbk_path, data = args
    bgc_id, ds_name, orig_folder, orig_filename = data
    insert_params = None
    # this is a bit too hardcoded, but it's okay
    # in this context
    if ds_name.startswith("mibig"):
        insert_params = ("mibig", (bgc_id, path.splitext(orig_filename)[0]))
    elif ds_name.startswith("isolate_"):
        nuccore_acc = orig_filename.split(".region")[0]
        if not path.exists(gbk_path):
            print(gbk_path + " not exists!")
            return None
        with open(gbk_path, "r") as gbk_file: # antismash5.1 type gbk
            for line in gbk_file:
                line = line.lstrip()
                if line.startswith("FEATURES"):
                    break
                if line.startswith("Orig. start"):
                    start_loc = int(re.sub('[^0-9]','', line.split("::")[-1]))
                if line.startswith("Orig. end"):
                    end_loc = int(re.sub('[^0-9]','', line.split("::")[-1]))
                    break
        insert_params = (
            "ncbi",
            (bgc_id, nuccore_acc, start_loc, end_loc)
        )                    
    elif False: # todo: check antismashdb
        pass
    return insert_params


def main():

    instance_folder = path.join(
        path.dirname(__file__),
        "..",
        "instance"
    )
    linkage_db = path.join(instance_folder, "linkage.db")
    source_db = path.join(instance_folder, "result", "data.db")
    input_folder = argv[1]
    if len(argv) > 2:
        num_jobs = int(argv[2])
    else:
        num_jobs = 1
    pool = fetch_pool(num_jobs)
    
    # check if linkage.db exists
    if path.exists(linkage_db):
        print("{} exists!".format(linkage_db))
        return 1

    # parse original datasets information
    print("parsing datasets.tsv...")
    datasets = {}
    with open(path.join(input_folder, "datasets.tsv"), "r") as dstv:
        for line in dstv:
            if not line.startswith("#"):
                ds_name, ds_folder, _, _ = line.rstrip("\n").split("\t")
                datasets[ds_name] = {
                    "path": path.join(input_folder, ds_folder)
                }

    # scan BGCs in database and populate args for multiprocessing
    print("populating list of BGCs to parse...")
    with db_open(source_db) as con:
        cur = con.cursor()

        to_process = [(
            path.join(
                input_folder,
                datasets[row[1]]["path"],
                row[2],
                row[3]
            ), row) for row in cur.execute((
            "select bgc.id, dataset.name"
            ", bgc.orig_folder, bgc.orig_filename"
            " from bgc, dataset"
            " where bgc.dataset_id=dataset.id"
            " order by bgc.id asc"
        )).fetchall()]
    print("found {:,} BGCs!".format(len(to_process)))

    # parse original input files
    print("parsing {:,} BGCs using {} threads...".format(
        len(to_process),
        num_jobs
    ))
    to_insert_mibig = []
    to_insert_ncbi = []
    to_insert_antismashdb = []
    i = 0
    for data in pool.imap_unordered(parse_bgc_gbk, to_process):
        i += 1
        stderr.write("\r{}/{}".format(i, len(to_process)))
        if data is None:
            continue
        elif data[0] == "mibig":
            to_insert_mibig.append(data[1])
        elif data[0] == "ncbi":
            to_insert_ncbi.append(data[1])
        elif data[0] == "antismashdb":
            to_insert_antismashdb.append(data[1])
    
    # create linkage db
    print("creating linkage db...")
    with db_open(linkage_db) as con:
        cur = con.cursor()
        schema_sql = path.join(
            path.dirname(__file__),
            "linkage_schema.sql"
        )
        with open(schema_sql, "r") as sql_script:
            cur.executescript(sql_script.read())
            con.commit()

        if len(to_insert_mibig) > 0:
            # insert mibig data
            print("inserting mibig linkages...")
            cur.executemany((
                "insert into linkage_mibig(bgc_id, mibig_acc)"
                " values (?, ?)"
            ), to_insert_mibig)
        else:
            print("found no mibig linkage")

        if len(to_insert_ncbi) > 0:
            # insert ncbi data
            print("inserting ncbi linkages...")
            cur.executemany((
                "insert into linkage_ncbi("
                "bgc_id, nuccore_acc,"
                " start_loc, end_loc)"
                " values (?, ?, ?, ?)"
            ), to_insert_ncbi)
        else:
            print("found no ncbi linkage")
            
        if len(to_insert_antismashdb) > 0:
            # insert antismashdb data
            print("inserting antismashdb linkages...")
            cur.executemany((
                "insert into linkage_antismashdb("
                "bgc_id, nuccore_acc,"
                " start_loc, end_loc)"
                " values (?, ?, ?, ?)"
            ), to_insert_antismashdb)
        else:
            print("found no antismashdb linkage")                


if __name__ == '__main__':
    exit(main())
