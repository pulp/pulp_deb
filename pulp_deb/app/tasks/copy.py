from gettext import gettext

from django.db import transaction
from django.db.models import Q

from pulpcore.plugin.models import Content, RepositoryVersion

from pulp_deb.app.models import (
    AptRepository,
    Package,
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
)

import logging

log = logging.getLogger(__name__)


def find_structured_publish_content(content, src_repo_version):
    """
    Finds the content for structured publish from packages to be copied and returns it all together.

    Args:
        content (iterable): Content for structured publish
        src_repo_version (pulpcore.models.RepositoryVersion): Source repo version

    Returns: Queryset of Content objects that extends intial set of content for structured publish
    """
    # Content in the source repository version
    package_release_component_ids = src_repo_version.content.filter(
        pulp_type=PackageReleaseComponent.get_pulp_type()
    ).only("pk")
    architecture_ids = src_repo_version.content.filter(
        pulp_type=ReleaseArchitecture.get_pulp_type()
    ).only("pk")
    package_release_components = PackageReleaseComponent.objects.filter(
        pk__in=package_release_component_ids
    )

    structured_publish_content = set()

    # Packages to be copied
    packages = Package.objects.filter(pk__in=content)
    structured_publish_content.update(packages.values_list("pk", flat=True))

    if len(content) != len(packages):
        message = gettext(
            "Additional data with packages is provided. Removing from the content list."
        )
        log.warning(message)

    # List of all architectures
    architectures = ReleaseArchitecture.objects.filter(pk__in=architecture_ids).values_list(
        "pk", flat=True
    )
    structured_publish_content.update(architectures)

    # Package release components, release components, release to be copied based on packages
    for pckg in package_release_components.iterator():
        if pckg.package in packages:
            structured_publish_content.update([pckg.pk, pckg.release_component.pk])
            release = Release.objects.filter(
                pk__in=src_repo_version.content, distribution=pckg.release_component.distribution
            ).first()
            if release:
                structured_publish_content.update([release.pk])

    return Content.objects.filter(pk__in=structured_publish_content)


@transaction.atomic
def copy_content(config, structured, dependency_solving):
    """
    Copy content from one repo to another.

    Args:
        source_repo_version_pk: repository version primary key to copy units from
        dest_repo_pk: repository primary key to copy units into
        criteria: a dict that maps type to a list of criteria to filter content by. Note that this
            criteria MUST be validated before being passed to this task.
        content_pks: a list of content pks to copy from source to destination
    """

    def process_entry(entry):
        source_repo_version = RepositoryVersion.objects.get(pk=entry["source_repo_version"])
        dest_repo = AptRepository.objects.get(pk=entry["dest_repo"])

        dest_version_provided = bool(entry.get("dest_base_version"))
        if dest_version_provided:
            dest_repo_version = RepositoryVersion.objects.get(pk=entry["dest_base_version"])
        else:
            dest_repo_version = dest_repo.latest_version()

        if entry.get("content") is not None:
            content_filter = Q(pk__in=entry.get("content"))
        else:
            content_filter = Q()

        log.info(gettext("Copying: {copy} created").format(copy=content_filter))

        return (
            source_repo_version,
            dest_repo_version,
            dest_repo,
            content_filter,
            dest_version_provided,
        )

    if not dependency_solving:
        # No Dependency Solving Branch
        # ============================
        for entry in config:
            (
                source_repo_version,
                dest_repo_version,
                dest_repo,
                content_filter,
                dest_version_provided,
            ) = process_entry(entry)

            content_to_copy = source_repo_version.content.filter(content_filter)
            if structured:
                content_to_copy = find_structured_publish_content(
                    content_to_copy, source_repo_version
                )

            base_version = dest_repo_version if dest_version_provided else None

            with dest_repo.new_version(base_version=base_version) as new_version:
                new_version.add_content(content_to_copy)
    else:
        raise NotImplementedError("Advanced copy with dependency solving is not yet implemented.")
