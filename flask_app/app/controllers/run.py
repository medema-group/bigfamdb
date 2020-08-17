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
        "run/main.html.j2",
        run_id=run_id,
        status_id=status_id,
        page_title=page_title,
        page_subtitle=page_subtitle,
        datasets_list=datasets_list,
        classes_list=classes_list
    )


@blueprint.route("/api/run/get_gcf_table")
def get_gcf_table():
    """ for gcf datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    # translate request parameters
    run_id = request.args.get('run_id', default=0, type=int)
    result["run_id"] = run_id
    dataset_ids = list(map(int, request.args.getlist('dataset_id[]')))
    chem_class_ids = list(map(int, request.args.getlist('chem_class_id[]')))
    taxon_ids = [int(i) for i in request.args.get(
        'taxons', type=str).split(",") if len(i) > 0]
    hmm_ids = [int(i) for i in request.args.get(
        'hmms', type=str).split(",") if len(i) > 0]
    core_members_from = request.args.get(
        "core_members_from", default=None, type=int)
    core_members_to = request.args.get(
        "core_members_to", default=None, type=int)
    offset = request.args.get('start', type=int)
    limit = request.args.get('length', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # load precalculated db
        cur.execute((
            "attach database ? as precalc"
        ), (conf["precalc_db_path"], ))

        # get selector for gcfs (based only on gcf table)
        selector_froms = ""
        selector_joins = ""
        selector_wheres = "1"
        if isinstance(core_members_from, int) or \
                isinstance(core_members_to, int):
            selector_froms += ",precalc.gcf_summary"
            selector_wheres += (
                " and precalc.gcf_summary.gcf_id=gcf.id"
            )
            if isinstance(core_members_from, int):
                selector_wheres += (
                    " and precalc.gcf_summary.core_members>={}"
                ).format(core_members_from)
            if isinstance(core_members_to, int):
                selector_wheres += (
                    " and precalc.gcf_summary.core_members<={}"
                ).format(core_members_to)
        if len(dataset_ids) > 0:
            selector_froms += ",precalc.gcf_summary_dataset"
            selector_wheres += (
                " and precalc.gcf_summary_dataset.gcf_id=gcf.id"
                " and precalc.gcf_summary_dataset.count>0"
                " and precalc.gcf_summary_dataset.dataset_id in ({})"
            ).format(
                ",".join(map(str, dataset_ids)))
        if len(chem_class_ids) > 0:
            selector_froms += ",precalc.gcf_summary_class"
            selector_froms += ",chem_subclass as gs_sub"
            selector_wheres += (
                " and precalc.gcf_summary_class.gcf_id=gcf.id"
                " and precalc.gcf_summary_class.count>0"
                " and precalc.gcf_summary_class.chem_subclass_id=gs_sub.id"
                " and gs_sub.class_id in ({})"
            ).format(
                ",".join(map(str, chem_class_ids)))
        if len(taxon_ids) > 0:
            selector_froms += ",precalc.gcf_summary_taxon"
            selector_wheres += (
                " and precalc.gcf_summary_taxon.gcf_id=gcf.id"
                " and precalc.gcf_summary_taxon.count>0"
                " and precalc.gcf_summary_taxon.taxon_id in ({})"
            ).format(
                ",".join(map(str, taxon_ids)))
        if len(hmm_ids) > 0:
            for hmm_id in hmm_ids:
                selector_joins += (
                    " inner join (select gcf_id,hmm_id"
                    " from precalc.gcf_domains"
                    " where hmm_id={}) as bd_{}"
                    " on bd_{}.gcf_id=gcf.id"
                ).format(hmm_id, hmm_id, hmm_id)

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
            (
                "select count(distinct gcf.id)"
                " from gcf{}"
                " {}"
                " where clustering_id=? and {}"
            ).format(selector_froms, selector_joins, selector_wheres),
            (clustering_id,)).fetchall()[0][0]

        # get max gcf id

        # fetch data for table
        result["data"] = []
        for row in cur.execute((
            "select gcf.id, gcf.id_in_run"
            ", precalc.gcf_summary.core_members"
            ", precalc.gcf_summary.putative_members"
            " from gcf,precalc.gcf_summary"
            " where gcf.id in ("
            " select distinct gcf.id"
            "  from gcf{}"
            " {}"
            "  where clustering_id=? and {}"
            "  limit ? offset ?"
            " )"
            " and precalc.gcf_summary.gcf_id=gcf.id"
        ).format(selector_froms, selector_joins, selector_wheres), (
                clustering_id, limit, offset)).fetchall():
            gcf_id, gcf_accession, core_members, putative_members = row

            gcf_name = "GCF_{:0{width}d}".format(
                gcf_accession, width=math.ceil(
                    math.log10(result["recordsTotal"])))

            # fetch classes counts
            class_counts = cur.execute(
                (
                    "select chem_class.name || ':' || chem_subclass.name"
                    ", gcf_subclass.count"
                    " from chem_class, chem_subclass"
                    ", precalc.gcf_summary_class as gcf_subclass"
                    " where gcf_subclass.gcf_id=?"
                    " and gcf_subclass.chem_subclass_id=chem_subclass.id"
                    " and chem_subclass.class_id=chem_class.id"
                    " order by gcf_subclass.count desc"
                ),
                (gcf_id, )).fetchall()

            # fetch taxon counts
            taxon_counts = cur.execute(
                (
                    "select taxon.name as taxon"
                    ", gcf_taxon.count"
                    " from taxon"
                    ", precalc.gcf_summary_taxon as gcf_taxon"
                    " where gcf_taxon.gcf_id=?"
                    " and gcf_taxon.taxon_id=taxon.id"
                    " and taxon.level=5"  # genus
                    " order by gcf_taxon.count desc"
                ),
                (gcf_id, )).fetchall()

            result["data"].append([
                gcf_name,  # gcf
                core_members,  # core members
                putative_members,  # putative members
                class_counts,  # representative class
                taxon_counts,  # representative taxon
                gcf_id  # gcf_id
            ])

    return result
