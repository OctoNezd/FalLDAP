import secrets
from http import HTTPStatus
from logging import getLogger

from flask import Blueprint, abort, render_template, request, session

import database
import settings
from ext import oidc

logger = getLogger("admin")
bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@oidc.require_login
def require_admin_group():
    if settings.ADMIN_GROUP not in session["oidc_auth_profile"].get(
        settings.GROUP_KEY, []
    ):
        raise abort(
            HTTPStatus.FORBIDDEN, "You dont have the required group to manage clients."
        )
    session["username"] = database.users.get_record_by_extid(
        session["oidc_auth_profile"]["sub"]
    ).user_name


@bp.delete("delete")
def delete():
    logger.info("user %s deleted %s", session["username"], request.args["name"])
    database.bindables.delete(request.args["name"])
    return render_template(
        "components/accounts.html.j2", clients=database.bindables.list()
    )


@bp.post("create")
def create():
    name = request.form["name"]
    if name is None:
        return (
            render_template("create_err.html.j2", reason="Name form value missing."),
            HTTPStatus.BAD_REQUEST,
        )
    if len(name) == 0:
        return (
            render_template("create_err.html.j2", reason="Name cant be empty."),
            HTTPStatus.BAD_REQUEST,
        )

    if database.bindables.exists(name):
        return (
            render_template(
                "create_err.html.j2",
                reason="There is already bindable client with that name. If you want to reset it, recreate it.",
            ),
            HTTPStatus.CONFLICT,
        )
    pw = secrets.token_urlsafe(settings.BINDABLE_PW_LENGTH)
    database.bindables.create(name, pw)
    logger.info("user %s created %s", session["username"], name)
    return render_template(
        "created_pw.html.j2",
        dn=f"uid={name},{settings.SERVICE_DN}",
        password=pw,
        clients=database.bindables.list(),
    )


@bp.get("panel")
def panel():
    return render_template(
        "admin.html.j2",
        username=session["username"],
        clients=database.bindables.list(),
    )
