from random import choice
from debian import deb822
import os
import pytest

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_ALT_SINGLE_DIST,
    DEB_FIXTURE_COMPLEX_REPOSITORY_NAME,
    DEB_FIXTURE_DISTRIBUTIONS,
    DEB_FIXTURE_FLAT_REPOSITORY_NAME,
    DEB_FIXTURE_MISSING_ARCHITECTURE_REPOSITORY_NAME,
    DEB_FIXTURE_SINGLE_DIST,
    DEB_PACKAGE_INDEX_NAME,
    DEB_PACKAGE_NAME,
    DEB_PACKAGE_RELEASE_COMPONENT_NAME,
    DEB_PUBLICATION_ARGS_ALL,
    DEB_PUBLICATION_ARGS_ONLY_SIMPLE,
    DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
    DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED,
    DEB_PUBLISH_COMPLEX_DEBIAN_SECURITY,
    DEB_PUBLISH_COMPLEX_UBUNTU_BACKPORTS,
    DEB_PUBLISH_EMPTY_REPOSITORY,
    DEB_PUBLISH_FLAT_NESTED_SIMPLE,
    DEB_PUBLISH_FLAT_NESTED_STRUCTURED,
    DEB_PUBLISH_FLAT_NESTED_VERBATIM,
    DEB_PUBLISH_FLAT_SIMPLE,
    DEB_PUBLISH_FLAT_STRUCTURED,
    DEB_PUBLISH_FLAT_VERBATIM,
    DEB_PUBLISH_MISSING_ARCHITECTURE,
    DEB_RELEASE_COMPONENT_NAME,
    DEB_RELEASE_FILE_NAME,
    DEB_RELEASE_NAME,
)

from pulpcore.client.pulp_deb.exceptions import ApiException


@pytest.fixture
def create_publication_and_verify_repo_version(
    deb_init_and_sync, deb_modify_repository, deb_repository_get_versions, request
):
    def _create_publication_and_verify_repo_version(
        remote_args,
        publication_args={},
        repo_args={},
        remote_name=None,
        is_verbatim=False,
        is_modified=False,
    ):
        """Setup a publishing test by creating a publication, repository, remote and repo versions.

        :param remote_args: The parameters for creating the remote.
        :param publication_args: The parameters for creating the publication. Default: {}.
        :param repo_args: The parameters for creating the repository. Default: {}.
        :param remote_name: Alternate remote repository source. Default: None -> (/debian/).
        :param is_verbatim: Whether the verbatim publisher should be used: Default: False.
        :param is_modified: Whether multiple repository versions should be created. Default: False.
        :returns: A tuple containing the created publication, repository, remote
            and repository versions.
        """
        publication_factory = (
            request.getfixturevalue("deb_verbatim_publication_factory")
            if is_verbatim
            else request.getfixturevalue("deb_publication_factory")
        )
        repo, remote = deb_init_and_sync(
            url=remote_name, remote_args=remote_args, repo_args=repo_args
        )
        if is_modified:
            deb_modify_repository(repo, {"remove_content_units": ["*"]})
        version_hrefs = tuple(deb_repository_get_versions(repo.pulp_href))
        assert repo.latest_version_href
        publication = publication_factory(repo, **publication_args)
        assert publication.repository_version == version_hrefs[-1]
        return (publication, repo, remote, version_hrefs)

    return _create_publication_and_verify_repo_version


@pytest.fixture
def verify_publication_data(deb_get_content_types):
    def _verify_publication_data(publication, expected, is_nested=False):
        """Verifies the content data of a given publication with the given expected values.

        :param publication: The publication which needs verification.
        :param expected: The expected data that the publication should contain.
        :param is_nested: Whether the data is nested. Default: False.
        """
        release_type = "Release" if is_nested else "InRelease"
        release_file_folder = "release_file_folder_sync" if is_nested else "release_file_folder"
        package_index_paths = "package_index_paths_sync" if is_nested else "package_index_paths"

        repo = publication.to_dict()
        version_href = publication.repository_version

        release_file = deb_get_content_types(
            "apt_release_file_api", DEB_RELEASE_FILE_NAME, repo, version_href
        )[0]
        release = deb_get_content_types("apt_release_api", DEB_RELEASE_NAME, repo, version_href)[0]
        components = deb_get_content_types(
            "apt_release_component_api", DEB_RELEASE_COMPONENT_NAME, repo, version_href
        )
        package_indices = deb_get_content_types(
            "apt_package_indices_api", DEB_PACKAGE_INDEX_NAME, repo, version_href
        )
        release_file_path = os.path.join(expected[release_file_folder], release_type)

        assert release_file_path == release_file.relative_path
        assert release_file.distribution == release.distribution == expected["distribution"]
        assert release_file.codename == release.codename == expected["codename"]
        assert release_file.suite == release.suite == expected["suite"]
        assert len(expected["components"]) == len(components)
        for component in components:
            assert component.component in expected["components"]
        assert len(expected[package_index_paths]) == len(package_indices)
        for package_index in package_indices:
            assert package_index.relative_path in expected[package_index_paths]

    return _verify_publication_data


@pytest.fixture
def verify_distribution(download_content_unit):
    def _verify_distribution(distribution, expected):
        """Verifies if the content of a given distribution can be accessed.

        :param distribution: The distribution that needs its data verified.
        :param expected: The expected data of the content locations.
        """
        release_file_path = os.path.join(expected["release_file_folder_dist"], "Release")
        unit = download_content_unit(distribution.to_dict()["base_path"], release_file_path)
        assert "404: Not Found" not in str(unit)
        for package_index_path in expected["package_index_paths_dist"]:
            unit = download_content_unit(distribution.to_dict()["base_path"], package_index_path)
            assert "404: Not Found" not in str(unit)

    return _verify_distribution


@pytest.mark.parallel
@pytest.mark.parametrize(
    "publication_args",
    [
        DEB_PUBLICATION_ARGS_ONLY_SIMPLE,
        DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
        DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED,
        DEB_PUBLICATION_ARGS_ALL,
        {},
    ],
)
def test_publish_any_repo_version(
    create_publication_and_verify_repo_version,
    deb_delete_publication,
    deb_publication_by_version_factory,
    deb_publication_factory,
    deb_signing_service_factory,
    publication_args,
):
    """Test whether a particular repository version can be published.

    The following cases are tested:

    * `Publish a simple repository version.`_
    * `Publish a structured repository version.`_
    * `Publish a simple and structured repository version.`_
    * `Publish a simple, structured and signed repository version.`_
    * `Publish with default arguments. Which is just a structured repository.`_
    """
    # Create a repository with multiple versions and publication with the latest version
    if "signing_service" in publication_args.keys():
        publication_args["signing_service"] = deb_signing_service_factory.pulp_href
    remote_args = {"distributions": DEB_FIXTURE_DISTRIBUTIONS}
    first_publication, repo, _, version_hrefs = create_publication_and_verify_repo_version(
        remote_args,
        publication_args=publication_args,
        is_modified=True,
    )

    # Create a second publication with a non-latest repository version
    non_latest = choice(version_hrefs[:-1])
    second_publication = deb_publication_by_version_factory(non_latest, **publication_args)
    assert second_publication.repository_version == non_latest

    # Verify publishing two different repository versions at the same time raises an exception
    with pytest.raises(ApiException) as exc:
        deb_publication_factory(repo, **{"repository_version": non_latest})
    assert exc.value.status == 400

    # Because the cleanup of the publications happens after we try to delete
    # the signing service in the `deb_signing_service_factory` fixture we need to
    # delete both publications explicitly here. Otherwise the signing service
    # deletion will result in a `django.db.models.deletion.ProtectedError`.
    if "signing_service" in publication_args.keys():
        deb_delete_publication(first_publication)
        deb_delete_publication(second_publication)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "set_on, expect_signed",
    [
        ("repo", True),
        ("release", True),
        ("publication", True),
        ("nothing", False),
    ],
)
def test_publish_signing_services(
    create_publication_and_verify_repo_version,
    deb_delete_publication,
    deb_delete_repository,
    deb_distribution_factory,
    deb_signing_service_factory,
    download_content_unit,
    set_on,
    expect_signed,
):
    """Test whether a signing service preferences are honored.

    The following cases are tested:

    * `Publish where a SigningService is set on the Repo.`_
    * `Publish where a SigningService is set on a Release.`_
    * `Publish where a SigningService is set on a Publication.`_
    """
    # Determine where the signing service is set on and set the publish and repository
    # settings accordingly.
    signing_service = deb_signing_service_factory
    remote_args = {"distributions": DEB_FIXTURE_SINGLE_DIST}
    if set_on == "publication":
        publication_args = DEB_PUBLICATION_ARGS_ALL
        publication_args["signing_service"] = signing_service.pulp_href
    else:
        publication_args = DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED
    repo_args = {}
    if set_on == "repo":
        repo_args["signing_service"] = signing_service.pulp_href
    elif set_on == "release":
        repo_args["signing_service_release_overrides"] = {
            DEB_FIXTURE_SINGLE_DIST: signing_service.pulp_href
        }

    # Create a repository and publication.
    publication, repo, _, _ = create_publication_and_verify_repo_version(
        remote_args, publication_args, repo_args
    )

    # Create a distribution
    distribution = deb_distribution_factory(publication)

    # Check that the expected InRelease file is there:
    unit = download_content_unit(distribution.to_dict()["base_path"], "dists/ragnarok/InRelease")
    succeeded = False if "404: Not Found" in str(unit) else True
    assert expect_signed == succeeded

    # Because the cleanup of the publications happens after we try to delete
    # the signing service in the `deb_signing_service_factory` fixture we need to
    # delete the publication explicitly here. Otherwise the signing service
    # deletion will result in a `django.db.models.deletion.ProtectedError`.
    deb_delete_publication(publication)
    deb_delete_repository(repo)


@pytest.mark.parallel
def test_publish_repository_version_verbatim(
    create_publication_and_verify_repo_version,
    deb_verbatim_publication_by_version_factory,
    deb_verbatim_publication_factory,
):
    """Test whether a particular repository version can be published verbatim."""
    # Create a repository with multiple versions and publication with the latest version
    remote_args = {"distributions": DEB_FIXTURE_DISTRIBUTIONS}
    _, repo, _, version_hrefs = create_publication_and_verify_repo_version(
        remote_args,
        is_verbatim=True,
        is_modified=True,
    )

    # Create a second publication with a non-latest repository version
    non_latest = choice(version_hrefs[:-1])
    publication = deb_verbatim_publication_by_version_factory(non_latest)
    assert publication.repository_version == non_latest

    # Verify publication two different repository versions at the same time raises an exception
    with pytest.raises(ApiException) as exc:
        deb_verbatim_publication_factory(repo, **{"repository_version": non_latest})
    assert exc.value.status == 400


@pytest.mark.parallel
def test_publish_empty_repository(
    create_publication_and_verify_repo_version,
    deb_distribution_factory,
    deb_get_content_summary,
    download_content_unit,
):
    """Test whether an empty respository with no packages can be published."""
    # Create a publication.
    publication, _, _, _ = create_publication_and_verify_repo_version(
        remote_args={"distributions": DEB_FIXTURE_ALT_SINGLE_DIST},
        publication_args=DEB_PUBLICATION_ARGS_SIMPLE_AND_STRUCTURED,
    )

    release = deb_get_content_summary(
        repo=publication.to_dict(), version_href=publication.repository_version
    ).present

    package_index_paths = DEB_PUBLISH_EMPTY_REPOSITORY["package_index_paths"]
    assert DEB_PACKAGE_NAME not in release.keys()
    assert len(release[DEB_PACKAGE_INDEX_NAME]) >= 0
    assert len(package_index_paths) - 1 == release[DEB_PACKAGE_INDEX_NAME]["count"]

    # Create a distribution
    distribution = deb_distribution_factory(publication)

    # Verify that the expected package indices are present
    for package_index_path in package_index_paths:
        download_content_unit(distribution.to_dict()["base_path"], package_index_path)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "expected_data", [DEB_PUBLISH_FLAT_VERBATIM, DEB_PUBLISH_FLAT_NESTED_VERBATIM]
)
def test_publish_flat_repository_verbatim(
    create_publication_and_verify_repo_version,
    deb_distribution_factory,
    verify_distribution,
    verify_publication_data,
    expected_data,
):
    """Test whether a particular flat repository can be published verbatim.

    The following cases are tested:

    * `Publish a flat repository verbatim.`_
    * `Publish a nested flat repository verbatim.`_
    """
    remote_args = {"distributions": expected_data["distribution"]}

    # Create a publication
    publication, _, _, _ = create_publication_and_verify_repo_version(
        remote_args, {}, remote_name=DEB_FIXTURE_FLAT_REPOSITORY_NAME, is_verbatim=True
    )
    verify_publication_data(publication, expected_data, is_nested=True)

    # Create a distribution
    distribution = deb_distribution_factory(publication)
    verify_distribution(distribution, expected_data)


@pytest.mark.parallel
@pytest.mark.parametrize(
    "expected_data, publication_args",
    [
        (DEB_PUBLISH_FLAT_STRUCTURED, DEB_PUBLICATION_ARGS_ONLY_STRUCTURED),
        (DEB_PUBLISH_FLAT_SIMPLE, DEB_PUBLICATION_ARGS_ONLY_SIMPLE),
        (DEB_PUBLISH_FLAT_NESTED_STRUCTURED, DEB_PUBLICATION_ARGS_ONLY_STRUCTURED),
        (DEB_PUBLISH_FLAT_NESTED_SIMPLE, DEB_PUBLICATION_ARGS_ONLY_SIMPLE),
    ],
)
def test_publish_flat_repository(
    create_publication_and_verify_repo_version,
    deb_distribution_factory,
    expected_data,
    verify_distribution,
    verify_publication_data,
    publication_args,
):
    """Test whether a particular flat repository can be published.

    The following cases are tested:

    * `Publish a flat repository structured.`_
    * `Publish a flat repository simple.`_
    * `Publish a nested flat repository structured.`_
    * `Publish a nested flat repository simple.`_
    """
    remote_args = {"distributions": expected_data["distribution"]}

    # Create a publication
    publication, _, _, _ = create_publication_and_verify_repo_version(
        remote_args=remote_args,
        publication_args=publication_args,
        remote_name=DEB_FIXTURE_FLAT_REPOSITORY_NAME,
    )
    verify_publication_data(publication, expected_data, is_nested=True)

    # Create a distribution
    distribution = deb_distribution_factory(publication)
    verify_distribution(distribution, expected_data)


@pytest.mark.skip("Skip - ignore_missing_package_indices sync parameter does currently not work")
@pytest.mark.parallel
def test_publish_missing_architecture(
    create_publication_and_verify_repo_version,
    deb_distribution_factory,
    download_content_unit,
    verify_publication_data,
):
    """Test whether a repository can be published with missing package indices."""
    remote_args = {
        "distributions": DEB_PUBLISH_MISSING_ARCHITECTURE["distribution"],
        "ignore_missing_package_indices": True,
    }

    publication, _, remote, _ = create_publication_and_verify_repo_version(
        remote_args,
        publication_args=DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
        remote_name=DEB_FIXTURE_MISSING_ARCHITECTURE_REPOSITORY_NAME,
    )
    verify_publication_data(publication, DEB_PUBLISH_MISSING_ARCHITECTURE)

    assert os.path.isdir(os.path.join(remote.url, "dists/ragnarok/asgard/binary-armeb"))
    assert os.path.isdir(os.path.join(remote.url, "dists/ragnarok/jotunheimr/binary-armeb"))

    # Create a distribution
    distribution = deb_distribution_factory(publication)

    # Check that the expected Release files and package indices are there
    release_file_path = os.path.join(
        DEB_PUBLISH_MISSING_ARCHITECTURE["release_file_folder"], "Release"
    )
    download_content_unit(distribution.to_dict()["base_path"], release_file_path)

    for package_index_path in DEB_PUBLISH_MISSING_ARCHITECTURE["package_index_paths"]:
        download_content_unit(distribution.to_dict()["base_path"], package_index_path + "/Packages")


@pytest.mark.parallel
@pytest.mark.parametrize(
    "expected_data", [DEB_PUBLISH_COMPLEX_UBUNTU_BACKPORTS, DEB_PUBLISH_COMPLEX_DEBIAN_SECURITY]
)
def test_publish_complex_dists(
    apt_distribution_api,
    create_publication_and_verify_repo_version,
    deb_distribution_factory,
    deb_get_fixture_server_url,
    download_content_unit,
    verify_publication_data,
    http_get,
    expected_data,
):
    """Test whether a repository with complex distributions can be published.

    The following cases are tested:

    * `Publish an ubuntu backports repository.`_
    * `Publish a debian security repository.`_
    """
    remote_args = {"distributions": expected_data["distribution"]}
    fixture_url = deb_get_fixture_server_url(DEB_FIXTURE_COMPLEX_REPOSITORY_NAME)

    # Create a publication
    publication, _, _, _ = create_publication_and_verify_repo_version(
        remote_args,
        publication_args=DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
        remote_name=DEB_FIXTURE_COMPLEX_REPOSITORY_NAME,
    )
    verify_publication_data(publication, expected_data)

    # Create a distribution
    distribution = deb_distribution_factory(publication)
    distribution = apt_distribution_api.read(distribution.pulp_href)

    # Check that the expected Release files and package indicies are there
    release_file_path = os.path.join(expected_data["release_file_folder"], "Release")
    download_content_unit(distribution.to_dict()["base_path"], release_file_path)

    for package_index_path in expected_data["package_index_paths"]:
        published = download_content_unit(distribution.to_dict()["base_path"], package_index_path)
        url = "/".join([fixture_url, package_index_path])
        print(f"url: {url}")
        remote = http_get(url)
        assert_equal_package_index(remote, published)


@pytest.mark.parallel
def test_remove_package_from_repository(
    create_publication_and_verify_repo_version,
    deb_get_content_types,
    deb_modify_repository,
    deb_get_repository_by_href,
):
    """Test whether removing content in a structured publication removes all relevant content."""
    remote_args = {"distributions": DEB_FIXTURE_DISTRIBUTIONS}
    _, repo, _, _ = create_publication_and_verify_repo_version(
        remote_args,
        publication_args=DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
        is_modified=False,
    )

    package = deb_get_content_types(
        "apt_package_api", DEB_PACKAGE_NAME, repo, repo.latest_version_href
    )[0]
    prcs = deb_get_content_types(
        "apt_package_release_components_api",
        DEB_PACKAGE_RELEASE_COMPONENT_NAME,
        repo,
        repo.latest_version_href,
    )
    deb_modify_repository(
        repo,
        {"remove_content_units": [package.pulp_href]},
    )
    repo = deb_get_repository_by_href(repo.pulp_href)
    prcs_new = deb_get_content_types(
        "apt_package_release_components_api",
        DEB_PACKAGE_RELEASE_COMPONENT_NAME,
        repo,
        repo.latest_version_href,
    )

    assert not any(package.pulp_href == prc.package for prc in prcs_new)
    assert len(prcs_new) == len(prcs) - 1


@pytest.mark.parallel
def test_remove_all_content_from_repository(
    create_publication_and_verify_repo_version,
    deb_get_content_types,
    deb_modify_repository,
    deb_get_repository_by_href,
):
    """Test whether removing all content from a structured publication removes relevant content."""
    remote_args = {"distributions": DEB_FIXTURE_DISTRIBUTIONS}
    _, repo, _, _ = create_publication_and_verify_repo_version(
        remote_args,
        publication_args=DEB_PUBLICATION_ARGS_ONLY_STRUCTURED,
        is_modified=False,
    )

    deb_modify_repository(
        repo,
        {"remove_content_units": ["*"]},
    )
    repo = deb_get_repository_by_href(repo.pulp_href)
    prcs = deb_get_content_types(
        "apt_package_release_components_api",
        DEB_PACKAGE_RELEASE_COMPONENT_NAME,
        repo,
        repo.latest_version_href,
    )

    assert len(prcs) == 0


def assert_equal_package_index(orig, new):
    """In-detail check of two PackageIndex file-strings"""
    parsed_orig = parse_package_index(orig)
    parsed_new = parse_package_index(new)

    assert len(parsed_orig) == len(parsed_new)

    for name, pkg in parsed_new.items():
        orig_pkg = parsed_orig[name]
        for k in orig_pkg.keys():
            assert k in pkg
            if k == "Filename":
                continue
            assert pkg[k] == orig_pkg[k]


def parse_package_index(pkg_idx):
    """Parses PackageIndex file-string.
    Returns a dict of the packages by '<Package>-<Version>-<Architecture>'.
    """
    packages = {}
    for package in deb822.Packages.iter_paragraphs(pkg_idx, use_apt_pkg=False):
        packages["-".join([package["Package"], package["Version"], package["Architecture"]])] = (
            package
        )
    return packages
