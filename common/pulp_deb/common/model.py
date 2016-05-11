import time

from mongoengine import DictField, IntField, StringField
from pulp.server.db.model import ContentUnit


class DebPackage(ContentUnit):
    name = StringField(required=True)
    version = StringField(required=True)
    architecture = StringField(required=True)

    _ns = StringField(required=True, default="units_deb")
    _content_type_id = StringField(required=True, default="deb")
    _last_updated = IntField(required=True, default=time.clock())

    _storage_path = StringField()
    file_name = StringField()
    _id = StringField()
    pulp_user_metadata = DictField()

    unit_key_fields = ("name", "version", "architecture")
    meta = {"collection": "units_deb", "database": "pulp_database"}
