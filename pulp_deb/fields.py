from django.db import models


class _DebVer(models.Value):
    def __init__(self, value):
        self.value = value

    def as_sql(self, compiler, connection):
        return "debver(%s)", [self.value]


class DebVersionField(models.CharField):
    description = "Debian Version"

    def db_type(self, connection):
        return "debver"

    def get_prep_value(self, value):
        if value is not None:
            return _DebVer(value)
        return value

    def select_format(self, compiler, sql, params):
        return f"({sql}).value", params
