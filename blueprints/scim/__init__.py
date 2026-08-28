from flask import Blueprint, abort, request, url_for

import settings
from blueprints.scim import groups_bp, users_bp

# -- setup-start --
bp = Blueprint("scim", __name__, url_prefix="/scim")


@bp.before_request
def validate_scim_token():
    header = request.headers.get("Authorization", "").split(" ")
    if len(header) < 2:
        raise abort(401, "invalid token header")
    token = header[1]
    if token != settings.SCIM_TOKEN:
        raise abort(401, "invalid token")


@bp.after_request
def set_scim_content_type(response):
    """Expose every endpoint with the SCIM media type."""
    response.headers["Content-Type"] = "application/scim+json"
    return response


bp.register_blueprint(users_bp.bp)
bp.register_blueprint(groups_bp.bp)
