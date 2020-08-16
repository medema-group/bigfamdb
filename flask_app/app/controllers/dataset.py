#!/usr/bin/env python3

import sqlite3
from flask import render_template, request, redirect
from flask import url_for

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('dataset', __name__)


@blueprint.route("/dataset/<int:dataset_id>")
def page_dataset(dataset_id):

    # in BiG-FAM, always shows all datasets
    if dataset_id != 0:
        return redirect(url_for("dataset.page_dataset", dataset_id=0))

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

    # for filtering
    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # datasets
        datasets_list = cur.execute((
            "select id, name"
            " from dataset"
            " order by name"
        )).fetchall()

        # bgc classes
        classes_list = cur.execute((
            "select id, name"
            " from chem_class"
            " order by name"
        )).fetchall()

    # render view
    return render_template(
        "dataset/main.html.j2",
        dataset_id=dataset_id,
        page_title=page_title,
        page_subtitle=page_subtitle,
        datasets_list=datasets_list,
        classes_list=classes_list
    )

# APIs


@blueprint.route("/api/dataset/get_bgc_table")
def get_bgc_table():
    """ for bgc datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    # translate request parameters
    dataset_ids = list(map(int, request.args.getlist('dataset_id[]')))
    chem_class_ids = list(map(int, request.args.getlist('chem_class_id[]')))
    taxon_ids = [int(i) for i in request.args.get(
        'taxons', type=str).split(",") if len(i) > 0]
    length_nt_from = request.args.get(
        "length_nt_from", default=None, type=int)
    length_nt_to = request.args.get(
        "length_nt_to", default=None, type=int)
    complete_only = request.args.get(
        "complete_only", default=False, type=bool)
    offset = request.args.get('start', type=int)
    limit = request.args.get('length', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # get selector for bgcs (based only on bgc table)
        selector_froms = ""
        selector_wheres = "1"
        if isinstance(length_nt_from, int):
            selector_wheres += " and bgc.length_nt>={}".format(
                length_nt_from)
        if isinstance(length_nt_to, int):
            selector_wheres += " and bgc.length_nt<={}".format(
                length_nt_to)
        if complete_only:
            selector_wheres += " and bgc.on_contig_edge=0"
        if len(dataset_ids) > 0:
            selector_wheres += " and bgc.dataset_id in ({})".format(
                ",".join(map(str, dataset_ids)))
        if len(chem_class_ids) > 0:
            selector_froms += ",bgc_class,chem_class,chem_subclass"
            selector_wheres += (
                " and bgc_class.bgc_id=bgc.id"
                " and bgc_class.chem_subclass_id=chem_subclass.id"
                " and chem_class.id=chem_subclass.class_id"
            )
            selector_wheres += " and chem_class.id in ({})".format(
                ",".join(map(str, chem_class_ids)))
        if len(taxon_ids) > 0:
            selector_froms += ",bgc_taxonomy"
            selector_wheres += " and bgc_taxonomy.bgc_id=bgc.id"
            selector_wheres += " and bgc_taxonomy.taxon_id in ({})".format(
                ",".join(map(str, taxon_ids)))

        # fetch total records (all bgcs in the dataset)
        result["recordsTotal"] = cur.execute((
            "select count(id) from bgc"
        )).fetchall()[0][0]

        # fetch total records (filtered)
        result["recordsFiltered"] = cur.execute((
            "select count(distinct bgc.id)"
            " from bgc{}"
            " where {}"
        ).format(selector_froms, selector_wheres)).fetchall()[0][0]

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
            " from bgc,dataset where bgc.id in ("
            " select distinct(bgc.id) from bgc{}"
            " where {}"
            " limit ? offset ?)"
            " and dataset.id=bgc.dataset_id"
        ).format(selector_froms, selector_wheres),
                (limit, offset)).fetchall():
            (bgc_id, dataset_id, dataset_name,
             genome, name, length, fragmented) = row

            # fetch basic data
            data = {
                "bgc_id": bgc_id,
                "dataset": dataset_name,
                "genome_name": genome if genome else "n/a",
                "bgc_name": name,
                "bgc_length": length
            }
            if fragmented == 1:
                data["completeness"] = "fragmented"
            elif fragmented == 0:
                data["completeness"] = "complete"
            else:
                data["completeness"] = "n/a"

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
                data["completeness"],
                data["bgc_id"]
            ])

    return result
