import logging
from gettext import gettext as _

from django.db import transaction

from pulpcore.plugin.exceptions import FeatureNotImplementedError
from pulpcore.plugin.models import RepositoryVersion

from pulp_deb.app.models import (
    AptRepository,
    Package,
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
)
from pulp_deb.app.sql_utils import get_content_in_repoversion, safe_in

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
    package_pks = list(package_qs.values_list("pk", flat=True))

    # PackageReleaseComponents:
    prc_qs = PackageReleaseComponent.objects.filter(
        safe_in("package_id", package_pks),
        pk__in=get_content_in_repoversion(source_repo_version),
    )

    # ReleaseComponents:
    release_components = prc_qs.values_list(
        "release_component_id", "release_component__distribution"
    ).distinct()
    release_component_ids = set()
    distributions = set()
    for release_component_id, distribution in release_components:
        release_component_ids.add(release_component_id)
        distributions.add(distribution)

    release_component_content_qs = (
        get_content_in_repoversion(source_repo_version)
        .filter(safe_in("pk", release_component_ids))
        .only("pk")
    )

    # ReleaseArchitectures:
    architectures = list(package_qs.values_list("architecture", flat=True).distinct())
    architecture_qs = ReleaseArchitecture.objects.filter(
        safe_in("architecture", architectures), safe_in("distribution", distributions)
    ).only("pk")

    # Releases:
    release_qs = Release.objects.filter(safe_in("distribution", distributions)).only("pk")

    combined_content_qs = content.only("pk").union(
        prc_qs.only("pk"), release_component_content_qs, architecture_qs, release_qs
    )

    return get_content_in_repoversion(source_repo_version).filter(pk__in=combined_content_qs)


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
        content_pks = entry.get("content")

        log.debug(_("Copying: {copy} created").format(copy=content_pks))

        return (
            source_repo_version,
            dest_repo,
            dest_base_version,
            content_pks,
        )

    if dependency_solving:
        raise FeatureNotImplementedError(
            "Advanced copy with dependency solving is not yet implemented."
        )

    for entry in config:
        (
            source_repo_version,
            dest_repo,
            dest_base_version,
            content_pks,
        ) = process_entry(entry)

        content_in_repo = get_content_in_repoversion(source_repo_version)
        if content_pks is None:
            content_to_copy = content_in_repo
        else:
            content_to_copy = content_in_repo.filter(safe_in("pk", content_pks))

        if structured:
            content_to_copy = find_structured_publish_content(content_to_copy, source_repo_version)

        with dest_repo.new_version(base_version=dest_base_version) as new_version:
            new_version.add_content(content_to_copy)
