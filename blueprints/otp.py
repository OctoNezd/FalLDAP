import secrets

import bcrypt
from flask import Blueprint, render_template, session

import database
import ext
import settings

bp = Blueprint("otp", __name__, url_prefix="/otp")


@ext.oidc.require_login
@bp.get("/")
def index():
    ext_uid = session["oidc_auth_profile"]["sub"]
    scim_user: database.ScimLDAPUser = database.users.get_record_by_extid(
        ext_uid
    )  # pyright: ignore[reportAssignmentType]
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
        "otp.html.j2",
        code=temp_pwd,
        remaining_time=settings.PASSWORD_LIFE,
        username=scim_user.user_name,
    )
