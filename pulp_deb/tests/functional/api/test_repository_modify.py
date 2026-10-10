from uuid import uuid4

import pytest

from pulpcore.client.pulp_deb.exceptions import ApiException
from pulpcore.tests.functional.utils import PulpTaskError

from pulp_deb.app.constants import (
    DEFAULT_COMPONENT,
    DEFAULT_DISTRIBUTION,
)
from pulp_deb.tests.functional.constants import DEB_PACKAGE_RELPATH
from pulp_deb.tests.functional.utils import get_local_package_absolute_path


def _modify_with_package(repository, package, deb_modify_repository, **kwargs):
    deb_modify_repository(
        repository,
        {"add_content_units": [package.pulp_href], **kwargs},
    )


def test_modify_package_creates_structure_without_release(
    apt_package_api,
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
    distribution = str(uuid4())
    component = str(uuid4())

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


def test_modify_architecture_all_package_creates_no_release_architecture(
    apt_package_release_components_api,
    apt_release_architecture_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    package = deb_package_factory(
        file=str(
            get_local_package_absolute_path(
                "eir_1.0_all.deb", relative_path="data/debian-mixed/pool/asgard/e/eir/"
            )
        )
    )

    _modify_with_package(
        repository,
        package,
        deb_modify_repository,
        distribution=str(uuid4()),
        component=str(uuid4()),
    )
    repository = deb_get_repository_by_href(repository.pulp_href)

    filters = {"repository_version": repository.latest_version_href}
    assert apt_release_architecture_api.list(**filters).count == 0
    assert apt_package_release_components_api.list(**filters).count == 1


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


def test_remove_package_from_all_distributions_and_components(
    apt_package_api,
    apt_package_release_components_api,
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    removed_package = deb_package_factory(
        file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH))
    )
    kept_package = deb_package_factory(
        file=str(
            get_local_package_absolute_path("odin_1.0_ppc64.deb", "data/debian/pool/asgard/o/odin/")
        )
    )
    distributions = [str(uuid4()), str(uuid4())]
    components = ["main", str(uuid4())]
    for distribution in distributions:
        deb_release_factory(
            codename=distribution,
            suite=distribution,
            distribution=distribution,
            repository=repository.pulp_href,
        )
    for distribution, component in (
        (distributions[0], components[0]),
        (distributions[0], components[1]),
        (distributions[1], components[0]),
    ):
        _modify_with_package(
            repository,
            removed_package,
            deb_modify_repository,
            distribution=distribution,
            component=component,
        )
    _modify_with_package(
        repository,
        kept_package,
        deb_modify_repository,
        distribution=distributions[1],
        component=components[1],
    )

    deb_modify_repository(
        repository,
        {
            "remove_content_units": [removed_package.pulp_href],
            "distribution": "*",
            "component": "*",
        },
    )
    repository = deb_get_repository_by_href(repository.pulp_href)

    filters = {"repository_version": repository.latest_version_href}
    assert [item.pulp_href for item in apt_package_api.list(**filters).results] == [
        kept_package.pulp_href
    ]
    assert [
        item.package for item in apt_package_release_components_api.list(**filters).results
    ] == [kept_package.pulp_href]
    assert apt_release_component_api.list(**filters).count == 4


def test_add_and_remove_packages_in_same_request(
    apt_package_api,
    apt_package_release_components_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    removed_package = deb_package_factory(
        file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH))
    )
    added_package = deb_package_factory(
        file=str(
            get_local_package_absolute_path("odin_1.0_ppc64.deb", "data/debian/pool/asgard/o/odin/")
        )
    )
    distribution = str(uuid4())
    component = str(uuid4())
    _modify_with_package(
        repository,
        removed_package,
        deb_modify_repository,
        distribution=distribution,
        component=component,
    )

    deb_modify_repository(
        repository,
        {
            "add_content_units": [added_package.pulp_href],
            "remove_content_units": [removed_package.pulp_href],
            "distribution": distribution,
            "component": component,
        },
    )
    repository = deb_get_repository_by_href(repository.pulp_href)

    filters = {"repository_version": repository.latest_version_href}
    packages = apt_package_api.list(**filters)
    package_components = apt_package_release_components_api.list(**filters)
    assert [package.pulp_href for package in packages.results] == [added_package.pulp_href]
    assert [relationship.package for relationship in package_components.results] == [
        added_package.pulp_href
    ]


def test_remove_all_packages_from_component(
    apt_package_api,
    apt_package_release_components_api,
    apt_release_api,
    apt_release_architecture_api,
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    distribution = str(uuid4())
    components = ["main", str(uuid4())]
    packages = [
        deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH))),
        deb_package_factory(
            file=str(
                get_local_package_absolute_path(
                    "odin_1.0_ppc64.deb", "data/debian/pool/asgard/o/odin/"
                )
            )
        ),
    ]
    deb_release_factory(
        codename=distribution,
        suite=distribution,
        distribution=distribution,
        repository=repository.pulp_href,
    )
    for package, component in zip(packages, components):
        _modify_with_package(
            repository,
            package,
            deb_modify_repository,
            distribution=distribution,
            component=component,
        )

    deb_modify_repository(
        repository,
        {
            "remove_content_units": ["*"],
            "distribution": distribution,
            "component": components[0],
        },
    )
    repository = deb_get_repository_by_href(repository.pulp_href)

    filters = {"repository_version": repository.latest_version_href}
    assert [item.pulp_href for item in apt_package_api.list(**filters).results] == [
        packages[1].pulp_href
    ]
    assert apt_package_release_components_api.list(**filters).count == 1
    # Only the emptied component goes away; the rest of the release is still in use.
    assert [item.component for item in apt_release_component_api.list(**filters).results] == [
        components[1]
    ]
    assert apt_release_api.list(**filters).count == 1
    assert apt_release_architecture_api.list(**filters).count == 1


def test_remove_all_packages_from_distribution(
    apt_package_api,
    apt_package_release_components_api,
    apt_release_api,
    apt_release_architecture_api,
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_release_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    distributions = [str(uuid4()), str(uuid4())]
    packages = [
        deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH))),
        deb_package_factory(
            file=str(
                get_local_package_absolute_path(
                    "odin_1.0_ppc64.deb", "data/debian/pool/asgard/o/odin/"
                )
            )
        ),
    ]
    for package, distribution in zip(packages, distributions):
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
            component="main",
        )

    deb_modify_repository(
        repository,
        {
            "remove_content_units": ["*"],
            "distribution": distributions[0],
            "component": "*",
        },
    )
    repository = deb_get_repository_by_href(repository.pulp_href)

    filters = {"repository_version": repository.latest_version_href}
    assert [item.pulp_href for item in apt_package_api.list(**filters).results] == [
        packages[1].pulp_href
    ]
    assert apt_package_release_components_api.list(**filters).count == 1
    # Emptying a distribution takes its whole release structure with it.
    assert [item.distribution for item in apt_release_api.list(**filters).results] == [
        distributions[1]
    ]
    assert [item.distribution for item in apt_release_component_api.list(**filters).results] == [
        distributions[1]
    ]
    assert [item.distribution for item in apt_release_architecture_api.list(**filters).results] == [
        distributions[1]
    ]


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

    deb_modify_repository(
        repository,
        {
            "remove_content_units": ["*"],
            "distribution": "*",
            "component": "*",
        },
    )
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
    deb_repository_factory,
):
    """A request without a distribution is scoped to the default one."""
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    component = str(uuid4())

    _modify_with_package(repository, package, deb_modify_repository, component=component)
    repository = deb_get_repository_by_href(repository.pulp_href)

    components = apt_release_component_api.list(repository_version=repository.latest_version_href)
    assert [(item.distribution, item.component) for item in components.results] == [
        (DEFAULT_DISTRIBUTION, component)
    ]


def test_modify_distribution_only_uses_default_component(
    apt_release_component_api,
    deb_get_repository_by_href,
    deb_modify_repository,
    deb_package_factory,
    deb_repository_factory,
):
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))
    distribution = str(uuid4())

    _modify_with_package(repository, package, deb_modify_repository, distribution=distribution)
    repository = deb_get_repository_by_href(repository.pulp_href)

    components = apt_release_component_api.list(repository_version=repository.latest_version_href)
    assert [(item.distribution, item.component) for item in components.results] == [
        (distribution, DEFAULT_COMPONENT)
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


@pytest.mark.parametrize("distribution,component", [("*", str(uuid4())), (str(uuid4()), "*")])
def test_add_package_to_wildcard_scope_fails(
    deb_modify_repository,
    deb_package_factory,
    deb_repository_factory,
    distribution,
    component,
):
    """'*' is a removal selector, so it must not be turned into a name by an addition."""
    repository = deb_repository_factory()
    package = deb_package_factory(file=str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)))

    with pytest.raises(ApiException) as exception:
        _modify_with_package(
            repository,
            package,
            deb_modify_repository,
            distribution=distribution,
            component=component,
        )

    assert exception.value.status == 400
    assert "does not accept the special value '*'" in exception.value.body


def test_create_release_with_wildcard_name_fails(deb_release_factory):
    codename = str(uuid4())

    with pytest.raises(ApiException) as exception:
        deb_release_factory(codename=codename, suite=codename, distribution="*")

    assert exception.value.status == 400
    assert "does not accept the special value '*'" in exception.value.body


def test_create_release_with_wildcard_component_fails(deb_release_factory):
    codename = str(uuid4())

    with pytest.raises(ApiException) as exception:
        deb_release_factory(
            codename=codename, suite=codename, distribution=codename, components=["*"]
        )

    assert exception.value.status == 400
    assert "does not accept the special value '*'" in exception.value.body


@pytest.mark.parametrize("distribution,component", [("*", str(uuid4())), (str(uuid4()), "*")])
def test_create_release_component_with_wildcard_name_fails(
    deb_release_component_factory,
    distribution,
    component,
):
    with pytest.raises(ApiException) as exception:
        deb_release_component_factory(component=component, distribution=distribution)

    assert exception.value.status == 400
    assert "does not accept the special value '*'" in exception.value.body
