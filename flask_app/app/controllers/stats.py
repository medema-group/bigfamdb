#!/usr/bin/env python3

import sqlite3
from flask import render_template, request

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('stats', __name__)


@blueprint.route("/stats")
def page_stats():

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()
        run_id, clustering_id, threshold = cur.execute((
            "select run.id, clustering.id, clustering.threshold"
            " from run,clustering"
            " where run.status >= 7"
            " and run.id=clustering.run_id"
            " order by run.id desc"
            " limit 1"
        )).fetchall()[0]

        bgc_total = cur.execute((
            "select count(bgc_id)"
            " from run_bgc_status"
            " where run_id=?"
        ), (run_id, )).fetchall()[0][0]

        gcf_total = cur.execute((
            "select count(id)"
            " from gcf"
            " where clustering_id=?"
        ), (clustering_id, )).fetchall()[0][0]

    # page title
    page_title = "Statistics"
    page_subtitle = ("")

    # render view
    return render_template(
        "stats/main.html.j2",
        page_title=page_title,
        page_subtitle=page_subtitle,
        bgc_total=bgc_total,
        gcf_total=gcf_total
    )

# APIs


@blueprint.route("/api/stats/get_dataset_table")
def get_dataset_table():
    """ for dataset datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # fetch total records (all bgcs in the dataset)
        result["recordsTotal"] = cur.execute((
            "select count(id)"
            " from dataset"
        )).fetchall()[0][0]

        # fetch total records (filtered)
        result["recordsFiltered"] = cur.execute((
            "select count(id)"
            " from dataset"
        )).fetchall()[0][0]

        # fetch data for table
        result["data"] = []
        for ds_id, ds_name, ds_desc in cur.execute((
            "select id, name, description"
            " from dataset"
        )).fetchall():

            # fetch total bgc
            total_bgc = cur.execute((
                "select count(id)"
                " from bgc"
                " where dataset_id=?"
            ), (ds_id, )).fetchall()[0][0]

            # fetch total genome
            total_genome = cur.execute((
                "select count(distinct orig_folder)"
                " from bgc"
                " where dataset_id=?"
                " and orig_folder not like ''"
            ), (ds_id, )).fetchall()[0][0]

            result["data"].append([
                ds_name,
                total_genome,
                total_bgc,
                ds_desc
            ])

        return result
