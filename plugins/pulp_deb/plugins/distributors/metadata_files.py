"""
This file provides functions for writing 'Release' and 'Packages' files.
It also provides functions for compressing and signing these files.
"""

import os
import gzip
import bz2

from shutil import copyfileobj
from copy import deepcopy
from time import strftime, gmtime
from debian import deb822
from pulp_deb.plugins.db.models import DebPackage

BUFFER_SIZE = 65536


def write_packages_file(path, component, packages):
    """
    Writes a 'Packages' file for an apt repository.
    This function assumes the file ":path:/Packages" does not exist.

    :param path: the path to the folder where the 'Packages' file will be placed
    :param component: the release component to which the packages file belongs
                      (this is needed for the 'pool' path of each package)
    :returns: the path to the 'Packages' file
    """
    output_file_path = os.path.join(path, 'Packages')

    with open(output_file_path, 'a') as packages_file:
        for package in packages:
            write_packages_file_paragraph(packages_file, component, package)
            packages_file.write('\n')

    return output_file_path


def write_packages_file_paragraph(packages_file, component, package):
    """
    Writes a single 'Packages' file paragraph (the entry for a single package).
    This function assumes the object supplied by :package: is correct.
    The order of entries are extracted from an official Debian mirror.

    :param packages_file: the file handle that is written to
    :param component: the release component to which the packages file belongs
                      (this is needed for the 'pool' path of each package)
    :param package: a single DebPackage object
    """
    # Ordered list of control file fields explicitly known to pulp_deb:
    known_control_fields = [
        'Package',
        'Source',
        'Version',
        'Installed-Size',
        'Maintainer',
        'Original-Maintainer',
        'Architecture',
        'Replaces',
        'Provides',
        'Depends',
        'Pre-Depends',
        'Recommends',
        'Suggests',
        'Enhances',
        'Conflicts',
        'Breaks',
        'Description',
        'Multi-Arch',
        'Homepage',
        'Section',
        'Priority',
    ]

    packages_object = deb822.Packages()
    control_fields = deepcopy(package.control_fields)

    # Add all known control fields (in order):
    for field in known_control_fields:
        if field in control_fields:
            packages_object[field] = control_fields.pop(field).encode('utf8')

    # Also add remaining (unknown) control fields:
    for field, value in control_fields.iteritems():
        packages_object[field] = value.encode('utf8')

    # Explicitly add various non control fields:
    relative_pool_path = os.path.join('pool', component, package.filename,)
    packages_object['Filename'] = relative_pool_path
    packages_object['Size'] = str(package.size)
    packages_object['MD5sum'] = package.md5sum
    packages_object['SHA1'] = package.sha1
    packages_object['SHA256'] = package.sha256

    packages_object.dump(packages_file)


def write_release_file(path, meta_data, release_meta_files):
    """
    Writes a 'Release' file for an apt repository.
    This function assumes the file ":path:/Release" does not exist.

    :param path: the path to the folder where the 'Release' file will be placed
    :param meta_data: a dict containing the needed meta data
    :param release_meta_files: a list of paths to files to be included
    :returns: the path to the 'Release' file
    """
    output_file_path = os.path.join(path, 'Release')

    # Ordered list of supported non-checksum fields (tuples):
    # Known to exist but currently unsupported fields include:
    # "Acquire-By-Hash" (after 'date')
    fields = [
        ('origin', 'Origin'),
        ('label', 'Label'),
        ('suite', 'Suite'),
        ('version', 'Version'),
        ('codename', 'Codename'),
        ('changelogs', 'Changelogs'),
        ('date', 'Date'),
        ('architectures', 'Architectures'),
        ('components', 'Components'),
        ('description', 'Description'),
    ]
    # Ordered list of supported checksum fields (tuples):
    checksum_fields = [
        ('md5sum', 'MD5sum'),
        ('sha1', 'SHA1'),
        ('sha256', 'SHA256'),
    ]

    # Amend or add incomplete fields:
    meta_data['architectures'] = " ".join(meta_data['architectures'])
    meta_data['components'] = " ".join(meta_data['components'])
    meta_data['date'] = strftime('%a, %d %b %Y %H:%M:%S +0000', gmtime())

    # Initialize deb822 object:
    release = deb822.Release()

    # Translate meta_data to deb822 for all fields (without checksum_fields):
    for field in fields:
        if field[0] in meta_data:
            release[field[1]] = meta_data[field[0]]

    # Initialize the needed deb822 checksum fields:
    release['MD5sum'] = []
    release['SHA1'] = []
    release['SHA256'] = []

    # Add the checksum fields to the deb822 object:
    for file_path in release_meta_files:
        checksums = DebPackage.calculate_deb_checksums(file_path)
        file_size = os.path.getsize(file_path)
        relative_path = os.path.relpath(file_path, path)
        for checksum_type in checksum_fields:
            release[checksum_type[1]].append({checksum_type[0]: checksums[checksum_type[0]],
                                              'size': file_size,
                                              'name': relative_path})

    # Write the deb822 object to a file:
    with open(output_file_path, "wb") as release_file:
        release.dump(release_file)

    return output_file_path


def gzip_compress_file(input_file_path):
    """
    Compresses a file using gzip. The compressed file is appended with '.gz'.

    :param input_file_path: the path to the file that is to be compressed
    :returns: the path to the compressed file
    """
    output_file_path = '{}.gz'.format(input_file_path)

    with open(input_file_path, 'rb') as input_file:
        with gzip.open(output_file_path, 'wb') as output_file:
            copyfileobj(input_file, output_file)

    return output_file_path


def bz2_compress_file(input_file_path):
    """
    Compresses a file using bz2. The compressed file is appended with '.bz2'.

    :param input_file_path: the path to the file that is to be compressed
    :returns: the path to the compressed file
    """
    output_file_path = '{}.bz2'.format(input_file_path)

    with open(input_file_path, 'rb') as input_file:
        with open(output_file_path, 'wb') as output_file:
            output_file.write(bz2.compress(input_file.read()))

    return output_file_path
