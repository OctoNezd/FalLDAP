# .env setup

Basic .env configuration:

```shell
HTTP_PORT=8080
LDAP_PORT=8389
SCIM_TOKEN=GENERATE_TOKEN_USING_GUIDE_BELOW
VALKEY_URL=valkey://falldap-valkey
BASE_DN=dc=falldap,dc=loc
PASSWORD_LIFE=15
PASSWORD_LENGTH=16
FLASK_OIDC_SCOPES=openid email groups
FLASK_OIDC_CLIENT_SECRETS=./client_secrets.json
```

- `HTTP_PORT` and `LDAP_PORT` - the ports that which your FalLDAP instance will be available at
- `SCIM_TOKEN` is used to verify that server connecting to FalLDAP is your identity provider. Generate it using [this guide](#Generating secrets)
- `VALKEY_URL` is URL pointing to your valkey server. If you are using compose example - keep it set to default.
- `BASE_DN` is distinguished name for root of your LDAP "domain". You can keep it as is.
- `PASSWORD_LIFE` - how long one time password is active for
- `PASSWORD_LENGTH` - length of one time password
- `FLASK_OIDC_SCOPES` - OIDC scopes
- `FLASK_OIDC_CLIENT_SECRETS` - path to file with OIDC client configuration

## Generating secrets

Run `python3 -c "import secrets;print(secrets.token_urlsafe(64))"` and use its output as a secret.

## Optional variables

- `ADMIN_GROUP` - group that can access admin panel for creating service accounts for other apps, `admin` by default
- `GROUP_KEY` - group key in what your OIDC server gives to the web app
- `USER_DN` - base DN for your user accounts. Default one is `cn=users,cn=accounts,YOUR_BASE_DN`
- `GROUP_DN` - same but for groups. Default one is `cn=groups,cn=accounts,YOUR_BASE_DN`
- `SERVICE_DN` - same but for service accounts. Default one is `cn=sysaccounts,cn=etc,YOUR_BASE_DN`
- `LOG_ALL_LOGINS` - logs all logins into your LDAP server
- `LOG_INVALID_LOGINS` - logs invalid logins (wrong password, user doesnt exist, invalid DN specified)
- `LOG_SEARCHES` - logs LDAP searches
- `SESSION_SECRET` - secret for HTTP server session. Random on every restart by default, set it to make webapp session persist, useful for development.
