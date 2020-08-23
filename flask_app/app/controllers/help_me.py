#!/usr/bin/env python3

import sqlite3
from flask import render_template, url_for

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
            "How were the GCFs hosted in BiG-FAM calculated?",
            (
                "GCFs hosted here were reconstructed using the"
                " BiG-SLICE algorithm. A description of this"
                " algorithm can be found in the <a target='_blank'"
                " href='https://doi.org/10.1101/2020.08.17.240838'>"
                "BiG-SLiCE preprint</a>."
            )
        ),
        (
            "How do I compare my own BGC against the GCFs in BiG-FAM?",
            (
                "First, you run <a href='https://antismash."
                "secondarymetabolites.org' target='_blank'>"
                "antiSMASH</a> (or <a href='https://fungismash."
                "secondarymetabolites.org' target='_blank'>"
                "fungiSMASH</a>) on your genome/assembly."
                " It will then provide you with a job ID"
                " (i.e. <strong>bacteria-3db13cf8-3367-4428-b305"
                "-6a3ce6d8bb0e</strong>). Once the job finishes "
                "(and not before!), you can insert this"
                " job ID into the input field on the "
                "<a href='{}' target='_blank'>query page"
                "</a> and then click ‘Submit’. After the"
                " querying compute finishes, the output page"
                " will show you distances to the GCFs most"
                " closely related to your query BGC. You can"
                " then view these GCFs to study the genetic"
                " architectures and taxonomic distribution"
                " of the underlying BGCs."
            ).format(
                url_for("query.page_query")
            )
        ),
        (
            "Can I set up a copy of this database on my own (local) servers?",
            (
                "Yes. Just follow the instruction provided in the"
                " source code for the BiG-FAM database:"
                " <a href='{}' target='_blank'>{}</a>."
                " All code is freely available under a"
                " <a href='{}' target='_blank'>GNU Affero"
                " General Public License v3.0.</a>"
            ).format(
                "https://github.com/medema-group/bigfamdb/",
                "https://github.com/medema-group/bigfamdb/",
                "https://www.gnu.org/licenses/gpl-3.0.en.html",
            )
        ),
        (
            "From which studies were the genomes and MAGs used in BiG-FAM sourced?",
            (
                "Please refer to "
                "<a href='{}#input_data' target='_blank'>this table</a>."
            ).format(
                url_for("stats.page_stats")
            )
        ),
        (
            "How do I (bulk) download GCF data from BiG-FAM?",
            (
                "For BiG-FAM version 1.0.0, we used the same data"
                " generated from BiG-SLiCE study: <a href='{}'"
                " target='_blank'>{}</a> (data is licensed under"
                " a <a href='{}' target='_blank'>Creative Commons"
                " CC-BY license</a>)."
            ).format(
                "https://bioinformatics.nl/~kauts001/ltr/bigslice/paper_data/",                
                "https://bioinformatics.nl/~kauts001/ltr/bigslice/paper_data/",
                "http://creativecommons.org/licenses/by/4.0/"
            )
        ),
        (
            "How do I cite BiG-FAM?",
            (
                "Please refer to <a href='{}#about_cite' target='_blank'>"
                "this page</a>."
            ).format(
                url_for("about.page_about")
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
