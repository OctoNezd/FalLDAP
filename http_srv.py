import secrets
from functools import wraps

import bcrypt
from flask import Flask, abort, jsonify, render_template, request, session, url_for
from flask_oidc import OpenIDConnect

import database
import settings
from blueprints import scim

app = Flask(__name__)
app.secret_key = settings.SESSION_SECRET
app.config["OIDC_CLIENT_SECRETS"] = "./client_secrets.json"
oidc = OpenIDConnect(app)
app.register_blueprint(scim.bp)


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
@oidc.require_login
def index():
    ext_uid = session["oidc_auth_profile"]["sub"]
    scim_user: database.ScimLDAPUser = database.users.get_record_by_extid(ext_uid)
    if scim_user is None:
        raise abort(
            404,
            "Sorry, your account hasnt been reported by SSO service yet - wait a bit. Contact your admin if this issue persists.",
        )
    temp_pwd = secrets.token_urlsafe(settings.PASSWORD_LENGTH)
    db_key = f"temppwd:{scim_user.id}"
    database.vk.set(db_key, bcrypt.hashpw(temp_pwd.encode(), bcrypt.gensalt()))
    database.vk.expire(db_key, settings.PASSWORD_LIFE)
    return render_template(
        "index.html.j2",
        code=temp_pwd,
        remaining_time=settings.PASSWORD_LIFE,
        username=scim_user.user_name,
    )
