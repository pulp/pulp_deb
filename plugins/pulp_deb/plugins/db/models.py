
import mongoengine
from debian import debfile
from debpkgr import debpkg
from pulp.server import util
from pulp.server.controllers import repository as repo_controller
from pulp.server.db.model import FileContentUnit
from pulp_deb.common import ids

NotUniqueError = mongoengine.NotUniqueError


class DebPackage(FileContentUnit):
    TYPE_ID = ids.TYPE_ID_DEB
    meta = dict(collection="units_deb",
                indexes=list(ids.UNIT_KEY_DEB))
    unit_key_fields = ids.UNIT_KEY_DEB

    UNIT_KEY_TO_FIELD_MAP = dict(name="Package",
                                 version="Version",
                                 architecture="Architecture",
                                 installed_size="Installed-Size",
                                 multi_arch="Multi-Arch",
                                 original_maintainer="Original-Maintainer",
                                 )
    name = mongoengine.StringField(required=True)
    version = mongoengine.StringField(required=True)
    architecture = mongoengine.StringField(required=True)
    checksumtype = mongoengine.StringField(required=True)
    checksum = mongoengine.StringField(required=True)
    size = mongoengine.IntField()

    filename = mongoengine.StringField(required=True)
    relativepath = mongoengine.StringField()

    REL_FIELDS = ['breaks', 'conflicts', 'depends', 'enhances', 'pre_depends',
                  'provides', 'recommends', 'replaces', 'suggests']

    breaks = mongoengine.DynamicField()
    conflicts = mongoengine.DynamicField()
    depends = mongoengine.DynamicField()
    enhances = mongoengine.DynamicField()
    pre_depends = mongoengine.DynamicField()
    provides = mongoengine.DynamicField()
    recommends = mongoengine.DynamicField()
    replaces = mongoengine.DynamicField()
    suggests = mongoengine.DynamicField()

    # For backward compatibility
    _ns = mongoengine.StringField(required=True, default=meta['collection'])
    _content_type_id = mongoengine.StringField(required=True, default=TYPE_ID)

    # Non-key fields

    source = mongoengine.StringField()
    maintainer = mongoengine.StringField()
    installed_size = mongoengine.StringField()
    section = mongoengine.StringField()
    priority = mongoengine.StringField()
    multi_arch = mongoengine.StringField()
    homepage = mongoengine.StringField()
    description = mongoengine.StringField()
    original_maintainer = mongoengine.StringField()

    @classmethod
    def from_file(cls, filename, user_metadata=None):
        if hasattr(filename, "read"):
            fobj = filename
        else:
            try:
                fobj = open(filename, "r")
            except IOError as e:
                raise Error(str(e))
        unit_md = cls._read_metadata(filename)
        unit_md.update(checksumtype=util.TYPE_SHA256,
                       checksum=cls._compute_checksum(fobj),
                       size=fobj.tell())

        return cls.from_metadata(unit_md, user_metadata)

    @classmethod
    def from_metadata(cls, unit_md, user_metadata=None):
        ignored = set(['filename'])

        metadata = dict()
        for attr, fdef in cls._fields.items():
            if attr == 'id' or attr.startswith('_'):
                continue
            if user_metadata and attr in user_metadata:
                # We won't be mapping fields from
                # user_metadata, if the user wanted to overwrite something
                # they'd have done it with the properties pulp expects.
                metadata[attr] = user_metadata[attr]
            prop_name = cls.UNIT_KEY_TO_FIELD_MAP.get(attr, attr)
            val = unit_md.get(prop_name)
            if val is None and fdef.required and attr not in ignored:
                raise Error('Required field is missing: {}'.format(attr))
            metadata[attr] = val
        metadata['filename'] = cls.filename_from_unit_key(metadata)
        return cls(**metadata)

    @classmethod
    def _compute_checksum(cls, fobj):
        cstype = util.TYPE_SHA256
        return util.calculate_checksums(fobj, [cstype])[cstype]

    @classmethod
    def filename_from_unit_key(cls, unit_key):
        return "{0}_{1}_{2}.{3}".format(
            unit_key['name'], unit_key['version'],
            unit_key['architecture'], cls.TYPE_ID)

    @property
    def download_path(self):
        """
        This should only be used during the initial sync
        """
        return self.relativepath

    def get_symlink_name(self):
        return self.filename

    @property
    def all_properties(self):
        ret = dict()
        for k in self.__class__._fields:
            if k.startswith('_'):
                continue
            ret[k] = getattr(self, k)
        return ret

    def associate(self, repo):
        repo_controller.associate_single_unit(
            repository=repo, unit=self)
        return self

    def save_and_associate(self, file_path, repo):
        filename = self.filename_from_unit_key(self.unit_key)
        self.set_storage_path(filename)
        unit = self
        try:
            self.save()
            self.safe_import_content(file_path)
        except NotUniqueError:
            unit = self.__class__.objects.filter(**unit.unit_key).first()
        unit.associate(repo)
        return unit

    @classmethod
    def _read_metadata(cls, filename):
        try:
            deb = debfile.DebFile(filename)
        except debfile.ArError as e:
            raise InvalidPackageError(str(e))
        ret = dict(deb.debcontrol())
        deps = debpkg.DebPkgRequires(**ret)
        # Munge relation fields

        for fname in cls.REL_FIELDS:
            vals = deps.relations.get(fname, [])
            vals = DependencyParser.parse(vals)
            ret[fname] = vals
        return ret


class DependencyParser(object):
    DEP_OPERATOR_MAP = {
        '=': 'EQ',
        '>>': 'GT',
        '>=': 'GE',
        '<<': 'LT',
        '<=': 'LE',
    }

    @classmethod
    def parse(cls, deps):
        assert isinstance(deps, list)

        return [cls._parse_one(x) for x in deps]

    @classmethod
    def _parse_one(cls, dep):
        assert isinstance(dep, list)
        pdeps = [cls._dep_simple(x) for x in dep]
        if len(pdeps) == 1:
            return pdeps[0]
        # Conjunction (dep OR dep)
        return pdeps

    @classmethod
    def _dep_simple(cls, dep):
        ret = dict()
        name = dep.get('name')
        assert name is not None
        ret.update(name=name)
        version = dep.get('version')
        if version is not None:
            flag = cls.DEP_OPERATOR_MAP.get(version[0])
            version = version[1]
            ret.update(version=version, flag=flag)
        arch = cls._dep_restrictions(dep.get('arch'))
        if arch:
            ret.update(arch=arch)

        restrictions = dep.get('restrictions')
        if restrictions:
            restrictions = [cls._dep_restrictions(x) for x in restrictions]
            ret.update(restrictions=restrictions)
        return ret

    @classmethod
    def _dep_restrictions(cls, vlist):
        if not vlist:
            return None
        return [cls._dep_restr(x) for x in vlist]

    @classmethod
    def _dep_restr(cls, value):
        if not value:
            return None
        # (true, "a") -> "a"
        # (false, "a") -> "!a"
        assert isinstance(value, (list, tuple))
        assert len(value) == 2
        if value[0]:
            return value[1]
        return '!' + value[1]


class Error(ValueError):
    pass


class InvalidPackageError(Error):
    pass
