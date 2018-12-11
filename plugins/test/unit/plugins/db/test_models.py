# coding=utf-8
"""
Contains tests for pulp_deb.plugins.db.models
"""

from __future__ import unicode_literals

import os
from debian import deb822
# Important to import testbase, since it mocks the server's config import snafu
from .... import testbase
from pulp_deb.plugins.db import models

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                           '../../../data'))


class TestModel(testbase.TestCase):
    def test_from_deb_file_no_metadata(self):
        pkg_path = os.path.join(DATA_DIR, "nscd_2.24-7ubuntu2_amd64.deb")
        pkg = models.DebPackage.from_deb_file(pkg_path)
        self.assertTrue(isinstance(pkg, models.DebPackage))
        self.assertEquals(pkg.unit_key, {
            'name': 'nscd',
            'version': '2.24-7ubuntu2',
            'architecture': 'amd64',
            'checksum': '177937795c2ef5b381718aefe2981ada4e8cfe458226348d87a6f5b100a4612b',  # noqa
            'checksumtype': 'sha256',
            })

    def test_from_deb_file_different_checksumtype(self):
        metadata = dict(checksumtype='sha1',
                        checksum='fake')
        pkg_path = os.path.join(DATA_DIR, "nscd_2.24-7ubuntu2_amd64.deb")
        pkg = models.DebPackage.from_deb_file(pkg_path, metadata)
        self.assertTrue(isinstance(pkg, models.DebPackage))
        self.assertEquals(pkg.unit_key['name'], 'nscd')
        self.assertEquals(
            'sha256',
            pkg.checksumtype)
        self.assertEquals(
            '177937795c2ef5b381718aefe2981ada4e8cfe458226348d87a6f5b100a4612b',
            pkg.checksum)

    def test_from_deb_file_no_file(self):
        with self.assertRaises(ValueError) as cm:
            models.DebPackage.from_deb_file('/missing-file')
        self.assertEquals(
            "[Errno 2] No such file or directory: u'/missing-file'",
            str(cm.exception))

    def test_from_deb_file_bad(self):
        with self.assertRaises(ValueError):
            models.DebPackage.from_deb_file(__file__)

    def test_from_packages_paragraph_all_fields(self):
        packages_paragraph = {
            'Package': 'package-name',
            'Version': '2.234434.1',
            'Architecture': 'amd64',
            'Filename': 'pool/main/p/package-name/package-name_2.234434.1_amd64.deb',
            'Size': '566',
            'Breaks': 'some-package',
            'Conflicts': 'some-package2 (<< 0.3)',
            'Depends': 'some-package3, some-package4',
            'Enhances': 'some-package5 | some-package6',
            'Pre-Depends': 'some-package7 (>= 2:3.12.1-2~)',
            'Recommends': 'python:any (<< 2.8), python:any (>= 2.7.5-5~)',
            'Replaces': 'some-package8',
            'Source': 'source-package-name',
            'Maintainer': 'Some Person <example@example.com>',
            'Installed-Size': '889',
            'Section': 'games',
            'Priority': 'standard',
            'Multi-Arch': 'foreign',
            'Homepage': 'https://www.example.com',
            'Description': 'some\n multiline\n description.',
            'Original-Maintainer': 'Someone Else <else@example.com>',
            'MD5sum': 'fake_md5',
            'SHA1': 'fake_sha1',
            'SHA256': 'fake_sha256',
            'SHA512': 'fake_sha512',
            'Description-md5': 'fake_desc_md5',
        }
        pkg = models.DebPackage.from_packages_paragraph(packages_paragraph)
        self.assertEqual(pkg.name, packages_paragraph['Package'])
        self.assertEqual(pkg.version, packages_paragraph['Version'])
        self.assertEqual(pkg.architecture, packages_paragraph['Architecture'])
        self.assertEqual(pkg.filename, 'package-name_2.234434.1_amd64.deb')
        self.assertEqual(pkg.size, int(packages_paragraph['Size']))
        self.assertEqual(pkg.source, packages_paragraph['Source'])
        self.assertEqual(pkg.maintainer, packages_paragraph['Maintainer'])
        self.assertEqual(pkg.installed_size, packages_paragraph['Installed-Size'])
        self.assertEqual(pkg.section, packages_paragraph['Section'])
        self.assertEqual(pkg.priority, packages_paragraph['Priority'])
        self.assertEqual(pkg.multi_arch, packages_paragraph['Multi-Arch'])
        self.assertEqual(pkg.homepage, packages_paragraph['Homepage'])
        self.assertEqual(pkg.description, packages_paragraph['Description'])
        self.assertEqual(pkg.original_maintainer, packages_paragraph['Original-Maintainer'])
        self.assertEqual(pkg.checksumtype, 'sha256')
        self.assertEqual(pkg.checksum, packages_paragraph['SHA256'])
        self.assertEqual(pkg.relativepath, None)
        self.assertEqual(pkg.breaks, [{'name': u'some-package'}])
        conflicts = [{'flag': 'LT', 'name': u'some-package2', 'version': u'0.3'}]
        self.assertEqual(pkg.conflicts, conflicts)
        depends = [{'name': u'some-package3'}, {'name': u'some-package4'}]
        self.assertEqual(pkg.depends, depends)
        enhances = [[{'name': u'some-package5'}, {'name': u'some-package6'}]]
        self.assertEqual(pkg.enhances, enhances)
        pre_depends = [{'flag': 'GE', 'name': u'some-package7', 'version': u'2:3.12.1-2~'}]
        self.assertEqual(pkg.pre_depends, pre_depends)
        # Note: The current implementation of DependencyParser drops the information ":any"!
        # TODO: This is probably a bug that should be looked at?!
        recommends = [{'flag': 'LT', 'name': u'python', 'version': u'2.8'},
                      {'flag': 'GE', 'name': u'python', 'version': u'2.7.5-5~'}]
        self.assertEqual(pkg.recommends, recommends)
        self.assertEqual(pkg.replaces, [{'name': u'some-package8'}])
        self.assertEqual(pkg.suggests, None)
        control_fields = {
            'Package': packages_paragraph['Package'],
            'Version': packages_paragraph['Version'],
            'Architecture': packages_paragraph['Architecture'],
            'Breaks': packages_paragraph['Breaks'],
            'Conflicts': packages_paragraph['Conflicts'],
            'Depends': packages_paragraph['Depends'],
            'Enhances': packages_paragraph['Enhances'],
            'Pre-Depends': packages_paragraph['Pre-Depends'],
            'Recommends': packages_paragraph['Recommends'],
            'Replaces': packages_paragraph['Replaces'],
            'Source': packages_paragraph['Source'],
            'Maintainer': packages_paragraph['Maintainer'],
            'Installed-Size': packages_paragraph['Installed-Size'],
            'Section': packages_paragraph['Section'],
            'Priority': packages_paragraph['Priority'],
            'Multi-Arch': packages_paragraph['Multi-Arch'],
            'Homepage': packages_paragraph['Homepage'],
            'Description': packages_paragraph['Description'],
            'Original-Maintainer': packages_paragraph['Original-Maintainer'],
        }
        self.assertEqual(control_fields, pkg.control_fields)

    def test_from_packages_paragraph_no_sha256(self):
        packages_paragraph = dict(
            Package='package-name',
            Version='2.234434.1',
            Architecture='amd64',
            Filename='pool/main/p/package-name/package-name_2.234434.1_amd64.deb',
            SHA512='fake_sha512',
        )
        with self.assertRaises(KeyError) as no_sha256_error:
            models.DebPackage.from_packages_paragraph(packages_paragraph)
        self.assertEqual(
            "'SHA256'",
            str(no_sha256_error.exception))

    def test_from_packages_paragraph_missing_required(self):
        packages_paragraph = dict(
            Package='package-name',
            Architecture='amd64',
            Filename='pool/main/p/package-name/package-name_2.234434.1_amd64.deb',
            SHA256='fake_sha256',
        )
        with self.assertRaises(models.Error) as missing_required_fields_error:
            models.DebPackage.from_packages_paragraph(packages_paragraph)
        self.assertEqual(
            'Required field is missing: version',
            str(missing_required_fields_error.exception))

    def test_from_packages_paragraph_non_ascii_field(self):
        packages_paragraph = dict(
            Package='package-name',
            Version='1.0',
            Architecture='amd64',
            Filename='pool/main/p/package-name/package-name_1.0_amd64.deb',
            Maintainer='Gärtner',
            SHA256='fake_sha256',
        )
        models.DebPackage.from_packages_paragraph(packages_paragraph)

    def test_from_packages_paragraph_unknown_field(self):
        packages_paragraph = dict(
            Package='package-name',
            Version='1.0',
            Architecture='amd64',
            Filename='pool/main/p/package-name/package-name_1.0_amd64.deb',
            License='super_free',
            SHA256='fake_sha256',
        )
        pkg = models.DebPackage.from_packages_paragraph(packages_paragraph)
        self.assertEqual(pkg.control_fields['License'], 'super_free')

    def test_equal_outcome_from_deb_file_and_from_packages_paragraph(self):
        packages_paragraph = {
            'Package': '389-admin',
            'Source': '389-admin (1.1.43-1)',
            'Version': '1.1.43-1+b1',
            'Installed-Size': '1247',
            'Maintainer': 'Debian 389ds Team <pkg-fedora-ds-maintainers@lists.alioth.debian.org>',
            'Architecture': 'amd64',
            'Depends': '389-ds-base, apache2, libapache2-mod-nss, libcgi-pm-perl,'
            ' libds-admin-serv0 (= 1.1.43-1+b1), libmozilla-ldap-perl,'
            ' libnss3-tools, init-system-helpers (>= 1.18~), libadminutil0'
            ' (>= 1.1.21), libc6 (>= 2.14), libldap-2.4-2 (>= 2.4.39), libnspr4'
            ' (>= 2:4.10.9), libnss3 (>= 2:3.13.4-2~)',
            'Pre-Depends': 'debconf (>= 0.5) | debconf-2.0',
            'Description': '389 Directory Administration Server\n'
            ' 389 Directory Administration Server is an HTTP agent that provides\n'
            ' management features for 389 Directory Server. It provides some\n'
            ' management web apps that can be used through a web browser. It provides\n'
            ' the authentication, access control, and CGI utilities used by the console.',
            'Homepage': 'http://directory.fedoraproject.org',
            'Description-md5': '54d5378a9195f30f9bb174c93052507a',
            'Section': 'net',
            'Priority': 'optional',
            'Filename': 'pool/main/3/389-admin/389-admin_1.1.43-1+b1_amd64.deb',
            'Size': '265682',
            'MD5sum': 'a54a688169a4ebb75d0390de536e9910',
            'SHA256': '567e370225de43dce18896e9d64d19a5d46b351f4e423dd16845710eac5e9786',
        }
        pkg_path = os.path.join(DATA_DIR, "389-admin_1.1.43-1+b1_amd64.deb")
        pkg1 = models.DebPackage.from_deb_file(pkg_path, {})
        pkg2 = models.DebPackage.from_packages_paragraph(packages_paragraph)
        self.assertEqual(pkg1.all_properties.update(id='fake_id'),
                         pkg2.all_properties.update(id='fake_id'),)

    def test_dep_parse(self):
        # Make sure we get the same behavior out of deb822 relationship
        # parsing
        tests = [
            ('emacs | emacsen, make, debianutils (>= 1.7)',
             [
                 [{'restrictions': None, 'version': None, 'arch': None,
                   'name': 'emacs', 'archqual': None},
                  {'restrictions': None, 'version': None, 'arch': None,
                   'name': 'emacsen', 'archqual': None}],
                 [{'restrictions': None, 'version': None, 'arch': None,
                   'name': 'make', 'archqual': None}],
                 [{'restrictions': None, 'version': ('>=', '1.7'), 'arch': None,
                   'name': 'debianutils', 'archqual': None}]],
             [
                 [{'name': 'emacs'}, {'name': 'emacsen'}],
                 {'name': 'make'},
                 {'name': 'debianutils', 'version': '1.7', 'flag': 'GE'},
             ]),

            ('tcl8.4-dev [amd64], procps [!hurd-i386]',
             [
                 [{'restrictions': None, 'version': None,
                   'arch': [(True, 'amd64')],
                   'name': 'tcl8.4-dev', 'archqual': None}],
                 [{'restrictions': None, 'version': None,
                   'arch': [(False, 'hurd-i386')],
                   'name': 'procps', 'archqual': None}]],
             [
                 {'name': 'tcl8.4-dev', 'arch': ['amd64']},
                 {'name': 'procps', 'arch': ['!hurd-i386']},
             ]),

            ('texlive <stage1 !cross> <stage2>',
             [
                 [{'restrictions': [
                     [(True, 'stage1'), (False, 'cross')],
                     [(True, 'stage2')]],
                   'version': None, 'arch': None, 'name': 'texlive', 'archqual': None}]],
             [
                 {'name': 'texlive', 'restrictions': [['stage1', '!cross'],
                                                      ['stage2']]},
             ]),
        ]
        for strdep, debdep, pulpdep in tests:
            pkg = list(deb822.Packages.iter_paragraphs(
                "Depends: {}".format(strdep)))[0]
            self.assertEquals(debdep, pkg.relations['depends'])
            self.assertEquals(pulpdep, models.DependencyParser.parse(debdep))
