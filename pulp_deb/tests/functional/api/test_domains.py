import pytest
import json
import uuid

from django.conf import settings

from pulpcore.client.pulp_deb.exceptions import ApiException

from pulp_deb.tests.functional.constants import DEB_PACKAGE_RELPATH, DEB_PUBLISH_STANDARD
from pulp_deb.tests.functional.utils import (
    gen_deb_remote,
    gen_distribution,
    gen_repo,
    get_local_package_absolute_path,
)

if not settings.DOMAIN_ENABLED:
    pytest.skip("Domains not enabled.", allow_module_level=True)


def test_domain_create(
    deb_domain_factory,
    deb_init_and_sync,
    apt_package_api,
    apt_repository_api,
):
    """Test repo-creation in a domain."""
    domain_name = deb_domain_factory().name

    # create and sync in default domain (not specified)
    deb_init_and_sync()

    # check that newly created domain doesn't have a repo or any packages
    assert apt_repository_api.list(pulp_domain=domain_name).count == 0
    assert apt_package_api.list(pulp_domain=domain_name).count == 0


def test_domain_sync(
    gen_object_with_cleanup,
    deb_domain_factory,
    apt_remote_api,
    apt_repository_api,
    apt_package_api,
    deb_get_fixture_server_url,
    deb_sync_repository,
    deb_cleanup_domains,
):
    """Test repo-sync in a domain."""
    domain = deb_domain_factory()
    try:
        domain_name = domain.name

        # create and sync in the newly-created domain
        url = deb_get_fixture_server_url()
        remote = gen_object_with_cleanup(
            apt_remote_api, gen_deb_remote(url=str(url)), pulp_domain=domain_name
        )
        repo = gen_object_with_cleanup(apt_repository_api, gen_repo(), pulp_domain=domain_name)

        # check that we can "find" the new repo in the new domain via filtering
        repos = apt_repository_api.list(name=repo.name, pulp_domain=domain_name).results
        assert len(repos) == 1
        assert repos[0].pulp_href == repo.pulp_href
        deb_sync_repository(remote=remote, repo=repo)
        repo = apt_repository_api.read(repo.pulp_href)

        # check that newly created domain has one repo (list works) and the expected contents
        assert apt_repository_api.list(pulp_domain=domain_name).count == 1
        assert (
            apt_package_api.list(
                repository_version=repo.latest_version_href, pulp_domain=domain_name
            ).count
            == 4
        )
    finally:
        deb_cleanup_domains([domain], content_api_client=apt_package_api, cleanup_repositories=True)


@pytest.mark.parallel
def test_object_creation(
    gen_object_with_cleanup,
    deb_domain_factory,
    apt_repository_api,
    deb_remote_factory,
    deb_sync_repository,
    deb_get_fixture_server_url,
):
    """Test basic object creation in a separate domain."""
    domain = deb_domain_factory()
    domain_name = domain.name

    url = deb_get_fixture_server_url()
    repo = gen_object_with_cleanup(apt_repository_api, gen_repo(), pulp_domain=domain_name)
    assert f"{domain_name}/api/v3/" in repo.pulp_href

    repos = apt_repository_api.list(pulp_domain=domain_name)
    assert repos.count == 1
    assert repo.pulp_href == repos.results[0].pulp_href

    # list repos on default domain
    default_repos = apt_repository_api.list(name=repo.name)
    assert default_repos.count == 0

    # try to create an object with cross domain relations
    url = deb_get_fixture_server_url()
    default_remote = deb_remote_factory(url)
    with pytest.raises(ApiException) as e:
        repo_body = {"name": str(uuid.uuid4()), "remote": default_remote.pulp_href}
        apt_repository_api.create(repo_body, pulp_domain=domain_name)
    assert e.value.status == 400
    assert json.loads(e.value.body) == {
        "non_field_errors": [f"Objects must all be a part of the {domain_name} domain."]
    }

    with pytest.raises(ApiException) as e:
        deb_sync_repository(remote=default_remote, repo=repo)
    assert e.value.status == 400
    assert json.loads(e.value.body) == {
        "non_field_errors": [f"Objects must all be a part of the {domain_name} domain."]
    }


@pytest.mark.parallel
def test_deb_from_file(
    deb_cleanup_domains,
    deb_domain_factory,
    apt_package_api,
    deb_package_factory,
):
    """Test uploading of deb content with domains"""
    domain = deb_domain_factory()

    try:
        package_upload_params = {
            "file": str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)),
            "relative_path": DEB_PACKAGE_RELPATH,
        }
        default_content = deb_package_factory(**package_upload_params)
        package_upload_params["pulp_domain"] = domain.name
        domain_content = deb_package_factory(**package_upload_params)
        assert default_content.pulp_href != domain_content.pulp_href
        assert default_content.sha256 == domain_content.sha256

        domain_contents = apt_package_api.list(pulp_domain=domain.name)
        assert domain_contents.count == 1
    finally:
        deb_cleanup_domains([domain], content_api_client=apt_package_api)


@pytest.mark.parallel
def test_content_promotion(
    gen_object_with_cleanup,
    monitor_task,
    download_content_unit,
    apt_remote_api,
    apt_repository_api,
    apt_publication_api,
    apt_distribution_api,
    deb_domain_factory,
    deb_cleanup_domains,
    deb_delete_repository,
    deb_sync_repository,
    deb_get_repository_by_href,
    deb_get_fixture_server_url,
):
    """Tests Content promotion path with domains: Sync->Publish->Distribute"""
    domain = deb_domain_factory()

    try:
        # Sync
        url = deb_get_fixture_server_url()
        remote = gen_object_with_cleanup(
            apt_remote_api, gen_deb_remote(url=str(url)), pulp_domain=domain.name
        )
        repo = gen_object_with_cleanup(apt_repository_api, gen_repo(), pulp_domain=domain.name)
        response = deb_sync_repository(remote=remote, repo=repo)
        assert len(response.created_resources) == 1

        repo = deb_get_repository_by_href(repo.pulp_href)
        assert repo.latest_version_href[-2] == "1"

        # Publish
        pub_body = {"repository": repo.pulp_href}
        task = apt_publication_api.create(pub_body, pulp_domain=domain.name).task
        response = monitor_task(task)
        assert len(response.created_resources) == 1
        pub_href = response.created_resources[0]
        publication = apt_publication_api.read(pub_href)
        assert publication.repository == repo.pulp_href

        # Distribute
        distro_body = gen_distribution()
        distro_body["publication"] = publication.pulp_href
        distribution = gen_object_with_cleanup(
            apt_distribution_api, distro_body, pulp_domain=domain.name
        )
        assert distribution.publication == publication.pulp_href
        # url structure should be host/CONTENT_ORIGIN/DOMAIN_PATH/BASE_PATH
        assert domain.name == distribution.base_url.rstrip("/").split("/")[-2]

        # check that content can be downloaded from base_url
        package_index_paths = DEB_PUBLISH_STANDARD["package_index_paths"]
        for package_index_path in package_index_paths:
            download_content_unit(
                distribution.to_dict()["base_path"], package_index_path, domain=domain.name
            )

        # cleanup to delete the domain
        deb_delete_repository(repo)
    finally:
        deb_cleanup_domains([domain], cleanup_repositories=True)


@pytest.mark.parallel
def test_domain_rbac(
    gen_object_with_cleanup, deb_domain_factory, deb_cleanup_domains, apt_repository_api, gen_user
):
    """Test domain level roles."""
    domain = deb_domain_factory()

    try:
        deb_viewer = "deb.aptrepository_viewer"
        deb_creator = "deb.aptrepository_creator"
        user_a = gen_user(username="a", domain_roles=[(deb_viewer, domain.pulp_href)])
        user_b = gen_user(username="b", domain_roles=[(deb_creator, domain.pulp_href)])

        # create two repos in different domains with admin user
        gen_object_with_cleanup(apt_repository_api, gen_repo())
        gen_object_with_cleanup(apt_repository_api, gen_repo(), pulp_domain=domain.name)

        with user_b:
            repo = gen_object_with_cleanup(apt_repository_api, gen_repo(), pulp_domain=domain.name)
            repos = apt_repository_api.list(pulp_domain=domain.name)
            assert repos.count == 1
            assert repos.results[0].pulp_href == repo.pulp_href

            # try to create a repository in default domain
            with pytest.raises(ApiException) as e:
                apt_repository_api.create({"name": str(uuid.uuid4())})
            assert e.value.status == 403

        with user_a:
            repos = apt_repository_api.list(pulp_domain=domain.name)
            assert repos.count == 2

            # try to read repos in the default domain
            repos = apt_repository_api.list()
            assert repos.count == 0

            # try to create a repo
            with pytest.raises(ApiException) as e:
                apt_repository_api.create({"name": str(uuid.uuid4())}, pulp_domain=domain.name)
            assert e.value.status == 403
    finally:
        deb_cleanup_domains([domain], cleanup_repositories=True)


@pytest.mark.parallel
def test_cross_domain_copy_all(
    deb_cleanup_domains,
    deb_copy_content_domain,
    deb_setup_domain,
):
    """Test attempting to copy between different domains."""
    domain1 = None
    domain2 = None
    try:
        domain1, _, src1, dest1 = deb_setup_domain()
        domain2, _, _, dest2 = deb_setup_domain()

        # Success, everything in domain1
        deb_copy_content_domain(
            source_repo_version=src1.latest_version_href,
            dest_repo=dest1.pulp_href,
            domain_name=domain1.name,
        )

        # Failure, call and src domain1, dest domain2
        with pytest.raises(ApiException):
            deb_copy_content_domain(
                source_repo_version=src1.latest_version_href,
                dest_repo=dest2.pulp_href,
                domain_name=domain1.name,
            )

        # Failure, call domain2, src/dest domain1
        with pytest.raises(ApiException):
            deb_copy_content_domain(
                source_repo_version=src1.latest_version_href,
                dest_repo=dest1.pulp_href,
                domain_name=domain2.name,
            )

    finally:
        deb_cleanup_domains([domain1, domain2], cleanup_repositories=True)


@pytest.mark.parallel
def test_cross_domain_content(
    apt_package_api,
    deb_setup_domain,
    deb_cleanup_domains,
    deb_copy_content_domain,
    deb_get_repository_by_href,
):
    """Test the content parameter."""
    domain1 = None
    domain2 = None
    try:
        domain1, _, src1, dest1 = deb_setup_domain()
        domain2, _, src2, dest2 = deb_setup_domain()

        # Copy content1 from src1 to dest1, expect 2 copied packages
        package1 = apt_package_api.list(package="frigg", pulp_domain=domain1.name).results[0]
        deb_copy_content_domain(
            source_repo_version=src1.latest_version_href,
            dest_repo=dest1.pulp_href,
            domain_name=domain1.name,
            content=[package1.pulp_href],
        )
        dest1 = deb_get_repository_by_href(dest1.pulp_href)
        packages1 = apt_package_api.list(
            repository_version=dest1.latest_version_href, pulp_domain=domain1.name
        ).results
        assert 1 == len(packages1)

        # copy content from src1 to dest1, domain2, expect failure
        with pytest.raises(ApiException):
            deb_copy_content_domain(
                source_repo_version=src1.latest_version_href,
                dest_repo=dest1.pulp_href,
                domain_name=domain2.name,
                content=[package1.pulp_href],
            )

        # copy content from src1 to dest2, domain1, expect failure
        with pytest.raises(ApiException):
            deb_copy_content_domain(
                source_repo_version=src1.latest_version_href,
                dest_repo=dest2.pulp_href,
                domain_name=domain1.name,
                content=[package1.pulp_href],
            )

        # copy mixed content from src2 to dest2, domain2, expect failure
        package2 = apt_package_api.list(package="frigg", pulp_domain=domain2.name).results[0]

        with pytest.raises(ApiException):
            deb_copy_content_domain(
                source_repo_version=src2.latest_version_href,
                dest_repo=dest2.pulp_href,
                domain_name=domain2.name,
                content=[package1.pulp_href, package2.pulp_href],
            )

    finally:
        deb_cleanup_domains([domain1, domain2], cleanup_repositories=True)
