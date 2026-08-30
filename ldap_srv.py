import io
import logging
import socket
import sys
from typing import Literal, Optional

import pydantic
from ldaptor.inmemory import InMemoryLDIFProtocol, ReadOnlyInMemoryLDAPEntry
from ldaptor.interfaces import IConnectedLDAPEntry
from ldaptor.protocols.ldap import ldaperrors
from ldaptor.protocols.ldap.ldapserver import LDAPServer
from ldaptor.protocols.pureldap import (
    LDAPExtendedResponse,
    LDAPFilter_and,
    LDAPFilter_equalityMatch,
    LDAPFilter_or,
    LDAPFilter_present,
)
from twisted.application import service
from twisted.internet import defer, reactor
from twisted.internet.endpoints import serverFromString
from twisted.internet.protocol import ServerFactory
from twisted.python import log
from twisted.python.components import registerAdapter
from twisted.python.failure import Failure

import database
import settings

logger = logging.getLogger("ldap")


class MixedFilter(pydantic.BaseModel):
    object_type: Optional[Literal["user", "group"]] = None
    query: Optional[bytes] = None
    group_filter: Optional[str] = None


def get_filter_params(
    filterobject: LDAPFilter_equalityMatch | LDAPFilter_present | LDAPFilter_and,
    currentFilter: Optional[MixedFilter] = None,
):
    if currentFilter is None:
        currentFilter = MixedFilter()
    if isinstance(filterobject, LDAPFilter_present):
        return currentFilter
    elif isinstance(filterobject, LDAPFilter_or):
        fo = list(filterobject)
        if len(fo) > 1:
            raise NotImplementedError(
                "Or operation for more than one parameter is not supported."
            )
        currentFilter = get_filter_params(fo[0], currentFilter)
    elif isinstance(filterobject, LDAPFilter_and):
        for subfilter in filterobject:
            currentFilter = get_filter_params(subfilter, currentFilter)
    elif isinstance(filterobject, LDAPFilter_equalityMatch):
        attrdesc = filterobject.attributeDesc.value.lower()
        if attrdesc == b"objectclass":
            if filterobject.assertionValue.value in [b"person", b"inetOrgPerson"]:
                currentFilter.object_type = "user"
            elif filterobject.assertionValue.value in [b"groupOfNames"]:
                currentFilter.object_type = "group"
        elif attrdesc in [b"uid", b"cn"]:
            currentFilter.query = filterobject.assertionValue.value.decode()
            if currentFilter.object_type is None:
                if attrdesc == b"uid":
                    currentFilter.object_type = "user"
                else:
                    currentFilter.object_type = "group"
        elif attrdesc == b"memberof":
            currentFilter.group_filter = filterobject.assertionValue.value.decode()
        else:
            raise NotImplementedError(f"I dont speak attributeDesc {attrdesc}")
    else:
        raise NotImplementedError(f"I dont speak filter {repr(filterobject)}")
    return currentFilter


class FalLDAPEntry(ReadOnlyInMemoryLDAPEntry):
    def __init__(self, dn, *args, **kwargs):
        super().__init__(dn=dn, *args, **kwargs)

    def lookup(self, dn):
        return defer.succeed(FalLDAPEntry(dn=dn))

    def bind(self, password):
        if database.auth_user(self.dn, password):
            return defer.succeed(self)
        return defer.fail(ldaperrors.LDAPInvalidCredentials())

    def search(
        self, filterText=None, filterObject=None, attributes=(), callback=None, **kwargs
    ):
        assert callback is not None
        desired_filter = get_filter_params(filterObject)
        if desired_filter.object_type == "user":
            if desired_filter.query is None:
                database.users.get_all_ldap(
                    callback, attributes, desired_filter.group_filter
                )
            else:
                record = database.users.get_record_by_uid(desired_filter.query)
                if record is None:
                    logger.info("Failed to find %s", desired_filter)
                    return defer.succeed(None)
                # shut up the linter
                _, groups = database.groups.list_records(
                    0, -1
                )  # pyright: ignore[reportAssignmentType]
                groups: list[database.ScimLDAPGroup]
                record = record.get_ldap_ldif(attributes, groups)
                callback(record)
        elif desired_filter.object_type == "group":
            if desired_filter.query is None:
                database.groups.get_all_ldap(
                    callback, attributes, desired_filter.group_filter
                )
            else:
                record = database.groups.get_record_by_uid(desired_filter.query)
                if record is None:
                    return defer.succeed(None)
                assert isinstance(record, database.ScimLDAPGroup)
                callback(record.get_ldap_ldif(attributes))
        if desired_filter.object_type is None:
            database.users.get_all_ldap(
                callback, attributes, desired_filter.group_filter
            )
            database.groups.get_all_ldap(
                callback, attributes, desired_filter.group_filter
            )

        return defer.succeed(None)


class LDAPServerLogged(LDAPServer):
    dn = "unbound"

    def handle_LDAPSearchRequest(self, request, controls, reply):
        res: defer.Deferred = super().handle_LDAPSearchRequest(request, controls, reply)
        logger.info(
            "%s searched for %s",
            self.dn,
            repr(request.filter),
        )
        return res

    def handle_LDAPBindRequest(self, request, controls, reply):
        res: defer.Deferred = super().handle_LDAPBindRequest(request, controls, reply)
        login_failed = isinstance(res.result, Failure)
        peer = self.transport.getPeer()
        logger.info(
            "Bind from %s as %s result: %s",
            peer.host,
            request.dn,
            "failed" if login_failed else "logged in OK",
        )
        if not login_failed:
            self.dn = request.dn
        return res

    def handle_LDAPExtendedRequest(self, request, controls, reply):
        # i wanted to try extendedRequest_ but writing that will make me go insane
        if request.requestName == b"1.3.6.1.4.1.4203.1.11.3":
            if self.dn is None:
                return defer.fail(ldaperrors.LDAPInvalidCredentials())
            uid = self.dn.decode("utf-8").split(",")[0].split("=")[1]
            record: database.ScimLDAPUser = database.users.get_record_by_uid(
                uid
            )  # pyright: ignore[reportAssignmentType]
            if record is None:
                return defer.fail(ldaperrors.LDAPInvalidCredentials())
            ldap_record = record.get_ldap_ldif(
                [], database.groups.list_records(0, -1)[1]
            )
            logger.info("%s asked for whoami", self.dn)
            return defer.succeed(
                LDAPExtendedResponse(
                    ldaperrors.Success.resultCode, response=ldap_record
                )
            )
        return super().handle_LDAPExtendedRequest(request, controls, reply)


class LDAPServerFactory(ServerFactory):
    protocol = LDAPServerLogged

    def __init__(self, root):
        self.root = root


def setup_reactor():
    root = FalLDAPEntry(
        dn=settings.BASE_DN,
    )
    factory = LDAPServerFactory(root)
    registerAdapter(
        lambda factory: factory.root, LDAPServerFactory, IConnectedLDAPEntry
    )
    reactor.listenTCP(settings.LDAP_PORT, factory)
