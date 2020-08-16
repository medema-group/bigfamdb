#!/usr/bin/env python3

from flask import Flask, redirect, url_for
from os import path
import sqlite3
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
from sys import argv

# import global config
from app.config import conf

# import controllers
from app.controllers import root, api, home, dataset, run
from app.controllers import bgc, gcf, query, stats
from app.controllers import about, help_me, feedback


def bigfam():

    # check databases
    jobs_db = conf["jobs_db_path"]
    if not path.exists(jobs_db):
        print("creating jobs db ({})...".format(jobs_db))
        with sqlite3.connect(jobs_db) as con:
            cur = con.cursor()
            schema_sql = path.join(
                path.dirname(__file__),
                "..",
                "query_processor",
                "jobs_schema.sql"
            )
            with open(schema_sql, "r") as sql_script:
                cur.executescript(sql_script.read())
                con.commit()

    # initiate app
    app = Flask(
        __name__,
        template_folder=path.join(path.dirname(
            path.realpath(__file__)), "app", "views"),
        static_folder=path.join(path.dirname(
            path.realpath(__file__)), "app", "static")
    )

    # register controllers
    app.register_blueprint(root.blueprint)
    app.register_blueprint(api.blueprint)
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
        nav_items.append(("Home", url_for("home.page_home")))

        with sqlite3.connect(conf["db_path"]) as con:
            cur = con.cursor()
            last_run_id = cur.execute((
                "select id"
                " from run"
                " where status >= 7"
                " order by id desc"
                " limit 1"
            )).fetchall()[0][0]

        nav_items.append(("GCFs", url_for(
            "run.page_run", run_id=last_run_id
        )))
        nav_items.append(("BGCs", url_for(
            "dataset.page_dataset", dataset_id=0
        )))

        nav_items.append(("Query", url_for("query.page_query")))
        nav_items.append(("Statistics", url_for("stats.page_stats")))
        nav_items.append(("Help", url_for("help_me.page_help")))
        nav_items.append(("Feedback", url_for("feedback.page_feedback")))
        nav_items.append(("About", url_for("about.page_about")))

        return dict(
            g=g,
            nav_items=nav_items,
            last_run_id=last_run_id
        )

    return app


if __name__ == "__main__":

    if len(argv) > 1:
        port = int(argv[1])
    else:
        port = 5000

    if len(argv) > 2:
        def create_dummy_app(actual_subfolder):
            app = Flask(__name__)

            @ app.route("/")
            def dummy():
                return redirect("/" + actual_subfolder)
            return app

        bigfamdb_app = DispatcherMiddleware(
            create_dummy_app(argv[2]), {
                "/" + argv[2]: bigfam()
            })
    else:
        bigfamdb_app = bigfam()

    run_simple(
        hostname="0.0.0.0",
        port=port,
        application=bigfamdb_app
    )
