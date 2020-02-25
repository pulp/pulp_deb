import mongoengine
from copy import deepcopy
from os.path import getsize
from debian import debfile, deb822
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

    # Fields included in the ids.UNIT_KEY_DEB list:
    # Note: The first three of these are control file fields.
    name = mongoengine.StringField(required=True)
    version = mongoengine.StringField(required=True)
    architecture = mongoengine.StringField(required=True)
    # Note: checksumtype and checksum should only be used for pulp internals.
    # Use md5sum, sha1, and sha256 for publishing and similar.
    # Currently, checksumtype should always be 'sha256'
    checksumtype = mongoengine.StringField(required=True)
    checksum = mongoengine.StringField(required=True)

    # Other required fields:
    filename = mongoengine.StringField(required=True)

    # List of required fields:
    REQUIRED_FIELDS = ['name', 'version', 'architecture', 'checksumtype',
                       'checksum', 'filename']

    # Named checksum fields:
    md5sum = mongoengine.StringField()
    sha1 = mongoengine.StringField()
    sha256 = mongoengine.StringField()

    # Other non control file fields:
    # Note: Relativepath does not appear to be meaningfully in use.
    size = mongoengine.IntField()
    relativepath = mongoengine.StringField()

    # Relational fields:
    # Note: These are intended for structured relationship information. Raw
    # relationship field strings as used in Debian control files and Packages
    # indicies are stored in the control_fields dict instead.
    breaks = mongoengine.DynamicField()
    conflicts = mongoengine.DynamicField()
    depends = mongoengine.DynamicField()
    enhances = mongoengine.DynamicField()
    pre_depends = mongoengine.DynamicField()
    provides = mongoengine.DynamicField()
    recommends = mongoengine.DynamicField()
    replaces = mongoengine.DynamicField()
    suggests = mongoengine.DynamicField()

    # List of relational fields:
    REL_FIELDS = ['breaks', 'conflicts', 'depends', 'enhances', 'pre_depends',
                  'provides', 'recommends', 'replaces', 'suggests']

    # The control file fields dict:
    # Note: This stores a dict of strings as used within the python-debian
    # library. This allows us to retain all control file information, even for
    # fields not explicitly supported by pulp_deb.
    control_fields = mongoengine.DynamicField()

    # Remaining control file fields:
    # Note: With the addition of the control_fields dict, these fields contain
    # redundant information.
    source = mongoengine.StringField()
    maintainer = mongoengine.StringField()
    installed_size = mongoengine.StringField()
    section = mongoengine.StringField()
    priority = mongoengine.StringField()
    multi_arch = mongoengine.StringField()
    homepage = mongoengine.StringField()
    description = mongoengine.StringField()
    original_maintainer = mongoengine.StringField()

    # Fields retained for backwards compatibility:
    _ns = mongoengine.StringField(required=True, default=meta['collection'])
    _content_type_id = mongoengine.StringField(required=True, default=TYPE_ID)

    # A dict translating all control file field names from this class into their
    # python-debian (deb822) equivalent.
    # Note: Fields not found in control files are handled separately.
    TO_DEB822_MAP = dict(
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

    @classmethod
    def from_file(cls, filename, user_metadata=None):
        """
        Creates a DebPackage object (and by extension a mongodb entry) from a
        .deb package file.
        """
        try:
            control_fields = debfile.DebFile(filename).debcontrol()
        except debfile.ArError as invalid_package_error:
            raise InvalidPackageError(str(invalid_package_error))
        except IOError as missing_file_error:
            raise Error(str(missing_file_error))

        initialization_params = user_metadata or {}
        initialization_params.update(cls._to_internal_dict_style(control_fields))
        initialization_params = cls._parse_rel_fields(initialization_params)

        checksums = cls.calculate_deb_checksums(filename)

        initialization_params.update(
            size=getsize(filename),
            checksumtype=util.TYPE_SHA256,
            checksum=checksums['sha256'],
            md5sum=checksums['md5sum'],
            sha1=checksums['sha1'],
            sha256=checksums['sha256'],
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

        # Handle non control file fields separately:
        if 'Size' in packages_paragraph:
            initialization_params['size'] = packages_paragraph['Size']
        if 'MD5sum' in packages_paragraph:
            initialization_params['md5sum'] = packages_paragraph['MD5sum']
        if 'SHA1' in packages_paragraph:
            initialization_params['sha1'] = packages_paragraph['SHA1']

        initialization_params.update(
            checksumtype=util.TYPE_SHA256,
            checksum=checksum,
            sha256=checksum,
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
        for field_name, deb822_key in cls.TO_DEB822_MAP.iteritems():
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
        missing_fields = []
        for field in cls.REQUIRED_FIELDS:
            if field == 'filename':
                continue
            if field not in metadata:
                missing_fields.append(field)
        if missing_fields:
            raise Error('Required fields are missing: {}'.format(missing_fields))

    @staticmethod
    def calculate_deb_checksums(input_file_path):
        """
        Uses util.calculate_checksums() to calculate the md5sum, sha1, and sha256
        of a file. The return dict is guaranteed to use the deb style keys
        'md5sum', 'sha1', and 'sha256'.

        :param file_path: the path to the file for which checksums are needed
        :returns: a dict containing the checksums
        """
        CHECKSUM_TYPES = {
            'md5sum': util.TYPE_MD5,
            'sha1': util.TYPE_SHA1,
            'sha256': util.TYPE_SHA256,
        }
        with open(input_file_path) as input_file:
            checksums = util.calculate_checksums(input_file, CHECKSUM_TYPES.values())
        return {deb_key: checksums[util_key] for deb_key, util_key in CHECKSUM_TYPES.items()}

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

    def save_and_associate(self, file_path, repo, force=False):
        filename = self.filename_from_unit_key(self.unit_key)
        self.set_storage_path(filename)
        unit = self
        try:
            self.save()
            self.safe_import_content(file_path)
        except NotUniqueError:
            unit = self.__class__.objects.filter(**unit.unit_key).first()
            if force:
                self.import_content(file_path)
        unit.associate(repo)
        return unit


class DebComponent(ContentUnit):
    """
    This unittype represents a deb release/distribution component
    """
    TYPE_ID = ids.TYPE_ID_DEB_COMP
    meta = dict(collection="units_deb_component",
                indexes=list(ids.UNIT_KEY_DEB_COMP))
    unit_key_fields = ids.UNIT_KEY_DEB_COMP

    name = mongoengine.StringField(required=True)
    distribution = mongoengine.StringField(required=True)
    release = mongoengine.StringField(required=True)
    repoid = mongoengine.StringField(required=True)
    packages = mongoengine.ListField()

    # For backward compatibility
    _ns = mongoengine.StringField(required=True, default=meta['collection'])
    _content_type_id = mongoengine.StringField(required=True, default=TYPE_ID)

    @property
    def plain_component(self):
        return self.name.strip('/').split('/')[-1]

    @property
    def prefixed_component(self):
        prefix = '/'.join(self.distribution.split('/')[1:]).strip('/')
        return (prefix + '/' + self.plain_component).strip('/')

    @classmethod
    def get_or_create_and_associate(cls, repo, release_unit, name):
        unit = cls()
        unit.name = name
        unit.repoid = repo.id
        unit.distribution = release_unit.distribution
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
                                                 distribution=self.distribution).first()
            if unit is None:
                # create a new one
                unit = self.__class__()
                # set the key fields
                unit.repoid = repo.repo_id
                unit.name = self.name
                unit.distribution = self.distribution
                unit.release = self.release

            # update data
            unit.packages = self.packages
            unit.save()
        repo_controller.associate_single_unit(
            repository=repo, unit=unit)
        return unit


class DebRelease(ContentUnit):
    """
    This unittype represents a deb release (also referred to as a "distribution")
    """
    TYPE_ID = ids.TYPE_ID_DEB_RELEASE
    meta = dict(collection="units_deb_release",
                indexes=list(ids.UNIT_KEY_DEB_RELEASE))
    unit_key_fields = ids.UNIT_KEY_DEB_RELEASE

    repoid = mongoengine.StringField(required=True)
    distribution = mongoengine.StringField(required=True)
    codename = mongoengine.StringField(required=True)
    suite = mongoengine.StringField()

    # For backward compatibility
    _ns = mongoengine.StringField(required=True, default=meta['collection'])
    _content_type_id = mongoengine.StringField(required=True, default=TYPE_ID)

    @classmethod
    def get_or_create_and_associate(cls, repo, distribution, codename, suite):
        unit = cls()
        unit.repoid = repo.id
        unit.distribution = distribution
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
                                                 distribution=self.distribution).first()
            if unit is None:
                # create a new one
                unit = self.__class__()
                # set the key fields
                unit.repoid = repo.repo_id
                unit.distribution = self.distribution
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
