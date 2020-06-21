#!/usr/bin/env python3

import sqlite3
import math
from flask import render_template, redirect, request
from flask import url_for
from os import path
from datetime import datetime

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('query', __name__)


@blueprint.route("/query")
def page_query():

    # page title
    page_title = "Query"
    page_subtitle = ("")

    # fetch jobs count
    jobs_db = conf["jobs_db_path"]
    if path.exists(jobs_db):
        with sqlite3.connect(jobs_db) as con:
            cur = con.cursor()
            pending = cur.execute((
                "select count(name)"
                " from jobs"
                " where status=?"
            ), (0, )).fetchall()[0][0]
            processing = cur.execute((
                "select count(name)"
                " from jobs"
                " where status=?"
                " or status=?"
            ), (1, 2)).fetchall()[0][0]
            processed = cur.execute((
                "select count(name)"
                " from jobs"
                " where status=?"
            ), (3, )).fetchall()[0][0]
    else:
        pending, processing, processed = (-1, -1, -1)

    # render view
    return render_template(
        "query/main.html.j2",
        page_title=page_title,
        page_subtitle=page_subtitle,
        example_query_id=conf["example_query_id"],
        pending=pending,
        processing=processing,
        processed=processed
    )


@blueprint.route("/query/submit/<string:job_id>")
def page_submit(job_id):

    # check/insert queue
    jobs_db = conf["jobs_db_path"]
    if path.exists(jobs_db):
        with sqlite3.connect(jobs_db) as con:
            cur = con.cursor()
            # insert if not exist
            if cur.execute((
                "select count(name)"
                " from jobs"
                " where name like ?"
            ), (job_id, )).fetchall()[0][0] < 1:
                cur.execute((
                    "insert into jobs"
                    " (name,submitted,status)"
                    " values(?,?,?)"
                ), (
                    job_id,
                    datetime.now(),
                    0
                ))
                con.commit()
                print(
                    "Inserted new job! " + job_id
                )

    # render view
    return redirect(url_for("query.page_view", job_id=job_id))


@blueprint.route("/query/view/<string:job_id>")
def page_view(job_id):

    # fetch query status
    with sqlite3.connect(conf["jobs_db_path"]) as con:
        cur = con.cursor()
        status, status_name, submitted = cur.execute((
            "select status, status_enum.name, submitted"
            " from jobs, status_enum"
            " where jobs.name like ?"
            " and status_enum.code=jobs.status"
        ), (job_id, )).fetchall()[0]

    if status > 2:
        # fetch query id and date
        with sqlite3.connect(conf["reports_db_path"]) as con:
            cur = con.cursor()
            with sqlite3.connect(conf["db_path"]) as con_source:
                cur_source = con_source.cursor()

                report_id, created = cur.execute((
                    "select id, creation_date"
                    " from reports"
                    " where name like ?"
                    " and type=?"
                ), (job_id, "query")).fetchall()[0]

                # set run_id
                run_id = cur.execute((
                    "select run_id"
                    " from reports_run"
                    " where report_id=?"
                ), (report_id, )).fetchall()[0][0]

                # set clustering id, get threshold
                clustering_id, threshold = cur_source.execute(
                    ("select id, threshold"
                     " from clustering"
                     " where run_id=?"),
                    (run_id, )
                ).fetchall()[0]
    else:
        report_id = -1,
        run_id = -1,
        clustering_id = -1,
        threshold = -1

    # page title
    page_title = "Query result: {}".format(job_id)
    page_subtitle = "Overview of all BGC to GCF hits in this query."

    # render view
    return render_template(
        "query/view/main.html.j2",
        page_title=page_title,
        page_subtitle=page_subtitle,
        job_id=job_id,
        status=status,
        status_name=status_name,
        submitted=submitted,
        report_id=report_id,
        run_id=run_id,
        clustering_id=clustering_id,
        threshold=threshold
    )


@blueprint.route("/api/query/bgc_list")
def get_bgc_table():
    """ for bgc datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    # translate request parameters
    report_id = request.args.get('report_id', default=0, type=int)
    result["report_id"] = report_id
    run_id = request.args.get('run_id', default=0, type=int)
    result["run_id"] = run_id
    offset = request.args.get('start', type=int)
    limit = request.args.get('length', type=int)

    # validate report id & run id
    with sqlite3.connect(conf["reports_db_path"]) as con:

        cur = con.cursor()
        if len(cur.execute((
            "select id"
            " from reports"
            " where id=?"
            " and type=?"
        ), (report_id, "query")).fetchall()) < 1:
            return "500: data not available"

        if len(cur.execute((
            "select run_id"
            " from reports_run"
            " where report_id=?"
            " and run_id=?"
        ), (report_id, run_id)).fetchall()) < 1:
            return "500: data not available"

    db_query_path = path.join(
        conf["reports_folder"], str(report_id), "data.db")
    with sqlite3.connect(db_query_path) as con:
        cur = con.cursor()
        with sqlite3.connect(conf["db_path"]) as con_source:
            cur_source = con_source.cursor()

            # set clustering id, get threshold
            clustering_id, result["threshold"] = cur_source.execute(
                ("select id, threshold"
                 " from clustering"
                 " where run_id=?"),
                (run_id, )
            ).fetchall()[0]

            # fetch total gcf count for this run
            result["totalGCFrun"] = cur_source.execute((
                "select count(id)"
                " from gcf"
                " where gcf.clustering_id=?"
            ), (clustering_id,)).fetchall()[0][0]

            # fetch total records (all bgcs in the dataset)
            result["recordsTotal"] = cur.execute((
                "select count(id)"
                " from bgc"
                " order by id asc"
            )).fetchall()[0][0]

            # fetch total records (filtered)
            result["recordsFiltered"] = cur.execute((
                "select count(id)"
                " from bgc"
                " order by id asc"
            )).fetchall()[0][0]

            # fetch data for table
            result["data"] = []
            for bgc_id, bgc_name, bgc_length, on_contig_edge, gcf_id, \
                    membership_value in cur.execute((
                        "select bgc.id, bgc.orig_filename, bgc.length_nt,"
                        " bgc.on_contig_edge,"
                        " gcf_membership.gcf_id,"
                        " gcf_membership.membership_value"
                        " from bgc, gcf_membership"
                        " where gcf_membership.bgc_id=bgc.id"
                        " and gcf_membership.rank=0"
                        " order by bgc.orig_filename asc"
                        " limit ? offset ?"
                    ), (limit, offset)).fetchall():

                # fetch completeness
                if on_contig_edge == 1:
                    comp = "fragmented"
                elif on_contig_edge == 0:
                    comp = "complete"
                else:
                    comp = "n/a"

                # fetch class information
                subclass_ids = [str(row[0]) for row in cur.execute((
                    "select distinct chem_subclass_id"
                    " from bgc_class"
                    " where bgc_id=?"
                ), (bgc_id, )).fetchall()]
                class_names = cur_source.execute((
                    "select chem_class.name, chem_subclass.name"
                    " from chem_subclass, chem_class"
                    " where chem_subclass.class_id=chem_class.id"
                    " and chem_subclass.id in ({})".format(
                        ",".join(subclass_ids))
                )).fetchall()

                # fetch gcf information
                gcf_accession = cur_source.execute((
                    "select id_in_run"
                    " from gcf"
                    " where id=?"
                ), (gcf_id, )).fetchall()[0][0]
                gcf_name = "GCF_{:0{width}d}".format(
                    gcf_accession, width=math.ceil(
                        math.log10(result["totalGCFrun"])))

                result["data"].append([
                    bgc_name,
                    class_names,
                    "{:.02f}".format(bgc_length / 1000),
                    comp,
                    (gcf_id, gcf_name),
                    membership_value,
                    bgc_id
                ])

            return result

# ------ detail view


@blueprint.route("/query/view/<string:job_id>/bgc/<int:bgc_id>")
def page_detail(job_id, bgc_id):

    # fetch query name and date
    with sqlite3.connect(conf["reports_db_path"]) as con:
        cur = con.cursor()
        # fetch report_id
        report_id = cur.execute((
            "select id"
            " from reports"
            " where name like ?"
        ), (job_id, )).fetchall()[0][0]
        with sqlite3.connect(conf["db_path"]) as con_source:
            cur_source = con_source.cursor()
            db_query_path = path.join(
                conf["reports_folder"], str(report_id), "data.db")
            with sqlite3.connect(db_query_path) as con_query:
                cur_query = con_query.cursor()

                name, created = cur.execute((
                    "select name, strftime('%Y-%m-%d %H:%M:%S', creation_date)"
                    " from reports"
                    " where id=?"
                    " and type=?"
                ), (report_id, "query")).fetchall()[0]

                # set run_id
                run_id = cur.execute((
                    "select run_id"
                    " from reports_run"
                    " where report_id=?"
                ), (report_id, )).fetchall()[0][0]

                # fetch bgc name
                bgc_name = cur_query.execute((
                    "select orig_filename"
                    " from bgc"
                    " where id=?"
                ), (bgc_id, )).fetchall()[0][0]

                # set clustering id, get threshold
                clustering_id, threshold = cur_source.execute(
                    ("select id, threshold"
                     " from clustering"
                     " where run_id=?"),
                    (run_id, )
                ).fetchall()[0]

    # page title
    page_title = "Query result: {}".format(bgc_name)
    page_subtitle = "From query: '{}'".format(name)

    # render view
    return render_template(
        "query/view/detail/main.html.j2",
        page_title=page_title,
        page_subtitle=page_subtitle,
        bgc_id=bgc_id,
        run_id=run_id,
        report_id=report_id,
        clustering_id=clustering_id,
        threshold=threshold
    )


@blueprint.route("/api/query/detail/overview")
def detail_get_overview():
    """ for bgc overview tables """
    result = {}
    bgc_id = request.args.get('bgc_id', type=int)
    report_id = request.args.get('report_id', type=int)
    run_id = request.args.get('run_id', type=int)
    result["run_id"] = run_id
    result["run_name"] = "run-{:04d}".format(run_id)
    db_query_path = path.join(
        conf["reports_folder"], str(report_id), "data.db")

    with sqlite3.connect(conf["reports_db_path"]) as con:
        cur = con.cursor()
        with sqlite3.connect(conf["db_path"]) as con_source:
            cur_source = con_source.cursor()
            with sqlite3.connect(db_query_path) as con_query:
                cur_query = con_query.cursor()

                # fetch query created
                result["run_created"] = cur.execute((
                    "select strftime('%Y-%m-%d %H:%M:%S', creation_date)"
                    " from reports"
                    " where id=?"
                ), (report_id, )).fetchall()[0][0]

                # fetch threshold
                result["threshold"] = cur_source.execute(
                    ("select threshold"
                     " from clustering"
                     " where run_id=?"),
                    (run_id, )
                ).fetchall()[0][0]

                # fetch direct properties
                (folder_path, file_path, on_contig_edge,
                 result["length"], result["type"]) = cur_query.execute((
                     "select orig_folder, orig_filename,"
                     " on_contig_edge, length_nt, type"
                     " from bgc"
                     " where bgc.id=?"
                 ), (bgc_id, )).fetchall()[0]
                result["file_path"] = path.join("/", folder_path, file_path)
                result["fragmented"] = "yes" if on_contig_edge == 1 else (
                    "no" if on_contig_edge == 0 else "n/a"
                )

                # fetch type desc
                result["type_desc"] = cur_source.execute((
                    "select description"
                    " from enum_bgc_type"
                    " where code=?"
                ), (result["type"], )).fetchall()[0][0]

                # fetch genes count
                result["genes_count"] = cur_query.execute((
                    "select count(id)"
                    " from cds"
                    " where bgc_id=?"
                ), (bgc_id, )).fetchall()[0][0]

                # fetch class information
                subclass_ids = [str(row[0]) for row in cur_query.execute((
                    "select distinct chem_subclass_id"
                    " from bgc_class"
                    " where bgc_id=?"
                ), (bgc_id, )).fetchall()]
                result["classes"] = cur_source.execute((
                    "select chem_class.name, chem_subclass.name"
                    " from chem_subclass, chem_class"
                    " where chem_subclass.class_id=chem_class.id"
                    " and chem_subclass.id in ({})".format(
                        ",".join(subclass_ids))
                )).fetchall()

    return result


@blueprint.route("/api/query/detail/get_arrower_objects")
def detail_get_arrower_objects():
    """ for arrower js """
    result = {}
    bgc_ids = map(int, request.args.get('bgc_id', type=str).split(","))
    report_id = request.args.get('report_id', type=int)

    db_query_path = path.join(
        conf["reports_folder"], str(report_id), "data.db")

    with sqlite3.connect(conf["db_path"]) as con_source:
        cur_source = con_source.cursor()
        with sqlite3.connect(db_query_path) as con_query:
            cur_query = con_query.cursor()

        for bgc_id in bgc_ids:
            data = {}

            # get bgc name, length and description
            bgc_name, bgc_length = cur_query.execute((
                "select bgc.name, bgc.length_nt"
                " from bgc"
                " where id=?"
            ), (bgc_id, )).fetchall()[0]

            data["id"] = "BGC: {}".format(bgc_name)
            data["start"] = 0
            data["end"] = bgc_length
            data["desc"] = ""

            # get cds
            data["orfs"] = []
            for cds_id, locus_tag, protein_id, \
                    cds_start, cds_end, cds_strand in cur_query.execute((
                        "select id, locus_tag, protein_id,"
                        " nt_start, nt_end, strand"
                        " from cds"
                        " where bgc_id=?"
                        " order by nt_start asc"
                    ), (bgc_id, )).fetchall():
                orf = {
                    "start": cds_start,
                    "end": cds_end,
                    "strand": cds_strand
                }

                orf_names = []
                if locus_tag:
                    orf_names.append(locus_tag)
                if protein_id:
                    orf_names.append(protein_id)
                if len(orf_names) < 1:
                    orf_names.append("n/a")
                orf["id"] = " / ".join(orf_names)

                orf["domains"] = []

                # get hsps
                for dom_id, bitscore, dom_start, dom_end, \
                        sub_ids, sub_scores in cur_query.execute((
                            "select hmm_id,"
                            " bitscore, cds_start, cds_end,"
                            " group_concat(sub_id),"
                            " group_concat(sub_score)"
                            " from"
                            " (select hsp.id as hsp_id,"
                            " hsp.hmm_id as hmm_id,"
                            " hsp.bitscore as bitscore,"
                            " hsp_alignment.cds_start as cds_start,"
                            " hsp_alignment.cds_end as cds_end,"
                            " hspsub.hmm_id as sub_id,"
                            " hspsub.bitscore as sub_score"
                            " from hsp, hsp_alignment"
                            " left join hsp_subpfam"
                            " on hsp_subpfam.hsp_parent_id=hsp.id"
                            " left join hsp as hspsub"
                            " on hspsub.id=hsp_subpfam.hsp_subpfam_id"
                            " where hsp.cds_id=?"
                            " and hsp_alignment.hsp_id=hsp.id"
                            " order by cds_start, hspsub.bitscore asc"
                            ") group by hsp_id"
                        ), (cds_id,)).fetchall():  # hsps:

                    # get hmm names
                    hmm_names = {
                        hmm_id: name for (
                            hmm_id, name
                        ) in cur_source.execute((
                            "select id, name from hmm"
                            " where id in ({},{})"
                        ).format(
                            dom_id,
                            sub_ids if sub_ids else dom_id
                        )).fetchall()
                    }

                    dom_code = hmm_names[dom_id]
                    if sub_ids:
                        dom_code += " [{}]".format(
                            ",".join([
                                hmm_names[
                                    int(sub_id)
                                ].split("aligned_")[
                                    -1
                                ] for sub_id in sub_ids.split(",")
                            ]))

                    hsp = {
                        "code": dom_code,
                        "bitscore": bitscore,
                        "start": dom_start,
                        "end": dom_end
                    }

                    orf["domains"].append(hsp)

                data["orfs"].append(orf)

            # append
            result[bgc_id] = data

    return result


@blueprint.route("/api/query/detail/get_word_cloud")
def detail_get_word_cloud():
    """ for bgc features word cloud """
    result = {}
    bgc_id = request.args.get('bgc_id', type=int)
    report_id = request.args.get('report_id', type=int)
    limit = request.args.get('limit', default=20, type=int)

    db_query_path = path.join(
        conf["reports_folder"], str(report_id), "data.db")

    with sqlite3.connect(conf["db_path"]) as con_source:
        cur_source = con_source.cursor()
        with sqlite3.connect(db_query_path) as con_query:
            cur_query = con_query.cursor()

            result["words"] = []

            # get bitscores
            bitscores = {
                hmm_id: list(map(float, bitscore.split(","))) for (
                    hmm_id, bitscore
                ) in cur_query.execute((
                    "select hmm_id, group_concat(hsp.bitscore)"
                    " from hsp, cds"
                    " where hsp.cds_id=cds.id"
                    " and cds.bgc_id=?"
                    " group by hmm_id"
                ), (bgc_id, )).fetchall()
            }

            # get weights
            weights = {}
            for subpfam_id, in cur_source.execute((
                "select hmm_id"
                " from subpfam"
                " where hmm_id in ({})"
            ).format(
                ",".join(map(str, bitscores.keys()))
            )).fetchall():
                weights[subpfam_id] = sum(bitscores[subpfam_id])
            for hmm_id in bitscores:
                if hmm_id not in weights:
                    weights[hmm_id] = len(bitscores[hmm_id]) * 255

            # get hmm names
            hmm_names = {
                hmm_id: name for (
                    hmm_id, name
                ) in cur_source.execute((
                    "select id, name from hmm"
                    " where id in ({})"
                ).format(
                    ",".join(map(str, weights.keys()))
                )).fetchall()
            }

            for hmm_id, weight in sorted(weights.items(), reverse=False):
                if len(result["words"]) < limit:
                    result["words"].append({
                        "text": hmm_names[hmm_id],
                        "weight": weight
                    })
                else:
                    break

    return result


@blueprint.route("/api/query/detail/get_genes_table")
def detail_get_genes_table():
    """ for genes datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    # translate request parameters
    bgc_id = request.args.get('bgc_id', type=int)
    report_id = request.args.get('report_id', type=int)
    offset = request.args.get('start', type=int)
    limit = request.args.get('length', type=int)

    db_query_path = path.join(
        conf["reports_folder"], str(report_id), "data.db")

    with sqlite3.connect(conf["db_path"]) as con_source:
        cur_source = con_source.cursor()
        with sqlite3.connect(db_query_path) as con_query:
            cur_query = con_query.cursor()

            # fetch total records (all bgcs in the dataset)
            result["recordsTotal"] = cur_query.execute((
                "select count(id)"
                " from cds"
                " where bgc_id=?"
            ), (bgc_id,)).fetchall()[0][0]

            # fetch total records (filtered)
            result["recordsFiltered"] = cur_query.execute((
                "select count(id)"
                " from cds"
                " where bgc_id=?"
            ), (bgc_id,)).fetchall()[0][0]

            # fetch data for table
            result["data"] = []
            for cds_id, start, end, strand, locus_tag, \
                    protein_id, product, aa_seq in cur_query.execute((
                        "select id, nt_start, nt_end, strand,"
                        " locus_tag, protein_id, product, aa_seq"
                        " from cds"
                        " where bgc_id=?"
                        " order by nt_start asc"
                        " limit ? offset ?"
                    ), (bgc_id, limit, offset)).fetchall():
                data = {}

                # gene name
                data["names"] = []
                if locus_tag:
                    data["names"].append(locus_tag)
                if protein_id:
                    data["names"].append(protein_id)
                if len(data["names"]) < 1:
                    data["names"].append("n/a")

                # product
                data["product"] = product or "n/a"
                data["locus"] = (start, end, strand)
                data["aa_seq"] = aa_seq

                # domain information
                data["domains"] = []
                for dom_id, bitscore, dom_start, dom_end, \
                        sub_ids, sub_scores in cur_query.execute((
                            "select hmm_id,"
                            " bitscore, cds_start, cds_end,"
                            " group_concat(sub_id),"
                            " group_concat(sub_score)"
                            " from"
                            " (select hsp.id as hsp_id,"
                            " hsp.hmm_id as hmm_id,"
                            " hsp.bitscore as bitscore,"
                            " hsp_alignment.cds_start as cds_start,"
                            " hsp_alignment.cds_end as cds_end,"
                            " hspsub.hmm_id as sub_id,"
                            " hspsub.bitscore as sub_score"
                            " from hsp, hsp_alignment"
                            " left join hsp_subpfam"
                            " on hsp_subpfam.hsp_parent_id=hsp.id"
                            " left join hsp as hspsub"
                            " on hspsub.id=hsp_subpfam.hsp_subpfam_id"
                            " where hsp.cds_id=?"
                            " and hsp_alignment.hsp_id=hsp.id"
                            " order by cds_start, hspsub.bitscore asc"
                            ") group by hsp_id"
                        ), (cds_id,)).fetchall():  # hsps:

                    # get hmm names
                    hmm_names = {
                        hmm_id: name for (
                            hmm_id, name
                        ) in cur_source.execute((
                            "select id, name from hmm"
                            " where id in ({},{})"
                        ).format(
                            dom_id,
                            sub_ids if sub_ids else dom_id
                        )).fetchall()
                    }

                    dom_code = hmm_names[dom_id]
                    if sub_ids:
                        dom_code += " [{}]".format(
                            ",".join([
                                hmm_names[
                                    int(sub_id)
                                ].split("aligned_")[
                                    -1
                                ] for sub_id in sub_ids.split(",")
                            ]))

                    data["domains"].append([
                        dom_code,
                        bitscore,
                        dom_start,
                        dom_end
                    ])

                result["data"].append([
                    data["names"],
                    data["product"],
                    data["locus"],
                    data["domains"],
                    (cds_id, data["aa_seq"])
                ])

    return result


@blueprint.route("/api/query/detail/get_gcf_hits_table")
def detail_get_gcf_hits_table():
    """ for gcf hits datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    # translate request parameters
    bgc_id = request.args.get('bgc_id', type=int)
    report_id = request.args.get('report_id', type=int)
    run_id = request.args.get('run_id', type=int)
    result["run_id"] = run_id
    offset = request.args.get('start', type=int)
    limit = request.args.get('length', type=int)

    db_query_path = path.join(
        conf["reports_folder"], str(report_id), "data.db")

    with sqlite3.connect(conf["db_path"]) as con_source:
        cur_source = con_source.cursor()
        with sqlite3.connect(db_query_path) as con_query:
            cur_query = con_query.cursor()

            # set clustering id and threshold
            clustering_id, threshold = cur_source.execute(
                ("select id, threshold"
                 " from clustering"
                 " where run_id=?"),
                (run_id, )
            ).fetchall()[0]

            # fetch total gcf count for this run
            result["totalGCFrun"] = cur_source.execute((
                "select count(id)"
                " from gcf"
                " where gcf.clustering_id=?"
            ), (clustering_id,)).fetchall()[0][0]

            # fetch total records (all gcf in bgc)
            result["recordsTotal"] = cur_query.execute((
                "select count(distinct gcf_id)"
                " from gcf_membership"
                " where bgc_id=?"
            ), (bgc_id,)).fetchall()[0][0]

            # fetch total records (filtered)
            result["recordsFiltered"] = cur_query.execute((
                "select count(distinct gcf_id)"
                " from gcf_membership"
                " where bgc_id=?"
            ), (bgc_id,)).fetchall()[0][0]

            # fetch data for table
            result["data"] = []
            for gcf_id, membership_value in cur_query.execute((
                "select gcf_id, membership_value"
                " from gcf_membership"
                " where bgc_id=?"
                " order by rank asc"
                " limit ? offset ?"
            ), (bgc_id, limit, offset)).fetchall():

                # fetch gcf accession
                gcf_accession = cur_source.execute((
                    "select id_in_run"
                    " from gcf"
                    " where id=?"
                ), (gcf_id, )).fetchall()[0][0]

                # fetch gcf name
                gcf_name = "GCF_{:0{width}d}".format(
                    gcf_accession, width=math.ceil(
                        math.log10(result["totalGCFrun"])))

                # fetch core members count
                core_members = cur_source.execute(
                    (
                        "select count(bgc_id)"
                        " from gcf_membership"
                        " where gcf_id=?"
                        " and rank=0"
                        " and membership_value <= ?"
                    ),
                    (gcf_id, threshold)).fetchall()[0][0]

                # fetch classes counts
                class_counts = cur_source.execute(
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
                taxon_counts = cur_source.execute(
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
                    membership_value,
                    (gcf_id, gcf_name),
                    core_members,
                    class_counts,
                    taxon_counts
                ])
    return result
