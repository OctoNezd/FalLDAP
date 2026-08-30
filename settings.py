import json
import os
import secrets

import dotenv

dotenv.load_dotenv(".env.dev")

HTTP_PORT = int(os.environ["HTTP_PORT"])
LDAP_PORT = int(os.environ["LDAP_PORT"])
SCIM_TOKEN = os.environ["SCIM_TOKEN"]
VALKEY_URL = os.environ["VALKEY_URL"]
BASE_DN = os.environ["BASE_DN"]
USER_DN = os.environ.get("USER_DN", "cn=users,cn=accounts," + BASE_DN)
GROUP_DN = os.environ.get("GROUP_DN", "cn=groups,cn=accounts," + BASE_DN)
SERVICE_DN = os.environ.get("SERVICE_DN", "cn=sysaccounts,cn=etc," + BASE_DN)
PASSWORD_LIFE = int(os.environ["PASSWORD_LIFE"])
PASSWORD_LENGTH = int(os.environ["PASSWORD_LENGTH"])
LOG_ALL_LOGINS = bool(os.environ.get("LOG_ALL_LOGINS", ""))
LOG_INVALID_LOGINS = bool(os.environ.get("LOG_INVALID_LOGINS", "yes"))
LOG_SEARCHES = bool(os.environ.get("LOG_SEARCHES", ""))
SESSION_SECRET = os.environ.get("SESSION_SECRET", secrets.token_bytes(64))
ADMIN_GROUP = os.environ.get("ADMIN_GROUP", "admin")
GROUP_KEY = os.environ.get("GROUP_KEY", "groups")
BINDABLE_PW_LENGTH = int(os.environ.get("BINDABLE_PW_LENGTH", 24))
