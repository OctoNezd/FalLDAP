from flask import Flask, jsonify, redirect, url_for

import ext
import settings
from blueprints import admin, otp, scim

app = Flask(__name__)
app.config.from_prefixed_env()
app.secret_key = settings.SESSION_SECRET
ext.oidc.init_app(app)
app.register_blueprint(scim.bp)
app.register_blueprint(otp.bp)
app.register_blueprint(admin.bp)


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


@app.route("/site-map")
def site_map():
    links = []
    for rule in app.url_map.iter_rules():
        # Filter out rules we can't navigate to in a browser
        # and rules that require parameters
        links.append((rule.rule, rule.endpoint, list(rule.methods)))
    # links is now a list of url, endpoint tuples
    return jsonify(links)


@app.route("/")
def index():
    return redirect(url_for("otp.index"), 301)
