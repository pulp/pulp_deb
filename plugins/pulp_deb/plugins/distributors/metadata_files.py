"""
This file provides functions for writing 'Release' and 'Packages' files.
It also provides functions for compressing and signing these files.
"""

import os
import gzip
import shutil
import bz2
import time

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
    # Ordered list of supported fields (tuples):
    # Known to exist but currently unsupported fields include:
    # "Description-md5" (after 'homepage')
    # "Tag" (after "Description-md5")
    fields = [
        ('name', 'Package'),
        ('source', 'Source'),
        ('version', 'Version'),
        ('installed_size', 'Installed-Size'),
        ('maintainer', 'Maintainer'),
        ('original_maintainer', 'Original-Maintainer'),
        ('architecture', 'Architecture'),
        ('replaces', 'Replaces'),
        ('provides', 'Provides'),
        ('depends', 'Depends'),
        ('pre_depends', 'Pre-Depends'),
        ('recommends', 'Recommends'),
        ('suggests', 'Suggests'),
        ('enhances', 'Enhances'),
        ('conflicts', 'Conflicts'),
        ('breaks', 'Breaks'),
        ('description', 'Description'),
        ('multi_arch', 'Multi-Arch'),
        ('homepage', 'Homepage'),
        ('section', 'Section'),
        ('priority', 'Priority'),
        ('filename', 'Filename'),
        ('size', 'Size'),
        ('md5sum', 'MD5sum'),
        ('sha1', 'SHA1'),
        ('sha256', 'SHA256'),
    ]

    package_properties = package.all_properties
    packages_object = deb822.Packages()

    for field in fields:
        if field[0] == 'filename':
            # TODO: A better pool folder structure is desirable.
            relative_pool_path = os.path.join('pool',
                                              component,
                                              package.filename,)
            packages_object['Filename'] = relative_pool_path
        elif package_properties[field[0]]:
            packages_object[field[1]] = cast_to_utf8_unicode(package_properties[field[0]])

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
    meta_data['date'] = time.strftime('%a, %d %b %Y %H:%M:%S +0000', time.gmtime())

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
            shutil.copyfileobj(input_file, output_file)

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


def cast_to_utf8_unicode(obj):
    """
    Will cast input of type 'int' or 'str' to 'unicode' using utf8 and return
    other types unchanged.

    :param obj: the object to be casted
    :returns: an unicode string using utf8 encoding or obj
    """
    if type(obj) == str:
        return_value = obj.decode('utf8')
    elif type(obj) == int:
        return_value = str(obj).decode('utf8')
    else:
        return_value = obj
    return return_value
