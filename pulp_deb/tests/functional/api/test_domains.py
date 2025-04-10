import pytest
import json
import uuid

from pulpcore.client.pulp_deb.exceptions import ApiException


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
    deb_domain_factory,
    deb_init_and_sync,
    apt_repository_api,
    apt_package_api,
    deb_cleanup_domains,
):
    """Test repo-sync in a domain."""
    domain = deb_domain_factory()
    try:
        domain_name = domain.name
        repo, _ = deb_init_and_sync(pulp_domain=domain_name)
        repos = apt_repository_api.list(name=repo.name, pulp_domain=domain_name).results
        assert len(repos) == 1
        assert repos[0].pulp_href == repo.pulp_href
        assert apt_repository_api.list(pulp_domain=domain_name).count == 1
        assert (
            apt_package_api.list(
                repository_version=repo.latest_version_href, pulp_domain=domain_name
            ).count
            == 2
        )
    finally:
        deb_cleanup_domains([domain], content_api_client=apt_package_api, cleanup_repositories=True)


@pytest.mark.parallel
def test_object_creation(
    deb_domain_factory,
    deb_repository_factory,
    apt_repository_api,
    deb_remote_factory,
    deb_sync_repository,
    deb_get_fixture_server_url,
):
    """Test basic object creation in a separate domain."""
    domain = deb_domain_factory()
    domain_name = domain.name

    repo = deb_repository_factory(pulp_domain=domain_name)
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
        "non_field_errors": [f"Objects must all be apart of the {domain_name} domain."]
    }

    with pytest.raises(ApiException) as e:
        deb_sync_repository(remote=default_remote, repo=repo)
    assert e.value.status == 400
    assert json.loads(e.value.body) == {
        "non_field_errors": [f"Objects must all be apart of the {domain_name} domain."]
    }


@pytest.mark.parallel
def test_content_promotion(
    deb_domain_factory,
    deb_cleanup_domains,
    deb_publication_factory,
    deb_distribution_factory,
    deb_delete_repository,
    deb_init_and_sync,
    deb_get_repository_by_href,
):
    """Tests Content promotion path with domains: Sync->Publish->Distribute"""
    domain = deb_domain_factory()

    try:
        # Sync
        repo, _, task = deb_init_and_sync(pulp_domain=domain.name, return_task=True)
        assert len(task.created_resources) == 1

        repo = deb_get_repository_by_href(repo.pulp_href)
        assert repo.latest_version_href[-2] == "1"

        # Publish
        publication = deb_publication_factory(repo=repo, pulp_domain=domain.name)
        assert publication.repository == repo.pulp_href

        # Distribute
        distribution = deb_distribution_factory(publication=publication, pulp_domain=domain.name)
        assert distribution.publication == publication.pulp_href
        # url structure should be host/CONTENT_ORIGIN/DOMAIN_PATH/BASE_PATH
        assert domain.name == distribution.base_url.rstrip("/").split("/")[-2]

        # check that content can be downloaded from base_url
        # for pkg in ("", ""):
        #   pkg_path = get_package_repo_path(pkg)
        #   download_content_unit(distribution.base_path, pkg_path, domain=domain.name)

        # cleanup to delete the domain
        deb_delete_repository(repo)
    finally:
        deb_cleanup_domains([domain], cleanup_repositories=True)


@pytest.mark.parallel
def test_domain_rbac(
    deb_domain_factory, deb_cleanup_domains, apt_repository_api, deb_repository_factory, gen_user
):
    """Test domain level roles."""
    domain = deb_domain_factory()

    try:
        deb_viewer = "deb.debrepository_viewer"
        deb_creator = "deb.debrepository_creator"
        user_a = gen_user(username="a", domain_roles=[(deb_viewer, domain.pulp_href)])
        user_b = gen_user(username="b", domain_roles=[(deb_creator, domain.pulp_href)])

        # create two repos in different domains with admin user
        deb_repository_factory()
        deb_repository_factory(pulp_domain=domain.name)

        with user_b:
            repo = deb_repository_factory(pulp_domain=domain.name)
            repos = apt_repository_api.list(pulp_domain=domain.name)
            assert repos.count == 1
            assert repos.results[0].pulp_href == repo.pulp_href

            # try to create a repository in default domain
            with pytest.raises(ApiException) as e:
                deb_repository_factory()
            assert e.value.status == 403

        with user_a:
            repos = apt_repository_api.list(pulp_domain=domain.name)
            assert repos.count == 2

            # try to read repos in the default domain
            repos = apt_repository_api.list()
            assert repos.count == 0

            # try to create a repo
            with pytest.raises(ApiException) as e:
                deb_repository_factory(pulp_domain=domain.name)
            assert e.value.status == 403
    finally:
        deb_cleanup_domains([domain], cleanup_repositories=True)


@pytest.mark.parallel
def test_cross_domain_copy_all(
    deb_domain_factory,
):
    """Test attempting to copy between different domains."""
    domain_1 = None
    domain_2 = None
