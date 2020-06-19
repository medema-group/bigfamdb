#!/usr/bin/env python3

from flask import Flask
from os import path
import sqlite3

# import global config
from .config import conf

# import controllers
from .controllers import root, home, dataset, run
from .controllers import bgc, gcf, query, stats
from .controllers import about, help_me, feedback


# initiate app
app = Flask(
    __name__,
    template_folder=path.join(path.dirname(path.realpath(__file__)), "views")
)

# register controllers
app.register_blueprint(root.blueprint)
app.register_blueprint(home.blueprint)
app.register_blueprint(dataset.blueprint)
app.register_blueprint(run.blueprint)
app.register_blueprint(bgc.blueprint)
app.register_blueprint(gcf.blueprint)
app.register_blueprint(query.blueprint)
app.register_blueprint(stats.blueprint)
app.register_blueprint(about.blueprint)
app.register_blueprint(help_me.blueprint)
app.register_blueprint(feedback.blueprint)

# app-specific contexts #


@app.context_processor
def inject_global():
    g = {
        "version": "1.0.0"
    }

    # for navigations
    nav_items = []
    nav_items.append(("Home", "/home"))

    with sqlite3.connect(conf["db_path"]) as con:
        cur = con.cursor()
        last_run_id = cur.execute((
            "select id"
            " from run"
            " where status >= 7"
            " order by id desc"
            " limit 1"
        )).fetchall()[0][0]

    nav_items.append(("GCFs", "/run/{}".format(last_run_id)))
    nav_items.append(("BGCs", "/dataset/0"))

    nav_items.append(("Query", "/query"))
    nav_items.append(("Statistics", "/stats"))
    nav_items.append(("Help", "/help"))
    nav_items.append(("Feedback", "/feedback"))
    nav_items.append(("About", "/about"))

    return dict(
        g=g,
        nav_items=nav_items,
        last_run_id=last_run_id
    )
