from http import HTTPStatus

from flask import Blueprint, abort, request, url_for
from pydantic import ValidationError
from scim2_models import (
    Context,
    Error,
    Group,
    ListResponse,
    PatchOp,
    ResponseParameters,
    SCIMException,
    SearchRequest,
)
from werkzeug.exceptions import HTTPException, PreconditionFailed
from werkzeug.routing import BaseConverter
from werkzeug.routing import ValidationError as RoutingValidationError

from database import groups

bp = Blueprint("scim_groups", __name__, url_prefix="/Groups")


def resource_location(app_record):
    """Return the canonical URL for a group record."""
    return url_for("scim.scim_groups.get_group", app_record=app_record, _external=True)


# -- setup-end --


# -- etag-start --
@bp.after_request
def set_etag_header(response):
    """Extract ``ETag`` from ``meta.version`` and handle conditional responses."""
    data = response.get_json(silent=True)
    if meta := (data or {}).get("meta"):
        if version := meta.get("version"):
            response.headers["ETag"] = version
    response.make_conditional(request)
    return response


@bp.before_request
def check_etag():
    """Verify ``If-Match`` on write operations.

    :raises ~werkzeug.exceptions.PreconditionFailed: If the header is present and does not match.
    """
    if request.method not in ("PUT", "PATCH", "DELETE"):
        return
    app_record = request.view_args.get("app_record")
    if app_record is None:
        return
    if_match = request.headers.get("If-Match")
    if not if_match:
        return
    if if_match.strip() == "*":
        return
    etag = groups.make_etag(app_record)
    tags = [t.strip() for t in if_match.split(",")]
    if etag not in tags:
        raise PreconditionFailed("ETag mismatch")


# -- etag-end --


# -- refinements-start --
# -- converters-start --
class GroupConverter(BaseConverter):
    """Resolve a group identifier to an application record."""

    def to_python(self, id):
        try:
            return groups.get_record(id)
        except KeyError:
            raise RoutingValidationError()

    def to_url(self, record):
        return record["id"]


@bp.record_once
def _register_converter(state):
    state.app.url_map.converters["group"] = GroupConverter


# -- converters-end --


# -- error-handlers-start --
@bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Turn Pydantic validation errors into SCIM error responses."""
    scim_error = Error.from_validation_error(error.errors()[0])
    return scim_error.model_dump(), scim_error.status


@bp.errorhandler(HTTPException)
def handle_http_error(error):
    """Turn HTTP errors into SCIM error responses."""
    scim_error = Error(status=error.code, detail=str(error.description))
    return scim_error.model_dump(), error.code


@bp.errorhandler(SCIMException)
def handle_scim_error(error):
    """Turn SCIM exceptions into SCIM error responses."""
    scim_error = error.to_error()
    return scim_error.model_dump(), scim_error.status


# -- error-handlers-end --
# -- refinements-end --


# -- endpoints-start --
# -- single-resource-start --
# -- get-group-start --
@bp.get("<group:app_record>")
def get_group(app_record):
    """Return one SCIM group."""
    req = ResponseParameters.model_validate(request.args.to_dict())
    scim_group = groups.to_scim(app_record, resource_location(app_record))
    return scim_group.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=req.attributes,
        excluded_attributes=req.excluded_attributes,
    )


# -- get-group-end --


# -- patch-group-start --
@bp.patch("<group:app_record>")
def patch_group(app_record):
    """Apply a SCIM PatchOp to an existing group."""
    req = ResponseParameters.model_validate(request.args.to_dict())
    scim_group = groups.to_scim(app_record, resource_location(app_record))
    patch = PatchOp[Group].model_validate(
        request.get_json(),
        scim_ctx=Context.RESOURCE_PATCH_REQUEST,
    )
    patch.patch(scim_group)

    updated_record = groups.from_scim(scim_group)
    groups.save_record(updated_record)

    return scim_group.model_dump(
        scim_ctx=Context.RESOURCE_PATCH_RESPONSE,
        attributes=req.attributes,
        excluded_attributes=req.excluded_attributes,
    )


# -- patch-group-end --


# -- put-group-start --
@bp.put("<group:app_record>")
def replace_group(app_record):
    """Replace an existing group with a full SCIM resource."""
    req = ResponseParameters.model_validate(request.args.to_dict())
    existing_group = groups.to_scim(app_record, resource_location(app_record))
    replacement = Group.model_validate(
        request.get_json(),
        scim_ctx=Context.RESOURCE_REPLACEMENT_REQUEST,
    )
    replacement.replace(existing_group)

    updated_record = groups.from_scim(replacement)
    groups.save_record(updated_record)

    response_group = groups.to_scim(updated_record, resource_location(updated_record))
    return response_group.model_dump(
        scim_ctx=Context.RESOURCE_REPLACEMENT_RESPONSE,
        attributes=req.attributes,
        excluded_attributes=req.excluded_attributes,
    )


# -- put-group-end --


# -- delete-group-start --
@bp.delete("<group:app_record>")
def delete_group(app_record):
    """Delete an existing group."""
    groups.delete_record(app_record["id"])
    return "", HTTPStatus.NO_CONTENT


# -- delete-group-end --
# -- single-resource-end --


# -- collection-start --
# -- list-groups-start --x
@bp.get("")
def list_groups():
    """Return one page of groups as a SCIM ListResponse."""
    req = SearchRequest.model_validate(request.args.to_dict())
    total, page = groups.list_records(req.start_index_0, req.stop_index_0)
    resources = [groups.to_scim(record, resource_location(record)) for record in page]
    response = ListResponse[Group](
        total_results=total,
        start_index=req.start_index or 1,
        items_per_page=len(resources),
        resources=resources,
    )
    return response.model_dump(
        scim_ctx=Context.RESOURCE_QUERY_RESPONSE,
        attributes=req.attributes,
        excluded_attributes=req.excluded_attributes,
    )


# -- list-groups-end --


# -- create-group-start --
@bp.post("")
def create_group():
    """Validate a SCIM creation payload and store the new group."""
    req = ResponseParameters.model_validate(request.args.to_dict())
    request_group = Group.model_validate(
        request.get_json(),
        scim_ctx=Context.RESOURCE_CREATION_REQUEST,
    )
    app_record = groups.from_scim(request_group)
    groups.save_record(app_record)
    print(app_record)
    response_group = groups.to_scim(app_record, resource_location(app_record))
    return (
        response_group.model_dump(
            scim_ctx=Context.RESOURCE_CREATION_RESPONSE,
            attributes=req.attributes,
            excluded_attributes=req.excluded_attributes,
        ),
        HTTPStatus.CREATED,
    )


# -- create-group-end --
# -- collection-end --
