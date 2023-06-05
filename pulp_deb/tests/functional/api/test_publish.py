from random import choice
import pytest
import requests

from pulp_smash import config
from pulp_smash.pulp3.utils import (
    download_content_unit,
    get_content,
    get_versions,
    gen_distribution,
    modify_repo,
)

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_DISTRIBUTIONS,
    DEB_GENERIC_CONTENT_NAME,
    DEB_PACKAGE_NAME,
)
from pulp_deb.tests.functional.utils import deb_distribution_api

from pulpcore.client.pulp_deb.exceptions import ApiException
from pulpcore.client.pulp_deb import (
    DebAptPublication,
    DebVerbatimPublication,
)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "testcase_number, publication_api, Publication",
    [
        (0, "apt_publication_api", DebAptPublication),
        (1, "apt_publication_api", DebAptPublication),
        (2, "apt_publication_api", DebAptPublication),
        (3, "apt_publication_api", DebAptPublication),
        (4, "apt_verbatim_publication_api", DebVerbatimPublication),
    ],
)
def test_publish_any_repo_version(
    deb_remote_factory,
    deb_repository_factory,
    deb_sync_repository,
    gen_object_with_cleanup,
    publish_parameters,
    publication_api,
    Publication,
    request,
    testcase_number,
):
    """Test whether a particular repository version can be published.

    The following cases are tested:

    * `Publish a simple repository version.`_
    * `Publish a structured repository version.`_
    * `Publish a simple and structured repository version.`_
    * `Publish a simple, structured and signed repository version.`_
    * `Publish a repository version verbatim.`
    """
    publication_api = request.getfixturevalue(publication_api)
    cfg = config.get_config()

    # Create a repository with at least two repository versions
    remote = deb_remote_factory(distributions=DEB_FIXTURE_DISTRIBUTIONS)
    repo = deb_repository_factory()
    deb_sync_repository(remote, repo)
    for deb_generic_content in get_content(repo.to_dict())[DEB_GENERIC_CONTENT_NAME]:
        modify_repo(cfg, repo.to_dict(), remove_units=[deb_generic_content])
    for deb_package in get_content(repo.to_dict())[DEB_PACKAGE_NAME]:
        modify_repo(cfg, repo.to_dict(), remove_units=[deb_package])
    version_hrefs = tuple(ver["pulp_href"] for ver in get_versions(repo.to_dict()))
    non_latest = choice(version_hrefs[:-1])

    # Create a publication supplying the latest `repository_version`
    publish_data = Publication(repository=repo.pulp_href, **publish_parameters[testcase_number])
    first_publish_href = gen_object_with_cleanup(publication_api, publish_data).pulp_href
    publication = publication_api.read(first_publish_href)

    # Verify that the publication `repository_version` points to the latest repository version
    assert publication.repository_version == version_hrefs[-1]

    # Create a publication by supplying the non-latest `repository_version`
    publish_data = Publication(repository_version=non_latest, **publish_parameters[testcase_number])
    second_publish_href = gen_object_with_cleanup(publication_api, publish_data).pulp_href
    publication = publication_api.read(second_publish_href)

    # Verify that the publication `repository_version` points to the supplied repository version
    assert publication.repository_version == non_latest

    # Verify publishing two different `repository_version` at the same time raises an exception
    with pytest.raises(ApiException) as exc:
        body = {"repository": repo.pulp_href, "repository_version": non_latest}
        gen_object_with_cleanup(publication_api, body)
    assert exc.value.status == 400

    # Because the cleanup of the publications happens after we try to delete
    # the signing service in the `deb_signing_service_factory` fixture we need to
    # delete both publications explicitly here. Otherwise the signing service
    # deletion will result in a `django.db.models.deletion.ProtectedError`.
    publication_api.delete(first_publish_href)
    publication_api.delete(second_publish_href)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "set_on,expect_signed",
    [
        ("repo", True),
        ("release", True),
        ("publication", True),
        ("nothing", False),
    ],
)
def test_publish_signing_services(
    deb_remote_factory,
    deb_repository_factory,
    deb_sync_repository,
    gen_object_with_cleanup,
    deb_signing_service_factory,
    set_on,
    expect_signed,
    request,
):
    """Test whether a signing service preferences are honored.

    The following cases are tested:

    * `Publish where a SigningService is set on the Repo.`_
    * `Publish where a SigningService is set on a Release.`_
    * `Publish where a SigningService is set on a Publication.`_
    """
    publication_api = request.getfixturevalue("apt_publication_api")
    repository_api = request.getfixturevalue("apt_repository_api")
    cfg = config.get_config()

    # Create a repository with at least two dists
    signing_service = deb_signing_service_factory
    remote = deb_remote_factory(distributions=DEB_FIXTURE_DISTRIBUTIONS)
    distro = DEB_FIXTURE_DISTRIBUTIONS.split()[0]
    repo_options = {}
    publish_options = {"simple": True, "structured": True}
    if set_on == "repo":
        repo_options["signing_service"] = signing_service.pulp_href
    elif set_on == "release":
        repo_options["signing_service_release_overrides"] = {distro: signing_service.pulp_href}
    elif set_on == "publication":
        publish_options["signing_service"] = signing_service.pulp_href

    repo = deb_repository_factory(**repo_options)
    deb_sync_repository(remote, repo)

    # Create a publication supplying the latest `repository_version`
    publish_data = DebAptPublication(repository=repo.pulp_href, **publish_options)
    publication_href = gen_object_with_cleanup(publication_api, publish_data).pulp_href

    # Create a distribution:
    body = gen_distribution()
    body["publication"] = publication_href
    distribution = gen_object_with_cleanup(deb_distribution_api, body)

    # Check that the expected InRelease file is there:
    succeeded = False
    try:
        download_content_unit(cfg, distribution.to_dict(), "dists/ragnarok/InRelease")
        succeeded = True
    except requests.exceptions.HTTPError:
        pass

    assert expect_signed == succeeded

    # Because the cleanup of the publications happens after we try to delete
    # the signing service in the `deb_signing_service_factory` fixture we need to
    # delete the publication explicitly here. Otherwise the signing service
    # deletion will result in a `django.db.models.deletion.ProtectedError`.
    publication_api.delete(publication_href)
    repository_api.delete(repo.pulp_href)


@pytest.fixture
def publish_parameters(deb_signing_service_factory):
    """Fixture for parameters for the publish test."""
    params = [
        {"simple": True},
        {"structured": True},
        {"simple": True, "structured": True},
        {
            "simple": True,
            "structured": True,
            "signing_service": deb_signing_service_factory.pulp_href,
        },
        {},
    ]
    return params
