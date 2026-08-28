import logging
import sys

from ldaptor.inmemory import fromLDIFFile
from ldaptor.interfaces import IConnectedLDAPEntry
from ldaptor.protocols.ldap.ldapserver import LDAPServer
from twisted.application import service
from twisted.internet import reactor
from twisted.internet.endpoints import serverFromString
from twisted.internet.protocol import ServerFactory
from twisted.logger import STDLibLogObserver, globalLogBeginner
from twisted.python import log
from twisted.python.components import registerAdapter
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

import ldap_srv
import settings
from http_srv import app

logging.basicConfig(level=logging.DEBUG)
# log.startLogging(sys.stdout)
# observer = log.PythonLoggingObserver()
# observer.start()
observer = STDLibLogObserver()
globalLogBeginner.beginLoggingTo([observer])


# web
flask_resource = WSGIResource(reactor, reactor.getThreadPool(), app)
site = Site(flask_resource)
reactor.listenTCP(settings.HTTP_PORT, site)

# ldap
ldap_srv.setup_reactor()

reactor.run()
