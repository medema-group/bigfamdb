#!/usr/bin/env python3

import sqlite3
from flask import render_template, request, redirect
from flask import url_for
import math
from os import path

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('bgc', __name__)


@blueprint.route("/dataset/<int:dataset_id>/bgc/<int:bgc_id>")
def page_bgc_no_run(dataset_id, bgc_id):
    return redirect(url_for(
        "bgc.page_bgc",
        dataset_id=dataset_id,
        bgc_id=bgc_id,
        run_id=0)
    )


@blueprint.route("/dataset/<int:dataset_id>/bgc/<int:bgc_id>/run/<int:run_id>")
def page_bgc(dataset_id, bgc_id, run_id):

    # page title
    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # load linkages
        cur.execute((
            "attach database ? as linkage"
        ), (conf["linkage_db_path"], ))
        linkages = []
        for name, doi in cur.execute((
            "select name, doi"
            " from linkage_study"
            " where dataset_id=?"
        ), (dataset_id, )).fetchall():
            url_study = (
                "https://doi.org/{}"
            ).format(doi)
            linkages.append((name, url_study))
        for mibig_acc, in cur.execute((
            "select mibig_acc"
            " from linkage_mibig"
            " where bgc_id=?"
        ), (bgc_id, )).fetchall():
            url_mibig = (
                "https://mibig.secondarymetabolites.org"
                "/repository/{}/"
            ).format(mibig_acc)
            linkages.append(("MIBiG", url_mibig))
        for nuccore_acc, start_loc, end_loc in cur.execute((
            "select nuccore_acc, start_loc, end_loc"
            " from linkage_ncbi"
            " where bgc_id=?"
        ), (bgc_id, )).fetchall():
            url_ncbi = (
                "https://www.ncbi.nlm.nih.gov/"
                "nuccore/{}?from={}&to={}"
            ).format(nuccore_acc, start_loc, end_loc)
            linkages.append(("NCBI", url_ncbi))
        for nuccore_acc, start_loc, end_loc in cur.execute((
            "select nuccore_acc, start_loc, end_loc"
            " from linkage_antismashdb"
            " where bgc_id=?"
        ), (bgc_id, )).fetchall():
            url_asdb = (
                "https://antismash-db.secondarymetabolites"
                ".org/area.html?record={}&start={}&end={}"
            ).format(nuccore_acc, start_loc, end_loc)
            linkages.append(("antiSMASH-DB", url_asdb))
        
        # redirect if run_id/dataset_id == 0
        redir = False
        if dataset_id < 1:
            # fetch appropriate dataset_id
            dataset_id = cur.execute((
                "select dataset_id"
                " from bgc"
                " where id=?"
            ), (bgc_id, )).fetchall()[0][0]
            redir = True
        if run_id < 1:
            # fetch latest run
            run_id = cur.execute((
                "select id"
                " from run"
                " order by id desc"
                " limit 1"
            )).fetchall()[0][0]
            redir = True
        if redir:
            return redirect(url_for(
                "bgc.page_bgc",
                dataset_id=dataset_id,
                bgc_id=bgc_id,
                run_id=run_id)
            )

        # fetch bgc_name, dataset_name
        bgc_name, dataset_name = cur.execute((
            "select bgc.name, dataset.name"
            " from bgc, dataset"
            " where bgc.id=?"
            " and bgc.dataset_id=?"
            " and bgc.dataset_id=dataset.id"
        ), (bgc_id, dataset_id)).fetchall()[0]

        # fetch taxon for subtitle
        bgc_taxon_name = cur.execute((
            "select taxon.name"
            " from bgc_taxonomy, taxon, bgc"
            " where bgc.id=bgc_taxonomy.bgc_id"
            " and taxon.id=bgc_taxonomy.taxon_id"
            " and bgc.id=?"
            " order by taxon.level desc"
            " limit 1"
        ), (bgc_id, )).fetchall()[:1]

        # fetch clustering threshold
        threshold = cur.execute((
            "select threshold"
            " from clustering"
            " where clustering.run_id=?"
        ), (run_id, )).fetchall()[0][0]

        # set title and subtitle
        page_title = "BGC: {}".format(bgc_name)
        if len(bgc_taxon_name) <= 0:
            page_subtitle = ("From dataset: {}".format(dataset_name))
        else:
            page_subtitle = (
                "From <i>{}</i> (dataset: {})".format(
                    bgc_taxon_name[0][0], dataset_name))

        # status_id
        status_id, = cur.execute((
            "select status"
            " from run"
            " where id = ?"
        ), (run_id, )).fetchall()[0]

        # for run selector dropdown
        run_ids = [row[0] for row
                   in cur.execute((
                       "select id"
                       " from run"
                       " order by id asc"
                   )).fetchall()]

    # render view
    return render_template(
        "bgc/main.html.j2",
        bgc_id=bgc_id,
        linkages=linkages,
        dataset_id=dataset_id,
        run_id=run_id,
        run_ids=run_ids,
        threshold=threshold,
        status_id=status_id,
        page_title=page_title,
        page_subtitle=page_subtitle
    )

# APIs


@blueprint.route("/api/bgc/get_overview")
def get_overview():
    """ for bgc overview tables """
    result = {}
    bgc_id = request.args.get('bgc_id', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # fetch direct properties
        (folder_path, file_path, on_contig_edge,
         result["length"], result["type"],
         result["type_desc"]) = cur.execute((
             "select orig_folder, orig_filename,"
             " on_contig_edge, length_nt, type,"
             " enum_bgc_type.description"
             " from bgc, enum_bgc_type"
             " where bgc.id=?"
             " and bgc.type=enum_bgc_type.code"
         ), (bgc_id, )).fetchall()[0]
        result["file_path"] = path.join("/", folder_path, file_path)
        result["fragmented"] = "yes" if on_contig_edge == 1 else (
            "no" if on_contig_edge == 0 else "n/a"
        )

        # fetch genes count
        result["genes_count"] = cur.execute((
            "select count(id)"
            " from cds"
            " where bgc_id=?"
        ), (bgc_id, )).fetchall()[0][0]

        # fetch taxonomy information
        result["taxon_desc"] = cur.execute((
            "select level, name"
            " from taxon_class"
            " order by level asc"
        )).fetchall()
        result["taxonomy"] = {
            row[0]: row[1] for row in cur.execute((
                "select level, taxon.name"
                " from taxon, bgc_taxonomy"
                " where taxon.id=bgc_taxonomy.taxon_id"
                " and bgc_taxonomy.bgc_id=?"
            ), (bgc_id, )).fetchall()
        }

        # fetch class information
        result["classes"] = cur.execute((
            "select chem_class.name, chem_subclass.name"
            " from bgc, bgc_class, chem_subclass, chem_class"
            " where bgc.id=bgc_class.bgc_id"
            " and bgc_class.chem_subclass_id=chem_subclass.id"
            " and chem_subclass.class_id=chem_class.id"
            " and bgc.id=?"
        ), (bgc_id, )).fetchall()

    return result


@blueprint.route("/api/bgc/get_arrower_objects")
def get_arrower_objects():
    """ for arrower js """
    result = {}
    bgc_ids = map(int, request.args.get('bgc_id', type=str).split(","))
    run_id = request.args.get('run_id', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        for bgc_id in bgc_ids:
            data = {}

            # get bgc name, length and description
            bgc_name, bgc_length, dataset_name = cur.execute((
                "select bgc.name, bgc.length_nt, dataset.name"
                " from bgc, dataset"
                " where bgc.id=?"
                " and bgc.dataset_id=dataset.id"
            ), (bgc_id, )).fetchall()[0]
            bgc_taxon_name = cur.execute((
                "select taxon.name"
                " from bgc_taxonomy, taxon, bgc"
                " where bgc.id=bgc_taxonomy.bgc_id"
                " and taxon.id=bgc_taxonomy.taxon_id"
                " and bgc.id=?"
                " order by taxon.level desc"
                " limit 1"
            ), (bgc_id, )).fetchall()[:1]

            data["id"] = "BGC: {}".format(bgc_name)
            data["start"] = 0
            data["end"] = bgc_length
            if len(bgc_taxon_name) <= 0:
                data["desc"] = ("From dataset: {}".format(dataset_name))
            else:
                data["desc"] = (
                    "From <i>{}</i> (dataset: {})".format(
                        bgc_taxon_name[0][0], dataset_name))

            # get cds
            data["orfs"] = []
            for cds_id, locus_tag, protein_id, \
                    cds_start, cds_end, cds_strand in cur.execute((
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
                for dom_id, dom_name, bitscore, dom_start, dom_end, \
                        sub_ids, sub_names, sub_scores in cur.execute((
                            "select hmm_id, hmm_name,"
                            " bitscore, cds_start, cds_end,"
                            " group_concat(sub_id),"
                            " group_concat(sub_name),"
                            " group_concat(sub_score)"
                            " from"
                            " (select hsp.id as hsp_id, hmm.id as hmm_id,"
                            " hmm.name as hmm_name, hsp.bitscore as bitscore,"
                            " hsp_alignment.cds_start as cds_start,"
                            " hsp_alignment.cds_end as cds_end,"
                            " hmmsub.id as sub_id,"
                            " substr(hmmsub.name,"
                            " instr(hmmsub.name, 'aligned_c')+8) as sub_name,"
                            " hspsub.bitscore as sub_score"
                            " from hmm, hsp, hsp_alignment, run"
                            " left join hsp_subpfam"
                            " on hsp_subpfam.hsp_parent_id=hsp.id"
                            " left join hsp as hspsub"
                            " on hspsub.id=hsp_subpfam.hsp_subpfam_id"
                            " left join hmm as hmmsub"
                            " on hmmsub.id=hspsub.hmm_id"
                            " where hsp.cds_id=?"
                            " and hsp_alignment.hsp_id=hsp.id"
                            " and hmm.id=hsp.hmm_id"
                            " and hmm.db_id=run.hmm_db_id"
                            " and run.id=?"
                            " order by cds_start, hspsub.bitscore asc"
                            ") group by hsp_id"
                        ), (cds_id, run_id)).fetchall():  # hsps:
                    dom_code = dom_name
                    if sub_ids:
                        dom_code += " [{}]".format(sub_names)
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


@blueprint.route("/api/bgc/get_word_cloud")
def get_word_cloud():
    """ for bgc features word cloud """
    result = {}
    bgc_id = request.args.get('bgc_id', type=int)
    limit = request.args.get('limit', default=20, type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        result["words"] = []
        for name, weight in cur.execute((
            "select hmm.name,"
            " case"
            " when subpfam.parent_hmm_id > 0"
            " then sum(hsp.bitscore)"
            " else count(hsp.bitscore)*255"
            " end weight"
            " from hsp, cds, hmm"
            " left join subpfam on hmm.id=subpfam.hmm_id"
            " where hsp.cds_id=cds.id"
            " and cds.bgc_id=?"
            " and hsp.hmm_id=hmm.id"
            " group by hmm.name"
            " order by weight desc"
            " limit ?"
        ), (bgc_id, limit)).fetchall():
            result["words"].append({
                "text": name,
                "weight": weight
            })

    return result


@blueprint.route("/api/bgc/get_genes_table")
def get_genes_table():
    """ for genes datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    # translate request parameters
    bgc_id = request.args.get('bgc_id', type=int)
    run_id = request.args.get('run_id', type=int)
    offset = request.args.get('start', type=int)
    limit = request.args.get('length', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # fetch total records (all bgcs in the dataset)
        result["recordsTotal"] = cur.execute((
            "select count(id)"
            " from cds"
            " where bgc_id=?"
        ), (bgc_id,)).fetchall()[0][0]

        # fetch total records (filtered)
        result["recordsFiltered"] = cur.execute((
            "select count(id)"
            " from cds"
            " where bgc_id=?"
        ), (bgc_id,)).fetchall()[0][0]

        # fetch data for table
        result["data"] = []
        for cds_id, start, end, strand, locus_tag, \
                protein_id, product, aa_seq in cur.execute((
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

            for dom_id, dom_name, bitscore, dom_start, dom_end, \
                    sub_ids, sub_names, sub_scores in cur.execute((
                        "select hmm_id, hmm_name,"
                        " bitscore, cds_start, cds_end,"
                        " group_concat(sub_id),"
                        " group_concat(sub_name),"
                        " group_concat(sub_score)"
                        " from"
                        " (select hsp.id as hsp_id, hmm.id as hmm_id,"
                        " hmm.name as hmm_name, hsp.bitscore as bitscore,"
                        " hsp_alignment.cds_start as cds_start,"
                        " hsp_alignment.cds_end as cds_end,"
                        " hmmsub.id as sub_id,"
                        " substr(hmmsub.name,"
                        " instr(hmmsub.name, 'aligned_c')+8) as sub_name,"
                        " hspsub.bitscore as sub_score"
                        " from hmm, hsp, hsp_alignment, run"
                        " left join hsp_subpfam"
                        " on hsp_subpfam.hsp_parent_id=hsp.id"
                        " left join hsp as hspsub"
                        " on hspsub.id=hsp_subpfam.hsp_subpfam_id"
                        " left join hmm as hmmsub"
                        " on hmmsub.id=hspsub.hmm_id"
                        " where hsp.cds_id=?"
                        " and hsp_alignment.hsp_id=hsp.id"
                        " and hmm.id=hsp.hmm_id"
                        " and hmm.db_id=run.hmm_db_id"
                        " and run.id=?"
                        " order by cds_start, hspsub.bitscore asc"
                        ") group by hsp_id"
                    ), (cds_id, run_id)).fetchall():
                dom_code = dom_name
                if sub_ids:
                    dom_code += " [{}]".format(sub_names)
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


@blueprint.route("/api/bgc/get_gcf_hits_table")
def get_gcf_hits_table():
    """ for gcf hits datatable """
    result = {}
    result["draw"] = request.args.get('draw', type=int)

    # translate request parameters
    bgc_id = request.args.get('bgc_id', type=int)
    run_id = request.args.get('run_id', type=int)
    result["run_id"] = run_id
    offset = request.args.get('start', type=int)
    limit = request.args.get('length', type=int)

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()

        # load precalculated db
        cur.execute((
            "attach database ? as precalc"
        ), (conf["precalc_db_path"], ))

        # set clustering id and threshold
        clustering_id, threshold = cur.execute(
            ("select id, threshold"
             " from clustering"
             " where run_id=?"),
            (run_id, )
        ).fetchall()[0]

        # fetch total gcf count for this run
        result["totalGCFrun"] = cur.execute((
            "select count(id)"
            " from gcf"
            " where gcf.clustering_id=?"
        ), (clustering_id,)).fetchall()[0][0]

        # fetch total records (all gcf in bgc)
        result["recordsTotal"] = cur.execute((
            "select count(gcf_id)"
            " from gcf, gcf_membership"
            " where bgc_id=?"
            " and gcf.id=gcf_membership.gcf_id"
            " and gcf.clustering_id=?"
        ), (bgc_id, clustering_id)).fetchall()[0][0]

        # fetch total records (filtered)
        result["recordsFiltered"] = cur.execute((
            "select count(gcf_id)"
            " from gcf, gcf_membership"
            " where bgc_id=?"
            " and gcf.id=gcf_membership.gcf_id"
            " and gcf.clustering_id=?"
        ), (bgc_id, clustering_id)).fetchall()[0][0]

        # fetch data for table
        result["data"] = []
        for row in cur.execute((
            "select membership_value, gcf.id, gcf.id_in_run"
            ", precalc.gcf_summary.core_members"
            ", precalc.gcf_summary.putative_members"
            " from gcf,precalc.gcf_summary"
            " inner join ("
            " select gcf.id as A_gcf_id, gcf_membership.membership_value"
            " from gcf, gcf_membership"
            " where bgc_id=?"
            " and gcf.id=gcf_membership.gcf_id"
            " and gcf.clustering_id=?"
            " order by membership_value asc"
            " limit ? offset ?"
            " ) on A_GCF_id=gcf.id"
            " and precalc.gcf_summary.gcf_id=gcf.id"
        ), (bgc_id, clustering_id, limit, offset)).fetchall():
            membership_value, gcf_id, gcf_accession, \
                core_members, putative_members = row

            # fetch gcf name
            gcf_name = "GCF_{:0{width}d}".format(
                gcf_accession, width=math.ceil(
                    math.log10(result["totalGCFrun"])))

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
                membership_value,
                (gcf_id, gcf_name),
                core_members,
                class_counts,
                taxon_counts
            ])
    return result
