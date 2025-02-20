"""Tests role-based access control."""

import pytest

from pulp_deb.tests.functional.constants import DEB_PACKAGE_RELPATH
from pulp_deb.tests.functional.utils import get_local_package_absolute_path

from pulpcore.client.pulp_deb.exceptions import ApiException


@pytest.mark.parallel
def test_rbac_repositories(apt_repository_api, deb_repository_factory, gen_user):
    """
    Test creation of a repository.
    """
    user_allowed = gen_user(
        model_roles=[
            "deb.aptrepository_creator",
            "deb.aptrepository_viewer",
        ]
    )
    user_denied = gen_user()

    with user_allowed:
        repo = deb_repository_factory()
        assert apt_repository_api.read(repo.pulp_href)

    with user_denied, pytest.raises(ApiException):
        deb_repository_factory()


@pytest.mark.parallel
def test_rbac_upload(deb_repository_factory, deb_package_factory, gen_user):
    """
    Test upload of a package.
    """
    user_allowed = gen_user(
        model_roles=[
            "deb.aptrepository_owner",
        ]
    )
    user_denied = gen_user()
    repo = deb_repository_factory()
    package_attrs = {
        "file": str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)),
        "relative_path": DEB_PACKAGE_RELPATH,
        "repository": repo.pulp_href,
    }

    with user_allowed:
        package = deb_package_factory(**package_attrs)
        assert package.pulp_created

    with user_denied, pytest.raises(ApiException):
        deb_package_factory(**package_attrs)


@pytest.mark.parallel
def test_rbac_publication(deb_publication_factory, deb_repository_factory, gen_user):
    """Test publication."""
    user_allowed = gen_user(
        model_roles=[
            "deb.aptpublication_creator",
            "deb.aptpublication_viewer",
            "deb.aptrepository_viewer",
        ]
    )
    user_denied = gen_user()
    repo = deb_repository_factory()

    with user_allowed:
        publication = deb_publication_factory(repo)
        assert publication.repository == repo.pulp_href

    with user_denied, pytest.raises(ApiException):
        deb_publication_factory(repo)


@pytest.mark.parallel
def test_rbac_verbatim_publication(
    deb_verbatim_publication_factory, deb_repository_factory, gen_user
):
    """Test verbatim publication."""
    user_allowed = gen_user(
        model_roles=[
            "deb.verbatimpublication_creator",
            "deb.verbatimpublication_viewer",
            "deb.aptrepository_viewer",
        ]
    )
    user_denied = gen_user()
    repo = deb_repository_factory()

    with user_allowed:
        verbatim_publication = deb_verbatim_publication_factory(repo)
        assert verbatim_publication.repository == repo.pulp_href

    with user_denied, pytest.raises(ApiException):
        deb_verbatim_publication_factory(repo)


@pytest.mark.parallel
def test_rbac_distribution(
    deb_distribution_factory, deb_publication_factory, deb_repository_factory, gen_user
):
    """Test distribution."""
    user_allowed = gen_user(
        model_roles=[
            "deb.aptdistribution_creator",
            "deb.aptdistribution_viewer",
            "deb.aptpublication_viewer",
        ]
    )
    user_denied = gen_user()
    repo = deb_repository_factory()
    publication = deb_publication_factory(repo)

    with user_allowed:
        distribution = deb_distribution_factory(publication)
        assert distribution.publication == publication.pulp_href

    with user_denied, pytest.raises(ApiException):
        deb_distribution_factory(publication)
