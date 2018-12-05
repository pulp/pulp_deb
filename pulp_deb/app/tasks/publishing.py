import os
import logging
from gettext import gettext as _

import hashlib
from debian import deb822

from django.core.files import File

from django.db.models import Q

from pulpcore.plugin.models import (
    RepositoryVersion,
    Publication,
    PublishedArtifact,
    PublishedMetadata,
)
from pulpcore.plugin.tasking import WorkingDirectory

from pulp_deb.app.models import (
    Package,
    DebVerbatimPublisher,
    DebPublisher,
)


log = logging.getLogger(__name__)


def publish_verbatim(publisher_pk, repository_version_pk):
    """
    Use provided publisher to create a verbatim Publication based on a RepositoryVersion.

    Args:
        publisher_pk (str): Use the publish settings provided by this publisher.
        repository_version_pk (str): Create a publication from this repository version.
    """
    publisher = DebVerbatimPublisher.objects.get(pk=publisher_pk)
    repository_version = RepositoryVersion.objects.get(
        pk=repository_version_pk)

    log.info(_('Publishing (verbatim): repository={repo}, version={ver}, publisher={pub}').format(
        repo=repository_version.repository.name,
        ver=repository_version.number,
        pub=publisher.name
    ))

    with WorkingDirectory():
        with Publication.create(repository_version, publisher, pass_through=True) as publication:
            pass

    log.info(_('Publication (verbatim): {publication} created').format(
        publication=publication.pk))


def publish(publisher_pk, repository_version_pk):
    """
    Use provided publisher to create a Publication based on a RepositoryVersion.

    Args:
        publisher_pk (str): Use the publish settings provided by this publisher.
        repository_version_pk (str): Create a publication from this repository version.
    """
    publisher = DebPublisher.objects.get(pk=publisher_pk)
    repository_version = RepositoryVersion.objects.get(
        pk=repository_version_pk)

    log.info(_('Publishing: repository={repo}, version={ver}, publisher={pub}').format(
        repo=repository_version.repository.name,
        ver=repository_version.number,
        pub=publisher.name
    ))

    with WorkingDirectory():
        with Publication.create(repository_version, publisher, pass_through=False) as publication:
            if publisher.simple:
                repository = repository_version.repository
                release = deb822.Release()
                # TODO: release['Label']
                release['Codename'] = 'default'
                release['Components'] = 'all'
                release['Architectures'] = ''
                if repository.description:
                    release['Description'] = repository.description
                release['MD5sum'] = []
                release['SHA1'] = []
                release['SHA256'] = []
                release['SHA512'] = []
                packages_files = {}
                for package in Package.objects.filter(
                    pk__in=repository_version.content.filter(Q(type='package'))
                ):
                    published_artifact = PublishedArtifact(
                        relative_path=package.filename(),
                        publication=publication,
                        content_artifact=package.contentartifact_set.get(),
                    )
                    published_artifact.save()
                    if package.architecture not in packages_files:
                        package_index_path = os.path.join(
                            'dists',
                            'default',
                            'all',
                            'binary-{}'.format(package.architecture),
                            'Packages',
                        )
                        os.makedirs(os.path.dirname(
                            package_index_path), exist_ok=True)
                        packages_files[package.architecture] = (
                            open(package_index_path, 'wb'), package_index_path)
                    package.to822('all').dump(
                        packages_files[package.architecture][0])
                    packages_files[package.architecture][0].write(b'\n')
                for packages_file, package_index_path in packages_files.values():
                    packages_file.close()
                    with open(package_index_path, 'rb') as packages_file:
                        size = 0
                        md5sum_hasher = hashlib.md5()
                        sha1_hasher = hashlib.sha1()
                        sha256_hasher = hashlib.sha256()
                        sha512_hasher = hashlib.sha512()
                        for chunk in iter(lambda: packages_file.read(4096), b''):
                            size += len(chunk)
                            md5sum_hasher.update(chunk)
                            sha1_hasher.update(chunk)
                            sha256_hasher.update(chunk)
                            sha512_hasher.update(chunk)

                        release['MD5sum'].append({
                            'md5sum': md5sum_hasher.hexdigest(),
                            'size': size,
                            'name': package_index_path,
                        })
                        release['SHA1'].append({
                            'sha1': sha1_hasher.hexdigest(),
                            'size': size,
                            'name': package_index_path,
                        })
                        release['SHA256'].append({
                            'sha256': sha256_hasher.hexdigest(),
                            'size': size,
                            'name': package_index_path,
                        })
                        release['SHA512'].append({
                            'sha512': sha512_hasher.hexdigest(),
                            'size': size,
                            'name': package_index_path,
                        })

                    package_index = PublishedMetadata(
                        relative_path=package_index_path,
                        publication=publication,
                        file=File(open(package_index_path, 'rb')),
                    )
                    package_index.save()
                release['Architectures'] = ', '.join(packages_files.keys())
                release_path = os.path.join('dists', 'default', 'Release')
                os.makedirs(os.path.dirname(release_path), exist_ok=True)
                with open(release_path, 'wb') as release_file:
                    release.dump(release_file)
                release_metadata = PublishedMetadata(
                    relative_path=release_path,
                    publication=publication,
                    file=File(open(release_path, 'rb')),
                )
                release_metadata.save()

            if publisher.structured:
                raise NotImplementedError(
                    "Structured publishing is not yet implemented.")

    log.info(_('Publication: {publication} created').format(
        publication=publication.pk))
