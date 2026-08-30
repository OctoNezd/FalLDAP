import datetime
import hashlib
import uuid
from logging import getLogger

import bcrypt
import ldapserver
import scim2_models
import valkey
from flask import abort

import settings

vk = valkey.Valkey.from_url(settings.VALKEY_URL, decode_responses=True)
logger = getLogger("database")
USER_SET_ID = "users"
GROUP_SET_ID = "groups"
BINDABLES_SET_ID = "bindables"


class ScimLDAPGroup(scim2_models.Group):
    def get_ldap_ldif(
        self, schema: ldapserver.SubschemaSubentry
    ) -> ldapserver.ObjectEntry:
        attrs = {
            "objectClass": ["top", "groupOfNames"],
            "cn": [self.display_name],
            "member": [],
        }
        if self.members:
            for member in self.members:
                scimuser: ScimLDAPUser = users.get_record(
                    member.value
                )  # pyright: ignore[reportAssignmentType]
                attrs["member"].append(
                    schema.DN.from_str(f"uid={scimuser.user_name},{settings.BASE_DN}")
                )

        return schema.ObjectEntry(
            dn=f"cn={self.display_name},{settings.GROUP_DN}", **attrs
        )


class ScimLDAPUser(scim2_models.User):
    def get_ldap_ldif(
        self, groups: list[ScimLDAPGroup], schema: ldapserver.SubschemaSubentry
    ) -> ldapserver.ObjectEntry:
        cn = self.display_name or self.user_name
        attrs = {
            "objectClass": ["top", "person", "inetOrgPerson"],
            "uid": [self.user_name],
            "cn": [cn],
        }
        if self.display_name:
            attrs["displayName"] = [self.display_name]
        if self.name:
            if self.name.given_name:
                attrs["givenName"] = [self.name.given_name]
            if self.name.family_name:
                attrs["sn"] = [self.name.family_name]
        if self.emails and len(self.emails) > 0:
            attrs["mail"] = []
            for mail in self.emails:
                attrs["mail"].append(mail.value)
        attrs["memberOf"] = []
        for group in groups:
            if group.members:
                for member in group.members:
                    if member.value == self.id:
                        attrs["memberOf"].append(
                            schema.DN.from_str(
                                f"cn={group.display_name},{settings.GROUP_DN}"
                            )
                        )
        return schema.ObjectEntry(
            dn=f"uid={self.user_name},{settings.USER_DN}", **attrs
        )


class ScimRecordManager:
    def __init__(self, set_id, record_class: ScimLDAPUser | ScimLDAPGroup) -> None:
        self.set_id = set_id
        self.record_class = record_class

    def delete_record(self, record_id):
        scimuser = self.get_record(record_id)
        vk.zrem(self.set_id, record_id)
        uidkey = getattr(scimuser, "user_name", scimuser.display_name)
        vk.delete(
            f"uid{self.set_id}:{uidkey}",
            f"{self.set_id}:{record_id}",
            f"extuid{self.set_id}:{scimuser.external_id}",
        )

    def from_scim(
        self, item: ScimLDAPUser | ScimLDAPGroup
    ) -> ScimLDAPUser | ScimLDAPGroup:
        if not item.id:
            item.id = str(uuid.uuid4())
        if not item.meta:
            item.meta = scim2_models.Meta()
        return item

    def get_record(self, id):
        item_vk: str = vk.get(f"{self.set_id}:{id}")  # type: ignore
        if item_vk is None:
            raise abort(404)
        return self.record_class.model_validate_json(item_vk)

    def get_all_ldap(self, schema: ldapserver.SubschemaSubentry, group=None):
        if group is not None:
            group = schema.DN.from_str(group)
        if self.record_class == ScimLDAPUser:
            _, grouplist = groups.list_records(
                0, -1
            )  # pyright: ignore[reportAssignmentType]
            grouplist: list[ScimLDAPGroup]
        elif group is not None:
            # no nested groups in SCIM afaik
            return
        _, users = self.list_records(0, -1)
        users: list[self.record_class]
        for item in users:
            if self.record_class == ScimLDAPUser:
                item = item.get_ldap_ldif(
                    groups=grouplist, schema=schema
                )  # pyright: ignore[reportPossiblyUnboundVariable]
                if group is not None:
                    if group not in item["memberOf"]:
                        continue
                yield item
            elif self.record_class == ScimLDAPGroup:
                yield item.get_ldap_ldif(schema=schema)

    def get_record_by_uid(self, uid) -> ScimLDAPUser | ScimLDAPGroup | None:
        record_id = vk.get(f"uid{self.set_id}:{uid}")
        if record_id is None:
            return None
        return self.get_record(record_id)

    def get_record_by_extid(self, uid) -> ScimLDAPUser | ScimLDAPGroup | None:
        record_id = vk.get(f"extuid{self.set_id}:{uid}")
        if record_id is None:
            return None
        return self.get_record(record_id)

    def list_records(
        self, start: int, stop: int
    ) -> tuple[int, list[ScimLDAPUser | ScimLDAPGroup]]:
        items = []
        total: int = vk.zcount(self.set_id, 0, 0)  # type: ignore
        item_keys: list[str] = vk.zrange(self.set_id, start, stop)  # type: ignore
        for item in item_keys:
            item_vk: str = vk.get(f"{self.set_id}:{item}")  # type: ignore
            if item_vk is None:
                continue
            items.append(self.record_class.model_validate_json(item_vk))
        return total, items

    def make_etag(self, record: ScimLDAPUser | ScimLDAPGroup):
        return hashlib.sha512(
            record.model_dump_json(exclude_none=True).encode("utf-8")
        ).hexdigest()

    def save_record(self, record: ScimLDAPUser | ScimLDAPGroup):
        vk.zadd(self.set_id, {record.id: 0})  # type: ignore
        assert record.meta is not None
        record.meta.last_modified = datetime.datetime.now()
        record.meta.last_modified = record.meta.last_modified.replace(
            tzinfo=datetime.UTC, microsecond=0
        )
        vk.set(f"{self.set_id}:{record.id}", record.model_dump_json(exclude_none=True))
        uidkey = getattr(record, "user_name", record.display_name)
        vk.set(f"uid{self.set_id}:{uidkey}", record.id)
        vk.set(f"extuid{self.set_id}:{record.external_id}", record.id)

    def to_scim(self, item: ScimLDAPUser | ScimLDAPGroup | str, location: str):
        if isinstance(item, str):
            item = self.record_class.model_validate_json(item)
        assert item.meta is not None
        item.meta.location = location
        return item


def auth_user(user: str, password):
    parent_dn = user.split(",", 1)[1]
    uid = user.split(",")[0].split("=", 1)[1]
    if parent_dn == settings.SERVICE_DN:
        crypted = bindables.get_pw(uid)
    elif parent_dn == settings.USER_DN:
        user_scim = users.get_record_by_uid(uid)
        if user_scim is None:
            return False
        crypted = vk.get(f"temppwd:{user_scim.id}")
    else:
        logger.error("Invalid DN specified: %s (parent: %s)", user.getText(), parent_dn)
        return False
    if crypted is None:
        logger.info("Rejecting invalid uid %s in dn %s", uid, parent_dn)
        return False
    res = bcrypt.checkpw(password, crypted.encode("utf-8"))
    if res and settings.LOG_ALL_LOGINS:
        logger.info("%s logged in", user)
    elif settings.LOG_ALL_LOGINS or settings.LOG_INVALID_LOGINS:
        logger.info("%s failed to log in", user)
    return res


class BindablesManager:
    def list(self) -> list[str]:
        members = []
        for member in vk.smembers(BINDABLES_SET_ID):
            # clean out invalid members
            if not self.exists(member):
                vk.srem(BINDABLES_SET_ID, member)
            else:
                members.append(member)
        return members

    def delete(self, name):
        vk.delete(f"{BINDABLES_SET_ID}:{name}")
        vk.srem(BINDABLES_SET_ID, name)

    def create(self, name, password):
        vk.sadd(BINDABLES_SET_ID, name)
        vk.set(
            f"{BINDABLES_SET_ID}:{name}",
            bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
        )

    def exists(self, name):
        return vk.sismember(BINDABLES_SET_ID, name) and vk.exists(
            f"{BINDABLES_SET_ID}:{name}"
        )

    def get_pw(self, name):
        if self.exists(name):
            return vk.get(f"{BINDABLES_SET_ID}:{name}")
        return None


users = ScimRecordManager(USER_SET_ID, ScimLDAPUser)  # type: ignore
groups = ScimRecordManager(GROUP_SET_ID, ScimLDAPGroup)  # type: ignore
bindables = BindablesManager()
