#!/usr/bin/env python3

from flask import render_template
import sqlite3

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('home', __name__)


@blueprint.route("/home")
def page_home():

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()
        clustering_id, threshold = cur.execute((
            "select clustering.id, clustering.threshold"
            " from run,clustering"
            " where run.status >= 7"
            " and run.id=clustering.run_id"
            " order by run.id desc"
            " limit 1"
        )).fetchall()[0]

        bgc_total, gcf_total = cur.execute((
            "select count(bgc_id), count(gcf_id)"
            " from gcf_membership,gcf"
            " where gcf_membership.gcf_id=gcf.id"
            " and gcf.clustering_id=?"
            " and gcf_membership.rank=0"
        ), (clustering_id, )).fetchall()[0]

    # page title
    page_title = "Welcome to the BiG-FAM database!"
    page_subtitle = (
        ""
    )

    # render view
    return render_template(
        "home/main.html.j2",
        page_title=page_title,
        page_subtitle=page_subtitle,
        threshold=threshold,
        bgc_total=bgc_total,
        gcf_total=gcf_total
    )
