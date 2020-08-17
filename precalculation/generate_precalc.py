#!/usr/bin/env python3

from os import path
from sys import exit, argv
from sqlite3 import connect as db_open
from datetime import datetime


def main():

    instance_folder = path.join(
        path.dirname(__file__),
        "..",
        "instance"
    )
    precalc_db = path.join(instance_folder, "precalculated.db")
    source_db = path.join(instance_folder, "result", "data.db")

    # make sure that source db only contains 1 clustering record and 1 hmmdb record
    with db_open(source_db) as con:
        cur = con.cursor()
        if cur.execute((
            "select count(id) from clustering"
        )).fetchall()[0][0] != 1:
            print("Expecting only 1 clustering record!")
            return 1
        if cur.execute((
            "select count(id) from hmm_db"
        )).fetchall()[0][0] != 1:
            print("Expecting only 1 hmmdb record!")
            return 1

    if not path.exists(precalc_db):
        print("creating precalculated db ({})...".format(precalc_db))
        with db_open(precalc_db) as con:
            cur = con.cursor()
            schema_sql = path.join(
                path.dirname(__file__),
                "cache_schema.sql"
            )
            with open(schema_sql, "r") as sql_script:
                cur.executescript(sql_script.read())
                con.commit()

        with db_open(precalc_db) as con:
            cur = con.cursor()

            # attach source_db
            cur.execute((
                "attach database ? as source"
            ), (source_db, ))

            # fetch clustering id
            clustering_id, threshold = cur.execute((
                "select id, threshold from clustering limit 1"
            )).fetchall()[0]

            # generate bgc summary
            cur.executemany((
                "insert into bgc_summary values(?,0)"
            ), cur.execute((
                "select id"
                " from source.bgc"
                " order by id asc"
            )).fetchall())
            print("calculating bgc cds counts...")
            cur.executemany((
                "update bgc_summary set cds_count=? where bgc_id=?"
            ), cur.execute((
                "select count(source.cds.id), source.cds.bgc_id"
                " from source.cds"
                " group by source.cds.bgc_id"
            )).fetchall())

            # generate gcf members summary
            cur.executemany((
                "insert into gcf_summary values(?,0,0)"
            ), cur.execute((
                "select id"
                " from source.gcf"
                " where clustering_id=?"
                " order by id asc"
            ), (clustering_id, )).fetchall())
            # inserting core member counts
            print("calculating gcf core member counts...")
            cur.executemany((
                "update gcf_summary set core_members=? where gcf_id=?"
            ), cur.execute((
                "select count(source.gcf_membership.bgc_id)"
                ", source.gcf_membership.gcf_id"
                " from source.gcf_membership,source.gcf"
                " where source.gcf.id=source.gcf_membership.gcf_id"
                " and source.gcf.clustering_id=?"
                " and source.gcf_membership.rank=0"
                " and source.gcf_membership.membership_value<=?"
                " group by source.gcf_membership.gcf_id"
            ), (clustering_id, threshold)).fetchall())
            # inserting putative member counts
            print("calculating gcf putative member counts...")
            cur.executemany((
                "update gcf_summary set putative_members=? where gcf_id=?"
            ), cur.execute((
                "select count(source.gcf_membership.bgc_id)"
                ", source.gcf_membership.gcf_id"
                " from source.gcf_membership,source.gcf"
                " where source.gcf.id=source.gcf_membership.gcf_id"
                " and source.gcf.clustering_id=?"
                " and source.gcf_membership.rank=0"
                " and source.gcf_membership.membership_value>?"
                " group by source.gcf_membership.gcf_id"
            ), (clustering_id, threshold)).fetchall())

            # generate gcf members summary dataset
            print("calculating gcf dataset counts...")
            cur.executemany((
                "insert into gcf_summary_dataset values(?,?,?)"
            ), cur.execute((
                "select source.gcf_membership.gcf_id"
                ", source.bgc.dataset_id"
                ", count(source.bgc.id)"
                " from source.gcf_membership,source.gcf,source.bgc"
                " where source.gcf.id=source.gcf_membership.gcf_id"
                " and source.gcf.clustering_id=?"
                " and source.gcf_membership.rank=0"
                " and source.gcf_membership.membership_value<=?"
                " and source.bgc.id=source.gcf_membership.bgc_id"
                " group by source.gcf_membership.gcf_id"
                ", source.bgc.dataset_id"
            ), (clustering_id, threshold)).fetchall())
            
            # generate gcf members summary class
            print("calculating gcf class counts...")
            cur.executemany((
                "insert into gcf_summary_class values(?,?,?)"
            ), cur.execute((
                "select source.gcf_membership.gcf_id"
                ", source.bgc_class.chem_subclass_id"
                ", count(source.bgc.id)"
                " from source.gcf_membership,source.gcf,source.bgc"
                ",source.bgc_class"
                " where source.gcf.id=source.gcf_membership.gcf_id"
                " and source.gcf.clustering_id=?"
                " and source.gcf_membership.rank=0"
                " and source.gcf_membership.membership_value<=?"
                " and source.bgc.id=source.gcf_membership.bgc_id"
                " and source.bgc.id=source.bgc_class.bgc_id"
                " group by source.gcf_membership.gcf_id"
                ", source.bgc_class.chem_subclass_id"
            ), (clustering_id, threshold)).fetchall())

            # generate gcf members summary taxon
            print("calculating gcf taxon counts...")
            cur.executemany((
                "insert into gcf_summary_taxon values(?,?,?)"
            ), cur.execute((
                "select source.gcf_membership.gcf_id"
                ", source.bgc_taxonomy.taxon_id"
                ", count(source.bgc.id)"
                " from source.gcf_membership,source.gcf,source.bgc"
                ",source.bgc_taxonomy"
                " where source.gcf.id=source.gcf_membership.gcf_id"
                " and source.gcf.clustering_id=?"
                " and source.gcf_membership.rank=0"
                " and source.gcf_membership.membership_value<=?"
                " and source.bgc.id=source.gcf_membership.bgc_id"
                " and source.bgc.id=source.bgc_taxonomy.bgc_id"
                " group by source.gcf_membership.gcf_id"
                ", source.bgc_taxonomy.taxon_id"
            ), (clustering_id, threshold)).fetchall())
            
            # make bgc_domains table
            print("inserting bgc_domains entries...")
            cur.executemany((
                "insert into bgc_domains values(?,?)"
            ), cur.execute((
                "select bgc_id, hmm_id"
                " from source.bgc_features"
                " where value >= 255"
            )).fetchall())
                
            # make gcf_domains table
            print("inserting gcf_domains entries...")
            cur.executemany((
                "insert into gcf_domains values(?,?)"
            ), cur.execute((
                "select gcf_id, hmm_id"
                " from source.gcf_models,source.gcf"
                " where source.gcf.clustering_id=?"
                " and source.gcf_models.gcf_id=source.gcf.id"
                " and value >= 200"
            ), (clustering_id, )).fetchall())
            
        return 0
    else:
        print("precalculated db exists!")
        return 1


if __name__ == '__main__':
    exit(main())
