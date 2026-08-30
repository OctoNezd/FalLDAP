from flask import Flask
from flask_oidc import OpenIDConnect
from ldapserver import SubschemaSubentry
from ldapserver.schema import RFC2307BIS_SCHEMA, RFC2798_SCHEMA

oidc = OpenIDConnect()
CUSTOM_SCHEMA = (RFC2307BIS_SCHEMA | RFC2798_SCHEMA).extend(
    attribute_type_definitions=[
        # pylint: disable=line-too-long
        "( 1.2.840.113556.1.2.102 NAME 'memberOf' DESC 'Group that the entry belongs to' EQUALITY distinguishedNameMatch SYNTAX 1.3.6.1.4.1.1466.115.121.1.12 )"
    ]
)
subschema = SubschemaSubentry(CUSTOM_SCHEMA, "cn=Subschema")
