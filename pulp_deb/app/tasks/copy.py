from django.db import transaction
from django.db.models import Q

from pulpcore.plugin.models import RepositoryVersion
from pulpcore.plugin.util import get_domain_pk

from pulp_deb.app.models import (
    AptRepository,
    Package,
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
)

import logging
from gettext import gettext as _

log = logging.getLogger(__name__)


def find_structured_publish_content(content, source_repo_version):
    """
    Finds the content for structured publish from packages to be copied and returns it all together.

    Args:
        content (iterable): Content for structured publish
        src_repo_version (pulpcore.models.RepositoryVersion): Source repo version

    Returns: Queryset of Content objects that extends intial set of content for structured publish
    """
    # Packages:
    package_content_qs = content.filter(pulp_type=Package.get_pulp_type()).only("pk")
    package_qs = Package.objects.filter(pk__in=package_content_qs)

    # PackageReleaseComponents:
    package_prc_qs = PackageReleaseComponent.objects.filter(package__in=package_qs.only("pk")).only(
        "pk"
    )
    prc_content_qs = source_repo_version.content.filter(pk__in=package_prc_qs)
    prc_qs = PackageReleaseComponent.objects.filter(pk__in=prc_content_qs.only("pk"))

    # ReleaseComponents:
    release_component_ids = set()
    distributions = set()
    for prc in prc_qs.select_related("release_component").iterator():
        release_component_ids.add(prc.release_component.pk)
        distributions.add(prc.release_component.distribution)

    release_component_content_qs = source_repo_version.content.filter(
        pk__in=release_component_ids
    ).only("pk")

    # ReleaseArchitectures:
    architectures = list(package_qs.values_list("architecture", flat=True).distinct())
    architecture_qs = ReleaseArchitecture.objects.filter(
        architecture__in=architectures, distribution__in=distributions
    ).only("pk")

    # Releases:
    release_qs = Release.objects.filter(distribution__in=distributions).only("pk")

    combined_content_qs = content.only("pk").union(
        prc_qs.only("pk"), release_component_content_qs, architecture_qs, release_qs
    )

    return source_repo_version.content.filter(pk__in=combined_content_qs)


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
        dest_base_version = (
            RepositoryVersion.objects.get(pk=entry["dest_base_version"])
            if bool(entry.get("dest_base_version"))
            else None
        )

        if entry.get("content") is not None:
            content_filter = Q(pk__in=entry.get("content"))
        else:
            content_filter = Q()

        content_filter &= Q(pulp_domain=get_domain_pk())

        log.info(_("Copying: {copy} created").format(copy=content_filter))

        return (
            source_repo_version,
            dest_repo,
            dest_base_version,
            content_filter,
        )

    if dependency_solving:
        raise NotImplementedError("Advanced copy with dependency solving is not yet implemented.")

    for entry in config:
        (
            source_repo_version,
            dest_repo,
            dest_base_version,
            content_filter,
        ) = process_entry(entry)

        content_to_copy = source_repo_version.content.filter(content_filter)
        if structured:
            content_to_copy = find_structured_publish_content(content_to_copy, source_repo_version)

        with dest_repo.new_version(base_version=dest_base_version) as new_version:
            new_version.add_content(content_to_copy)
