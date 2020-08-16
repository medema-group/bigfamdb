#!/usr/bin/env python3

import sqlite3
import json
from flask import request
from flask import abort

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('api', __name__)


@blueprint.route("/api/autocomplete_taxon/")
def get_taxons():
    keyword = request.args.get('q', type=str, default="")

    if len(keyword) >= 4:
        with sqlite3.connect(conf["db_path"]) as con:
            cur = con.cursor()

            result = []

            for tax_id, tax_level, tax_name in cur.execute((
                "select taxon.id, taxon_class.name, taxon.name"
                " from taxon, taxon_class"
                " where taxon_class.level=taxon.level"
                " and taxon.name like ?"
                " order by taxon.level,taxon.name asc"
            ), (keyword + "%", )).fetchall():
                result.append({
                    "id": tax_id,
                    "name": "{} ({})".format(tax_name, tax_level)
                })
        return json.dumps(result)
    else:
        return abort(403)
