"""
Contains tests for pulp_deb.plugins.db.models
"""

from __future__ import unicode_literals

import mock
import os
# Important to import testbase, since it mocks the server's config import snafu
from .... import testbase
from pulp_deb.plugins.db import models

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                           '../../../data'))


class TestModel(testbase.TestCase):
    def test_from_file_no_metadata(self):
        pkg_path = os.path.join(DATA_DIR, "nscd_2.24-7ubuntu2_amd64.deb")
        pkg = models.DebPackage.from_file(pkg_path)
        self.assertTrue(isinstance(pkg, models.DebPackage))
        self.assertEquals(pkg.unit_key, {
            'name': 'nscd',
            'version': '2.24-7ubuntu2',
            'architecture': 'amd64',
            'checksum': '177937795c2ef5b381718aefe2981ada4e8cfe458226348d87a6f5b100a4612b',  # noqa
            'checksumtype': 'sha256',
            })

    def test_from_file_different_checksumtype(self):
        metadata = dict(checksumtype='sha1',
                        checksum='fake')
        pkg_path = os.path.join(DATA_DIR, "nscd_2.24-7ubuntu2_amd64.deb")
        pkg = models.DebPackage.from_file(pkg_path, metadata)
        self.assertTrue(isinstance(pkg, models.DebPackage))
        self.assertEquals(pkg.unit_key['name'], 'nscd')
        self.assertEquals(
            'sha256',
            pkg.checksumtype)
        self.assertEquals(
            '177937795c2ef5b381718aefe2981ada4e8cfe458226348d87a6f5b100a4612b',
            pkg.checksum)

    def test_from_file_no_file(self):
        with self.assertRaises(ValueError) as cm:
            models.DebPackage.from_file('/missing-file')
        self.assertEquals(
            "[Errno 2] No such file or directory: u'/missing-file'",
            str(cm.exception))

    def test_from_file_bad(self):
        with self.assertRaises(ValueError):
            models.DebPackage.from_file(__file__)

    @classmethod
    def _make_property(cls, **properties):
        l = [('Property', 'Value'), ('s72', 'l0')]
        l.extend(sorted(properties.items()))
        return '\n'.join('{}\t{}'.format(k, v) for (k, v) in l)

    @classmethod
    def _make_table(cls, *tables):
        return '\n'.join(tables)

    @mock.patch("pulp_deb.plugins.db.models")
    def tttest_from_file_deb(self, _Popen):
        msm_md_path = os.path.join(DATA_DIR, "msm-msiinfo-export.out")
        msm_md = open(msm_md_path).read()
        msi_properties = self._make_msi_property(
            ProductName='lorem-ipsum',
            ProductVersion='0.0.1',
            Manufacturer='Cicero Enterprises',
            ProductCode='{0FE5FDB7-1DA6-44D2-8C17-10510D12D0EE}',
            UpgradeCode='{12345678-1234-1234-1234-111111111111}',
        )
        popen = _Popen.return_value
        popen.configure_mock(returncode=0)
        popen.communicate.side_effect = [
            (self._make_msi_table("ModuleSignature", "Property"), ""),
            (msi_properties, ""),
            (msm_md, ""),
        ]
        metadata = dict(checksumtype='sha256',
                        checksum='doesntmatter')
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.DebPackage.from_file(msi_path, metadata)
        self.assertEquals("lorem-ipsum",
                          pkg.unit_key['name'])
        self.assertEquals("0.0.1",
                          pkg.unit_key['version'])
        self.assertEquals(
            [
                dict(guid='8E012345_0123_4567_0123_0123456789AB',
                     version='1.2.3.4', name='foobar'),
            ],
            pkg.ModuleSignature)

    @mock.patch("pulp_deb.plugins.db.models")
    def tttest_from_file_msi_no_module_signature(self, _Popen):
        msm_md_path = os.path.join(DATA_DIR, "msm-msiinfo-export.out")
        msm_md = open(msm_md_path).read()
        msi_properties = self._make_msi_property(
            ProductName='lorem-ipsum',
            ProductVersion='0.0.1',
            Manufacturer='Cicero Enterprises',
            ProductCode='{0FE5FDB7-1DA6-44D2-8C17-10510D12D0EE}',
            UpgradeCode='{12345678-1234-1234-1234-111111111111}',
        )
        popen = _Popen.return_value
        popen.configure_mock(returncode=0)
        popen.communicate.side_effect = [
            (self._make_msi_table("Property"), ""),
            (msi_properties, ""),
            (msm_md, ""),
        ]
        metadata = dict(checksumtype='sha256',
                        checksum='doesntmatter')
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.DebPackage.from_file(msi_path, metadata)
        self.assertEquals("lorem-ipsum",
                          pkg.unit_key['name'])
        self.assertEquals("0.0.1",
                          pkg.unit_key['version'])
        self.assertEquals(
            [],
            pkg.ModuleSignature)

    @mock.patch("pulp_deb.plugins.db.models")
    def tttest_from_file_msm(self, _Popen):
        msm_md_path = os.path.join(DATA_DIR, "msm-msiinfo-export.out")
        msm_md = open(msm_md_path).read()
        popen = _Popen.return_value
        popen.configure_mock(returncode=0)
        popen.communicate.side_effect = [
            ("ModuleSignature", ""),
            (msm_md, ""),
        ]
        metadata = dict(checksumtype='sha256',
                        checksum='doesntmatter')
        msi_path = os.path.join(DATA_DIR, "lorem-ipsum-0.0.1.msi")
        pkg = models.DebPackage.from_file(msi_path, metadata)
        self.assertEquals("foobar",
                          pkg.unit_key['name'])
        self.assertEquals("1.2.3.4",
                          pkg.unit_key['version'])
        self.assertEquals("8E012345_0123_4567_0123_0123456789AB",
                          pkg.guid)
