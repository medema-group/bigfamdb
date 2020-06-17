#!/usr/bin/env python3

import sqlite3
from flask import render_template

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('help_me', __name__)


@blueprint.route("/help")
def page_help():

    # todo: implements

    # page title
    page_title = "Help"
    page_subtitle = ("")

    # FAQs
    faqs = [
        (
            "Please help us!",
            (
                "We're collecting questions from users to put in this FAQ"
                " section. Feel free to send yours to our e-mail (see above)."
            )
        )
    ]

    # render view
    return render_template(
        "help/main.html.j2",
        page_title=page_title,
        page_subtitle=page_subtitle,
        faqs=faqs
    )
