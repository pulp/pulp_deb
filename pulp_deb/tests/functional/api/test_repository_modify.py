from uuid import uuid4

import pytest

from pulpcore.client.pulp_deb.exceptions import ApiException
from pulpcore.tests.functional.utils import PulpTaskError

from pulp_deb.app.constants import (
    PACKAGE_UPLOAD_DEFAULT_COMPONENT,
    PACKAGE_UPLOAD_DEFAULT_DISTRIBUTION,
)
from pulp_deb.tests.functional.constants import DEB_PACKAGE_RELPATH
from pulp_deb.tests.functional.utils import get_local_package_absolute_path


def _modify_with_package(repository, package, deb_modify_repository, **kwargs):
    deb_modify_repository(
        repository,
        {"add_content_units": [package.pulp_href], **kwargs},
    )


def test_modify_package_creates_structure(
    apt_package_api,
    apt_package_release_components_api,
    apt_release_architecture_api,
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    distribution = str(uuid4())
    component = str(uuid4())

    with pytest.raises(ApiException, match="This distribution has no Release"):
        _modify_with_package(
            repository,
            package,
            deb_modify_repository,
            distribution=distribution,
            component=component,
        )

    deb_release_factory(
        codename=distribution,
        suite=distribution,
        distribution=distribution,
        repository=repository.pulp_href,
    )
    _modify_with_package(
        repository,
        package,
        deb_modify_repository,
        distribution=distribution,
        component=component,
    )
    repository = deb_get_repository_by_href(repository.pulp_href)

    components = apt_release_component_api.list(repository_version=repository.latest_version_href)
    architectures = apt_release_architecture_api.list(
        repository_version=repository.latest_version_href
    )
    package_components = apt_package_release_components_api.list(
        repository_version=repository.latest_version_href
    )
    packages = apt_package_api.list(repository_version=repository.latest_version_href)
    assert [(item.distribution, item.component) for item in components.results] == [
        (distribution, component)
    ]
    assert [(item.distribution, item.architecture) for item in architectures.results] == [
        (distribution, package.architecture)
    ]
    assert package_components.results[0].package == package.pulp_href
    assert package_components.results[0].release_component == components.results[0].pulp_href
    assert [item.pulp_href for item in packages.results] == [package.pulp_href]


def test_modify_package_without_structure_fields_only_adds_package(
    apt_package_release_components_api,
    apt_release_architecture_api,
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))

    _modify_with_package(repository, package, deb_modify_repository)
    repository = deb_get_repository_by_href(repository.pulp_href)

    filters = {"repository_version": repository.latest_version_href}
    assert apt_release_component_api.list(**filters).count == 0
    assert apt_release_architecture_api.list(**filters).count == 0
    assert apt_package_release_components_api.list(**filters).count == 0


def test_modify_packages_reuses_structure(
    apt_package_release_components_api,
    apt_release_architecture_api,
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    distribution = str(uuid4())
    component = str(uuid4())

    deb_release_factory(
        codename=distribution,
        suite=distribution,
        distribution=distribution,
        repository=repository.pulp_href,
    )
    for _ in range(2):
        _modify_with_package(
            repository,
            package,
            deb_modify_repository,
            distribution=distribution,
            component=component,
        )
    repository = deb_get_repository_by_href(repository.pulp_href)

    filters = {"repository_version": repository.latest_version_href}
    assert apt_release_component_api.list(**filters).count == 1
    assert apt_release_architecture_api.list(**filters).count == 1
    assert apt_package_release_components_api.list(**filters).count == 1


def test_remove_package_from_component(
    apt_package_api,
    apt_package_release_components_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    distribution = str(uuid4())
    components = [str(uuid4()), str(uuid4())]
    deb_release_factory(
        codename=distribution,
        suite=distribution,
        distribution=distribution,
        repository=repository.pulp_href,
    )
    for component in components:
        _modify_with_package(
            repository,
            package,
            deb_modify_repository,
            distribution=distribution,
            component=component,
        )

    for expected_count, component in zip((1, 0), components):
        deb_modify_repository(
            repository,
            {
                "remove_content_units": [package.pulp_href],
                "distribution": distribution,
                "component": component,
            },
        )
        repository = deb_get_repository_by_href(repository.pulp_href)
        filters = {"repository_version": repository.latest_version_href}
        assert apt_package_api.list(**filters).count == expected_count
        assert apt_package_release_components_api.list(**filters).count == expected_count


def test_remove_all_content_units(
    apt_package_api,
    apt_package_release_components_api,
    apt_release_architecture_api,
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    distribution = str(uuid4())
    deb_release_factory(
        codename=distribution,
        suite=distribution,
        distribution=distribution,
        repository=repository.pulp_href,
    )
    _modify_with_package(
        repository,
        package,
        deb_modify_repository,
        distribution=distribution,
        component=str(uuid4()),
    )

    deb_modify_repository(repository, {"remove_content_units": ["*"]})
    repository = deb_get_repository_by_href(repository.pulp_href)

    filters = {"repository_version": repository.latest_version_href}
    assert apt_package_api.list(**filters).count == 0
    assert apt_package_release_components_api.list(**filters).count == 0
    assert apt_release_component_api.list(**filters).count == 0
    assert apt_release_architecture_api.list(**filters).count == 0


def test_remove_package_outside_of_component_is_kept(
    apt_package_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    """A package without a relationship in the given component is not removed."""
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    distribution = str(uuid4())
    deb_release_factory(
        codename=distribution,
        suite=distribution,
        distribution=distribution,
        repository=repository.pulp_href,
    )
    _modify_with_package(repository, package, deb_modify_repository)

    deb_modify_repository(
        repository,
        {
            "remove_content_units": [package.pulp_href],
            "distribution": distribution,
            "component": str(uuid4()),
        },
    )
    repository = deb_get_repository_by_href(repository.pulp_href)

    assert apt_package_api.list(repository_version=repository.latest_version_href).count == 1


def test_modify_component_only_uses_default_distribution(
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    """A request without a distribution is scoped to (and validated against) the default one."""
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    component = str(uuid4())

    with pytest.raises(ApiException, match="This distribution has no Release"):
        _modify_with_package(repository, package, deb_modify_repository, component=component)

    deb_release_factory(
        codename=str(uuid4()),
        suite=str(uuid4()),
        distribution=PACKAGE_UPLOAD_DEFAULT_DISTRIBUTION,
        repository=repository.pulp_href,
    )
    _modify_with_package(repository, package, deb_modify_repository, component=component)
    repository = deb_get_repository_by_href(repository.pulp_href)

    components = apt_release_component_api.list(repository_version=repository.latest_version_href)
    assert [(item.distribution, item.component) for item in components.results] == [
        (PACKAGE_UPLOAD_DEFAULT_DISTRIBUTION, component)
    ]


def test_modify_distribution_only_uses_default_component(
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    distribution = str(uuid4())
    deb_release_factory(
        codename=distribution,
        suite=distribution,
        distribution=distribution,
        repository=repository.pulp_href,
    )

    _modify_with_package(repository, package, deb_modify_repository, distribution=distribution)
    repository = deb_get_repository_by_href(repository.pulp_href)

    components = apt_release_component_api.list(repository_version=repository.latest_version_href)
    assert [(item.distribution, item.component) for item in components.results] == [
        (distribution, PACKAGE_UPLOAD_DEFAULT_COMPONENT)
    ]


def test_modify_accepts_release_added_in_same_request(
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    """The Release backing the distribution may be added by the very same request."""
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    distribution = str(uuid4())
    component = str(uuid4())
    release = deb_release_factory(
        codename=distribution, suite=distribution, distribution=distribution
    )

    deb_modify_repository(
        repository,
        {
            "add_content_units": [release.pulp_href, package.pulp_href],
            "distribution": distribution,
            "component": component,
        },
    )
    repository = deb_get_repository_by_href(repository.pulp_href)

    components = apt_release_component_api.list(repository_version=repository.latest_version_href)
    assert [(item.distribution, item.component) for item in components.results] == [
        (distribution, component)
    ]


def test_modify_forwards_overwrite(
    deb_modify_repository,
    deb_release_factory,
    deb_repository_factory,
):
    """overwrite=False must reach the task and reject conflicting content."""
    repository = deb_repository_factory()
    distribution = str(uuid4())
    deb_release_factory(
        codename=str(uuid4()),
        suite=str(uuid4()),
        distribution=distribution,
        repository=repository.pulp_href,
    )
    conflicting_release = deb_release_factory(
        codename=str(uuid4()), suite=str(uuid4()), distribution=distribution
    )

    with pytest.raises(PulpTaskError) as exception:
        deb_modify_repository(
            repository,
            {"add_content_units": [conflicting_release.pulp_href], "overwrite": False},
        )
    assert "Content overwrite rejected" in exception.value.task.error["description"]
