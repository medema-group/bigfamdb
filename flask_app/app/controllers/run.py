#!/usr/bin/env python3

import sqlite3
from flask import render_template, request
import math

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('run', __name__)


@blueprint.route("/run/<int:run_id>")
def page_run(run_id):

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        status_id, = cur.execute((
            "select status"
            " from run"
            " where id = ?"
        ), (run_id, )).fetchall()[0]

        page_title = "Gene Cluster Families (GCFs)"
        page_subtitle = ("")

    # render view
    return render_template(
        "run/main.html.j2",
        run_id=run_id,
        status_id=status_id,
        page_title=page_title,
        page_subtitle=page_subtitle
    )


@blueprint.route("/api/run/get_gcf_table")
def get_gcf_table():
    """ for gcf datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    # translate request parameters
    run_id = request.args.get('run_id', default=0, type=int)
    result["run_id"] = run_id
    offset = request.args.get('start', type=int)
    limit = request.args.get('length', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # set clustering id and threshold
        clustering_id, threshold = cur.execute(
            ("select id, threshold"
             " from clustering"
             " where run_id=?"),
            (run_id, )
        ).fetchall()[0]

        # fetch total records (all gcfs in the dataset)
        result["recordsTotal"] = cur.execute(
            ("select count(id)"
             " from gcf"
             " where clustering_id=?"),
            (clustering_id,)).fetchall()[0][0]

        # fetch total records (filtered)
        result["recordsFiltered"] = cur.execute(
            ("select count(id)"
             " from gcf"
             " where clustering_id=?"),
            (clustering_id,)).fetchall()[0][0]

        # get max gcf id

        # fetch data for table
        result["data"] = []
        for row in cur.execute(
            ("select id, id_in_run"
             " from gcf"
             " where clustering_id=?"
             " limit ? offset ?"),
                (clustering_id, limit, offset)).fetchall():
            gcf_id, gcf_accession = row

            # todo: fetch directly from gcf.name (need schema update)
            gcf_name = "GCF_{:0{width}d}".format(
                gcf_accession, width=math.ceil(
                    math.log10(result["recordsTotal"])))

            # fetch core members count
            core_members = cur.execute(
                (
                    "select count(bgc_id)"
                    " from gcf_membership"
                    " where gcf_id=?"
                    " and rank=0"
                    " and membership_value <= ?"
                ),
                (gcf_id, threshold)).fetchall()[0][0]

            # fetch putative members count
            putative_members = cur.execute(
                (
                    "select count(bgc_id)"
                    " from gcf_membership"
                    " where gcf_id=?"
                    " and rank=0"
                    " and membership_value > ?"
                ),
                (gcf_id, threshold)).fetchall()[0][0]

            # fetch classes counts
            class_counts = cur.execute(
                (
                    "select chem_class.name || ':' || chem_subclass.name"
                    " as chem_class,"
                    " count(gcf_membership.bgc_id) as bgc"
                    " from chem_class, chem_subclass,"
                    " bgc_class, gcf_membership"
                    " where gcf_membership.gcf_id=?"
                    " and gcf_membership.bgc_id=bgc_class.bgc_id"
                    " and bgc_class.chem_subclass_id=chem_subclass.id"
                    " and chem_subclass.class_id=chem_class.id"
                    " and rank=0"
                    " and membership_value <= ?"
                    " group by chem_class"
                    " order by bgc desc"
                ),
                (gcf_id, threshold)).fetchall()

            # fetch taxon counts
            taxon_counts = cur.execute(
                (
                    "select taxon.name as taxon,"
                    " count(gcf_membership.bgc_id) as bgc"
                    " from taxon, bgc_taxonomy, gcf_membership"
                    " where gcf_membership.gcf_id=?"
                    " and gcf_membership.bgc_id=bgc_taxonomy.bgc_id"
                    " and bgc_taxonomy.taxon_id=taxon.id"
                    " and taxon.level=5"  # genus
                    " and membership_value <= ?"
                    " group by taxon"
                    " order by bgc desc"
                ),
                (gcf_id, threshold)).fetchall()

            result["data"].append([
                gcf_name,  # gcf
                core_members,  # core members
                putative_members,  # putative members
                class_counts,  # representative class
                taxon_counts,  # representative taxon
                gcf_id  # gcf_id
            ])

    return result
