import mongoengine
from copy import deepcopy
from os.path import getsize
from debian import debfile, deb822
from debpkgr import debpkg
from pulp.server import util
from pulp.server.controllers import repository as repo_controller
from pulp.server.db.model import ContentUnit, FileContentUnit
from pulp_deb.common import ids

NotUniqueError = mongoengine.NotUniqueError


class DebPackage(FileContentUnit):
    TYPE_ID = ids.TYPE_ID_DEB
    meta = dict(collection="units_deb",
                indexes=list(ids.UNIT_KEY_DEB))
    unit_key_fields = ids.UNIT_KEY_DEB

    # Should contain all control file fields explicitly supported by pulp_deb:
    # (Fields not found in control files are handled separately).
    UNIT_KEY_TO_FIELD_MAP = dict(
        name="Package",
        version="Version",
        architecture="Architecture",
        breaks="Breaks",
        conflicts="Conflicts",
        depends="Depends",
        enhances="Enhances",
        pre_depends="Pre-Depends",
        provides="Provides",
        recommends="Recommends",
        replaces="Replaces",
        suggests="Suggests",
        source="Source",
        maintainer="Maintainer",
        installed_size="Installed-Size",
        section="Section",
        priority="Priority",
        multi_arch="Multi-Arch",
        homepage="Homepage",
        description="Description",
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

    REQUIRED_FIELDS = ['name', 'version', 'architecture', 'checksumtype',
                       'checksum', 'filename']

    REL_FIELDS = ['breaks', 'conflicts', 'depends', 'enhances', 'pre_depends',
                  'provides', 'recommends', 'replaces', 'suggests']

    # The REL_FIELDS are intended for structured relationship information.
    # Raw relationship fields as used in Debian control files and Packages
    # indices are stored in the control_fields dict instead.

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

    # Store all Debian control fields in a dict of strings.
    # This ensures we can retain all control file information even for fields
    # not explicitly known to pulp_deb.
    control_fields = mongoengine.DynamicField()

    @classmethod
    def from_deb_file(cls, input_file_path, user_metadata={}):
        """
        Creates a DebPackage object (and by extension a mongodb entry) from a
        .deb package file.
        """
        try:
            control_fields = debfile.DebFile(input_file_path).debcontrol()
        except debfile.ArError as invalid_package_error:
            raise InvalidPackageError(str(invalid_package_error))
        except IOError as missing_file_error:
            raise Error(str(missing_file_error))

        initialization_params = user_metadata
        initialization_params.update(cls._to_internal_dict_style(control_fields))
        initialization_params = cls._parse_rel_fields(initialization_params)

        with open(input_file_path) as input_file:
            checksum = cls._compute_checksum(input_file)

        initialization_params.update(
            size=getsize(input_file_path),
            checksumtype=util.TYPE_SHA256,
            checksum=checksum,
            control_fields=control_fields,
        )

        cls._check_for_required_fields(initialization_params)
        filename = cls.filename_from_unit_key(initialization_params)
        initialization_params['filename'] = filename

        return cls(**initialization_params)

    @classmethod
    def from_packages_paragraph(cls, packages_paragraph):
        """
        Creates a DebPackage object (and by extension a mongodb entry) from a
        single 'Packages' file paragraph as parsed by python-debian's
        deb822.Packages.iter_paragraphs function.
        """

        NON_CONTROL_FIELDS = [
            'Filename',
            'Size',
            'MD5sum',
            'SHA1',
            'SHA256',
            'SHA512',
            'Description-md5',
        ]

        checksum = packages_paragraph['SHA256']

        control_fields = deepcopy(packages_paragraph)
        for field in NON_CONTROL_FIELDS:
            control_fields.pop(field, None)

        initialization_params = cls._to_internal_dict_style(packages_paragraph)
        initialization_params = cls._parse_rel_fields(initialization_params)

        # Since 'Size' is not a control file field we need to handle it separately:
        if 'Size' in packages_paragraph:
            initialization_params['size'] = packages_paragraph['Size']

        initialization_params.update(
            checksumtype=util.TYPE_SHA256,
            checksum=checksum,
            control_fields=control_fields,
        )

        cls._check_for_required_fields(initialization_params)
        filename = cls.filename_from_unit_key(initialization_params)
        initialization_params['filename'] = filename

        return cls(**initialization_params)

    @classmethod
    def _to_internal_dict_style(cls, deb822_style_dict):
        """
        Converts a dict using deb822 style keys to one using our internal field
        names. Entries that do not have a corresponding field name are dropped.
        """
        return_value = dict()
        for field_name, deb822_key in cls.UNIT_KEY_TO_FIELD_MAP.iteritems():
            if deb822_key in deb822_style_dict:
                return_value[field_name] = deb822_style_dict[deb822_key]
        return return_value

    @classmethod
    def _parse_rel_fields(cls, field_dict):
        """
        Converts any relatinal fields found in field_dict from plain Debian
        package relation strings to a parsed dict.
        """
        for rel_field in cls.REL_FIELDS:
            if rel_field in field_dict:
                parsed_rel_value = DependencyParser.from_string(field_dict[rel_field])
                field_dict[rel_field] = parsed_rel_value

        return field_dict

    @classmethod
    def _check_for_required_fields(cls, metadata):
        """
        Checks if the dict in metadata contains a value for all required db
        fields except 'filename', which needs to be generated from the other
        required fields.
        """
        for field in cls.REQUIRED_FIELDS:
            if field == 'filename':
                pass
            elif field not in metadata:
                raise Error('Required field is missing: {}'.format(field))

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


class DebComponent(ContentUnit):
    """
    This unittype represents a deb release component
    """
    TYPE_ID = ids.TYPE_ID_DEB_COMP
    meta = dict(collection="units_deb_component",
                indexes=list(ids.UNIT_KEY_DEB_COMP))
    unit_key_fields = ids.UNIT_KEY_DEB_COMP

    name = mongoengine.StringField(required=True)
    release = mongoengine.StringField(required=True)
    repoid = mongoengine.StringField(required=True)
    packages = mongoengine.ListField()

    # For backward compatibility
    _ns = mongoengine.StringField(required=True, default=meta['collection'])
    _content_type_id = mongoengine.StringField(required=True, default=TYPE_ID)

    @classmethod
    def get_or_create_and_associate(cls, repo, release_unit, name):
        unit = cls()
        unit.name = name
        unit.repoid = repo.id
        unit.release = release_unit.codename
        try:
            unit.save()
        except NotUniqueError:
            unit = cls.objects.filter(**unit.unit_key).first()
        repo_controller.associate_single_unit(
            repository=repo.repo_obj, unit=unit)
        return unit

    def associate(self, repo):
        # actually update the corresponding unit in the repository
        # or create a new copy
        unit = self
        if unit.repoid != repo.repo_id:
            # find the corresponding unit
            unit = self.__class__.objects.filter(repoid=repo.repo_id,
                                                 name=self.name,
                                                 release=self.release).first()
            if unit is None:
                # create a new one
                unit = self.__class__()
                unit.repoid = repo.repo_id
                unit.name = self.name
                unit.release = self.release

            # update data
            unit.packages = self.packages
            unit.save()
        repo_controller.associate_single_unit(
            repository=repo, unit=unit)
        return unit


class DebRelease(ContentUnit):
    """
    This unittype represents a deb release
    """
    TYPE_ID = ids.TYPE_ID_DEB_RELEASE
    meta = dict(collection="units_deb_release",
                indexes=list(ids.UNIT_KEY_DEB_RELEASE))
    unit_key_fields = ids.UNIT_KEY_DEB_RELEASE

    repoid = mongoengine.StringField(required=True)
    codename = mongoengine.StringField(required=True)
    suite = mongoengine.StringField()

    # For backward compatibility
    _ns = mongoengine.StringField(required=True, default=meta['collection'])
    _content_type_id = mongoengine.StringField(required=True, default=TYPE_ID)

    @classmethod
    def get_or_create_and_associate(cls, repo, codename, suite):
        unit = cls()
        unit.repoid = repo.id
        unit.codename = codename
        unit.suite = suite
        try:
            unit.save()
        except NotUniqueError:
            unit = cls.objects.filter(**unit.unit_key).first()
            unit.suite = suite
            unit.save()
        repo_controller.associate_single_unit(
            repository=repo.repo_obj, unit=unit)
        return unit

    def associate(self, repo):
        # actually update the corresponding unit in the repository
        # or create a new copy
        unit = self
        if unit.repoid != repo.repo_id:
            # find the corresponding unit
            unit = self.__class__.objects.filter(repoid=repo.repo_id,
                                                 codename=self.codename).first()
            if unit is None:
                # create a new one
                unit = self.__class__()
                unit.repoid = repo.repo_id
                unit.codename = self.codename

            # update data
            unit.suite = self.suite
            unit.save()
        repo_controller.associate_single_unit(
            repository=repo, unit=unit)
        return unit


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
    def from_string(cls, relationship_string):
        initial_parse = deb822.PkgRelation.parse_relations(relationship_string)
        return cls.parse(initial_parse)

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
