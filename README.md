# FalLDAP

A fallback-crutch to make your stubborn LDAP-only apps to work with OIDC server.

## Requirements

OIDC provider that support [SCIM](https://scim.cloud/) - because the FalLDAP provides actual data back to its users and service accounts, I decided to prefer being in sync with identity server.

Right now FalLDAP is tested only on [Pocket ID](https://pocket-id.org/).

## Setup

OIDC:

- [Pocket ID](docs/sso/pocket_id.md)

Clients:

- [Jellyfin](docs/client/jellyfin.md)

## Maybe-to-dos?

- Perhaps move away from redis, so there will be no need for extra service? But I hate doing proper databases, and SCIM can contain a lot of wacky data, which, can get changed if provider sees it being out of spec, resulting in loop, so I just throw the entire SCIM model into database, only using it in otp endpoints.
- Push login? E.g., type in any password - a popup shows on FalLDAP, user allows/denies it and bind succeeds/fails.
- Move away from ldaptor. Twisted, together with ldaptor got to be the worst libraries I ever used in my life.

## Why not just spin up LDAP?

I spun up Pocket ID. I dont want to use permanent passwords or make me and my friends enter `password;otpcode` for auth, hence, this.
