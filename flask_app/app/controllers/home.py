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
        bgc_total="{:,}".format(bgc_total),
        gcf_total="{:,}".format(gcf_total)
    )
