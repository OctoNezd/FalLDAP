import logging
import socketserver
from typing import Literal, Optional

import ldapserver
import pydantic

import database
import ext
import settings

logger = logging.getLogger("falldap-ldap")


class MixedFilter(pydantic.BaseModel):
    object_type: Optional[Literal["user", "group"]] = None
    query: Optional[str] = None
    group_filter: Optional[str] = None


def get_filter_params(
    filterobject: (
        ldapserver.ldap.FilterEqual
        | ldapserver.ldap.FilterPresent
        | ldapserver.ldap.FilterAnd
        | ldapserver.ldap.FilterOr
        | ldapserver.ldap.Filter
    ),
    currentFilter: Optional[MixedFilter] = None,
):
    if currentFilter is None:
        currentFilter = MixedFilter()
    if isinstance(filterobject, ldapserver.ldap.FilterPresent):
        return currentFilter
    elif isinstance(filterobject, ldapserver.ldap.FilterOr):
        if len(filterobject.filters) > 1:
            raise NotImplementedError(
                "Or operation for more than one parameter is not supported."
            )
        currentFilter = get_filter_params(filterobject.filters[0], currentFilter)
    elif isinstance(filterobject, ldapserver.ldap.FilterAnd):
        for subfilter in filterobject.filters:
            currentFilter = get_filter_params(subfilter, currentFilter)
    elif isinstance(filterobject, ldapserver.ldap.FilterEqual):
        attrdesc = filterobject.attribute.lower()
        valdesc = filterobject.value.decode()
        if attrdesc == "objectclass":
            if valdesc in ["person", "inetOrgPerson"]:
                currentFilter.object_type = "user"
            elif valdesc in ["groupOfNames"]:
                currentFilter.object_type = "group"
        elif attrdesc in ["uid", "cn"]:
            currentFilter.query = valdesc
            if currentFilter.object_type is None:
                if attrdesc == "uid":
                    currentFilter.object_type = "user"
                else:
                    currentFilter.object_type = "group"
        elif attrdesc == "memberof":
            currentFilter.group_filter = valdesc
        else:
            raise NotImplementedError(f"I dont speak attributeDesc {attrdesc}")
    else:
        raise NotImplementedError(f"I dont speak filter {repr(filterobject)}")
    return currentFilter


class FalLDAP(ldapserver.LDAPRequestHandler):
    bound_dn = None
    subschema = ext.subschema
    supports_whoami = True
    supports_sasl_anonymous = False
    supports_paged_results = False
    supports_password_modify = False
    supports_sasl_external = False

    def do_bind_simple_authenticated(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, dn, password
    ) -> bool:
        if database.auth_user(dn, password):
            self.bound_dn = dn
            return True
        raise ldapserver.exceptions.LDAPInvalidCredentials()

    def do_bind_sasl_plain(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, identity, password, authzid=None
    ):
        if authzid is not None and identity != authzid:
            raise ldapserver.exceptions.LDAPInvalidCredentials()
        if database.auth_user(identity, password):
            self.bound_dn = identity
            return True
        raise ldapserver.exceptions.LDAPInvalidCredentials()

    def do_search(self, baseobj, scope, filterobj):
        if self.bound_dn is None:
            raise ldapserver.exceptions.LDAPInsufficientAccessRights(
                "Binding is required"
            )
        if settings.LOG_SEARCHES:
            logger.info("%s searches for %s", self.bound_dn, filterobj)
        desired_filter = get_filter_params(filterobj)
        yield from self.do_search_user(desired_filter)
        yield from self.do_search_group(desired_filter)

    def do_search_user(self, desired_filter: MixedFilter):
        if desired_filter.object_type in ["user", None]:
            if desired_filter.query is None:
                for user in database.users.get_all_ldap(
                    schema=self.subschema, group=desired_filter.group_filter
                ):
                    yield user
            else:
                record: database.ScimLDAPUser = database.users.get_record_by_uid(
                    desired_filter.query
                )  # pyright: ignore[reportAssignmentType]
                if record is not None:
                    # shut up the linter
                    _, groups = database.groups.list_records(
                        0, -1
                    )  # pyright: ignore[reportAssignmentType]
                    groups: list[database.ScimLDAPGroup]
                    yield record.get_ldap_ldif(
                        groups=groups,
                        schema=self.subschema,
                    )

    def do_search_group(self, desired_filter: MixedFilter):
        if desired_filter.object_type in ["group", None]:
            if desired_filter.query is None:
                yield from database.groups.get_all_ldap(
                    group=desired_filter.group_filter, schema=self.subschema
                )
            else:
                record = database.groups.get_record_by_uid(desired_filter.query)
                if record is not None:
                    assert isinstance(record, database.ScimLDAPGroup)
                    yield record.get_ldap_ldif(schema=self.subschema)

    def do_whoami(self):
        return self.bound_dn


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    socketserver.ThreadingTCPServer(
        (settings.LDAP_HOST, settings.LDAP_PORT), FalLDAP
    ).serve_forever()
