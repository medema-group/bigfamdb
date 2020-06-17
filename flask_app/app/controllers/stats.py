#!/usr/bin/env python3

import sqlite3
from flask import render_template

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('stats', __name__)


@blueprint.route("/stats")
def page_stats():

    # todo: implements

    # page title
    page_title = "Statistics"
    page_subtitle = ("")

    # render view
    return render_template(
        "stats/main.html.j2",
        page_title=page_title,
        page_subtitle=page_subtitle
    )
