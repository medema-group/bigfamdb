#!/usr/bin/env python3

import sqlite3
from flask import render_template, request
import json
from os import path

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('dataset', __name__)


@blueprint.route("/dataset/<int:dataset_id>")
def page_dataset(dataset_id):

    # page title
    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()
        if dataset_id > 0:
            page_title, page_subtitle = cur.execute((
                "select name, description"
                " from dataset"
                " where id = ?"
            ), (dataset_id, )).fetchall()[0]
            page_title = "Dataset: " + page_title
        else:
            page_title = "Biosynthetic Gene Clusters (BGCs)"
            page_subtitle = ""

    # render view
    return render_template(
        "dataset/main.html.j2",
        dataset_id=dataset_id,
        page_title=page_title,
        page_subtitle=page_subtitle
    )

# APIs


@blueprint.route("/api/dataset/get_bgc_table")
def get_bgc_table():
    """ for bgc datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    # translate request parameters
    dataset_id = request.args.get('dataset_id', default=0, type=int)
    result["dataset_id"] = dataset_id
    offset = request.args.get('start', type=int)
    limit = request.args.get('length', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # fetch total records (all bgcs in the dataset)
        result["recordsTotal"] = cur.execute((
            "select count(id)"
            " from bgc"
            " where dataset_id{}?"
        ).format("=" if dataset_id > 0 else "!="),
            (dataset_id,)).fetchall()[0][0]

        # fetch total records (filtered)
        result["recordsFiltered"] = cur.execute((
            "select count(id)"
            " from bgc"
            " where dataset_id{}?"
        ).format("=" if dataset_id > 0 else "!="),
            (dataset_id,)).fetchall()[0][0]

        # fetch taxonomy descriptor
        result["taxon_desc"] = cur.execute((
            "select level, name"
            " from taxon_class"
            " order by level asc"
        )).fetchall()

        # fetch data for table
        result["data"] = []
        for row in cur.execute((
            "select bgc.id as bgc_id"
            ",dataset_id, dataset.name"
            ",bgc.orig_folder as genome"
            ",orig_filename as bgc_name"
            ",length_nt,on_contig_edge"
            " from bgc,dataset"
            " where dataset_id{}?"
            " and bgc.dataset_id=dataset.id"
            " limit ? offset ?"
        ).format("=" if dataset_id > 0 else "!="),
                (dataset_id, limit, offset)).fetchall():
            (bgc_id, dataset_id, dataset_name,
             genome, name, length, fragmented) = row

            # fetch basic data
            data = {
                "bgc_id": bgc_id,
                "dataset": dataset_name,
                "genome_name": genome if genome else "n/a",
                "bgc_name": name,
                "bgc_length": "{:.02f}".format(length / 1000)
            }
            if fragmented == 1:
                data["completeness"] = "fragmented"
            elif fragmented == 0:
                data["completeness"] = "complete"
            else:
                data["completeness"] = "n/a"

            # fetch genes count
            data["genes_count"] = cur.execute((
                "select count(id)"
                " from cds"
                " where bgc_id=?"
            ), (bgc_id, )).fetchall()[0][0]

            # fetch taxonomy information
            data["taxonomy"] = {
                row[0]: row[1] for row in cur.execute((
                    "select taxon.level, taxon.name"
                    " from taxon, bgc_taxonomy"
                    " where taxon.id=bgc_taxonomy.taxon_id"
                    " and bgc_taxonomy.bgc_id=?"
                ), (bgc_id, )).fetchall()
            }

            # fetch class information
            data["class_name"] = cur.execute((
                "select chem_class.name, chem_subclass.name"
                " from bgc, bgc_class, chem_subclass, chem_class"
                " where bgc.id=bgc_class.bgc_id"
                " and bgc_class.chem_subclass_id=chem_subclass.id"
                " and chem_subclass.class_id=chem_class.id"
                " and bgc.id=?"
            ), (bgc_id, )).fetchall()

            result["data"].append([
                data["dataset"],
                data["genome_name"],
                data["bgc_name"],
                data["taxonomy"],
                data["class_name"],
                data["bgc_length"],
                data["genes_count"],
                data["completeness"],
                data["bgc_id"]
            ])

    return result
