from pulpcore.plugin import tasking
from pulpcore.plugin.models import CreatedResource

from pulp_deb.app.models import (
    ReleaseComponent,
    Package,
    PackageReleaseComponent,
)


def add_and_remove(
    repository_pk,
    add_content_units,
    remove_content_units,
    base_version_pk=None,
    distribution=None,
    component=None,
):
    # TODO: handle source packages

    if distribution and component:
        relcomp = ReleaseComponent.objects.get(distribution=distribution, component=component)

        if add_content_units:
            for package in Package.objects.filter(pk__in=add_content_units):
                prc, created = PackageReleaseComponent.objects.get_or_create(
                    release_component=relcomp, package=package
                )
                if created:
                    CreatedResource(content_object=prc).save()
                add_content_units.append(prc.pk)

        if remove_content_units:
            # just remove the PRC with the package and not the architecture
            for package in Package.objects.filter(pk__in=remove_content_units):
                if prc := PackageReleaseComponent.objects.filter(
                    release_component=relcomp, package=package
                ).first():
                    remove_content_units.append(prc.pk)

                # TODO: check the other releases and if the package belongs to one, don't remove it
                # from the repo

    tasking.add_and_remove(repository_pk, add_content_units, remove_content_units)
