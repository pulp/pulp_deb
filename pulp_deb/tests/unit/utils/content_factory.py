import uuid

from pulpcore.plugin.models import Content

from pulp_deb.app.models import (
    AptRepository,
    Package,
    PackageReleaseComponent,
    Release,
    ReleaseArchitecture,
    ReleaseComponent,
)


class RepoContentFactory:
    """Accumulates content added inside a `with` block into one RepositoryVersion on exit.

    Each `add_*` method creates a single content unit, adds it to this factory's pending set,
    and returns whatever identifies it (its pk). Callers loop over `add_*` themselves for
    "many" - this class only tracks what to put in the repo version.
    """

    def __init__(self, repo_name=None):
        self._repo_name = repo_name or str(uuid.uuid4())
        self._content_pks = []
        self._repo = None
        self.version = None

    def __enter__(self):
        self._repo, _ = AptRepository.objects.get_or_create(name=self._repo_name)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            with self._repo.new_version() as version:
                version.add_content(Content.objects.filter(pk__in=self._content_pks))
            self.version = self._repo.latest_version()

    def get_repository(self):
        return self._repo

    def add_packages(self, names: list[str], *, architecture="amd64") -> list:
        """Create one Package per name. Returns their pks, in the same order as `names`."""
        pks = []
        for name in names:
            pk = Package.objects.create(
                package=name,
                version="1.0",
                architecture=architecture,
                maintainer="",
                description="",
                sha256=uuid.uuid4().hex,
            ).pk
            pks.append(pk)
        self._content_pks.extend(pks)
        return pks

    def add_release(self, distribution):
        release, _ = Release.objects.get_or_create(distribution=distribution)
        self._content_pks.append(release.pk)
        return release.pk

    def add_release_architecture(self, distribution, architecture):
        release_architecture, _ = ReleaseArchitecture.objects.get_or_create(
            distribution=distribution, architecture=architecture
        )
        self._content_pks.append(release_architecture.pk)
        return release_architecture.pk

    def add_release_component(self, distribution, component):
        release_component, _ = ReleaseComponent.objects.get_or_create(
            distribution=distribution, component=component
        )
        self._content_pks.append(release_component.pk)
        return release_component.pk

    def add_package_release_component(self, package_pk, release_component_pk):
        prc, _ = PackageReleaseComponent.objects.get_or_create(
            package_id=package_pk, release_component_id=release_component_pk
        )
        self._content_pks.append(prc.pk)
        return prc.pk
