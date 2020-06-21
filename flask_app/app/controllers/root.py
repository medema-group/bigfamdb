#!/usr/bin/env python3
from flask import redirect, url_for

# import global config
from ..config import conf

# set blueprint object
from flask import Blueprint
blueprint = Blueprint('root', __name__)


@blueprint.route("/")
def page():
    return redirect(url_for("home.page_home"))
