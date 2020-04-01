# coding=utf-8
"""Utilities for tests for the deb plugin."""
import os
from functools import partial
from unittest import SkipTest
from time import sleep
from tempfile import NamedTemporaryFile

from pulp_smash import api, config, selectors, utils
from pulp_smash.pulp3.utils import (
    gen_remote,
    gen_repo,
    get_content,
    require_pulp_3,
    require_pulp_plugins,
    sync,
)

from pulp_deb.tests.functional.constants import (
    DEB_FIXTURE_DISTRIBUTIONS,
    DEB_FIXTURE_URL,
    DEB_GENERIC_CONTENT_NAME,
    DEB_GENERIC_CONTENT_PATH,
    DEB_GENERIC_CONTENT_RELPATH,
    # DEB_PACKAGE_INDEX_NAME,
    DEB_PACKAGE_NAME,
    DEB_PACKAGE_RELEASE_COMPONENT_NAME,
    DEB_PUBLICATION_PATH,
    DEB_RELEASE_COMPONENT_NAME,
    DEB_RELEASE_FILE_NAME,
    DEB_REMOTE_PATH,
    DEB_REPO_PATH,
    VERBATIM_PUBLICATION_PATH,
)

from pulpcore.client.pulpcore import (
    ApiClient as CoreApiClient,
    ArtifactsApi,
    TasksApi,
    SigningServicesApi,
)
from pulpcore.client.pulp_deb import (
    ApiClient as DebApiClient,
    ContentGenericContentsApi,
    ContentPackagesApi,
    DistributionsAptApi,
    PublicationsAptApi,
    PublicationsVerbatimApi,
    RemotesAptApi,
    RepositoriesAptApi,
)

skip_if = partial(selectors.skip_if, exc=SkipTest)  # pylint:disable=invalid-name
"""The ``@skip_if`` decorator, customized for unittest.

:func:`pulp_smash.selectors.skip_if` is test runner agnostic. This function is
identical, except that ``exc`` has been set to ``unittest.SkipTest``.
"""

cfg = config.get_config()
configuration = cfg.get_bindings_config()

core_client = CoreApiClient(configuration)
artifact_api = ArtifactsApi(core_client)
task_api = TasksApi(core_client)
signing_service_api = SigningServicesApi(core_client)

deb_client = DebApiClient(configuration)
deb_generic_content_api = ContentGenericContentsApi(deb_client)
deb_package_api = ContentPackagesApi(deb_client)
deb_remote_api = RemotesAptApi(deb_client)
deb_repository_api = RepositoriesAptApi(deb_client)
deb_apt_publication_api = PublicationsAptApi(deb_client)
deb_verbatim_publication_api = PublicationsVerbatimApi(deb_client)
deb_distribution_api = DistributionsAptApi(deb_client)


def set_up_module():
    """Skip tests Pulp 3 isn't under test or if pulp_deb isn't installed."""
    require_pulp_3(SkipTest)
    require_pulp_plugins({"pulp_deb"}, SkipTest)


def gen_deb_client():
    """Return an OBJECT for deb client."""
    return deb_client


def gen_deb_remote(
    url=DEB_FIXTURE_URL,
    distributions=DEB_FIXTURE_DISTRIBUTIONS,
    sync_udebs=False,
    gpgkey=None,
    **kwargs,
):
    """Return a semi-random dict for use in creating a deb Remote.

    :param url: The URL of an external content source.
    """
    if gpgkey:
        kwargs["gpgkey"] = gpgkey
    return gen_remote(url, distributions=distributions, sync_udebs=sync_udebs, **kwargs)


def get_deb_content_unit_paths(repo, version_href=None):
    """Return the relative path of content units present in a deb repository.

    :param repo: A dict of information about the repository.
    :param version_href: The repository version to read.
    :returns: A dict of list with the paths of units present in a given repository
        for different content types. Paths are given as pairs with the remote and the
        local version.
    """

    def _rel_path(package, component=""):
        sourcename = package["source"] or package["package"]
        if sourcename.startswith("lib"):
            prefix = sourcename[0:4]
        else:
            prefix = sourcename[0]
        return os.path.join(
            "pool",
            component,
            prefix,
            sourcename,
            "{}_{}_{}.deb".format(package["package"], package["version"], package["architecture"]),
        )

    content = get_content(repo.to_dict(), version_href)
    result = {
        DEB_PACKAGE_NAME: [
            (content_unit["relative_path"], _rel_path(content_unit, "all"))
            for content_unit in content[DEB_PACKAGE_NAME]
        ]
    }
    for prc in content[DEB_PACKAGE_RELEASE_COMPONENT_NAME]:
        package = next(
            package
            for package in content[DEB_PACKAGE_NAME]
            if package["pulp_href"] == prc["package"]
        )
        release_component = next(
            rc
            for rc in content[DEB_RELEASE_COMPONENT_NAME]
            if rc["pulp_href"] == prc["release_component"]
        )
        result[DEB_PACKAGE_NAME].append(
            (package["relative_path"], _rel_path(package, release_component["component"]))
        )
    return result


def get_deb_verbatim_content_unit_paths(repo, version_href=None):
    """Return the relative path of content units present in a deb repository.

    :param repo: A dict of information about the repository.
    :param version_href: The repository version to read.
    :returns: A dict of list with the paths of units present in a given repository
        for different content types. Paths are given as pairs with the remote and the
        local version.
    """
    return {
        DEB_RELEASE_FILE_NAME: [
            (content_unit["relative_path"], content_unit["relative_path"])
            for content_unit in get_content(repo.to_dict(), version_href)[DEB_RELEASE_FILE_NAME]
        ],
        DEB_PACKAGE_NAME: [
            (content_unit["relative_path"], content_unit["relative_path"])
            for content_unit in get_content(repo.to_dict(), version_href)[DEB_PACKAGE_NAME]
        ],
        DEB_GENERIC_CONTENT_NAME: [
            (content_unit["relative_path"], content_unit["relative_path"])
            for content_unit in get_content(repo.to_dict(), version_href)[DEB_GENERIC_CONTENT_NAME]
        ],
    }


def gen_deb_content_attrs(artifact):
    """Generate a dict with generic content unit attributes.

    :param: artifact: A dict of info about the artifact.
    :returns: A semi-random dict for use in creating a content unit.
    """
    return {"artifact": artifact["pulp_href"], "relative_path": DEB_GENERIC_CONTENT_RELPATH}


def gen_deb_content_upload_attrs():
    """Generate a dict with generic content unit attributes for upload.

    :returns: A semi-random dict for use in creating a content unit.
    """
    return {"relative_path": DEB_GENERIC_CONTENT_RELPATH}


def gen_deb_package_attrs(artifact):
    """Generate a dict with package unit attributes.

    :param: artifact: A dict of info about the artifact.
    :returns: A semi-random dict for use in creating a content unit.
    """
    return {"artifact": artifact["pulp_href"]}


def gen_deb_package_upload_attrs():
    """Generate a dict with package unit attributes for upload.

    :returns: A semi-random dict for use in creating a content unit.
    """
    return {}


def populate_pulp(cfg, url=DEB_FIXTURE_URL):
    """Add deb contents to Pulp.

    :param pulp_smash.config.PulpSmashConfig: Information about a Pulp application.
    :param url: The deb repository URL. Defaults to
        :data:`pulp_smash.constants.DEB_FIXTURE_URL`
    :returns: A list of dicts, where each dict describes one file content in Pulp.
    """
    client = api.Client(cfg, api.json_handler)
    remote = {}
    repo = {}
    try:
        remote.update(client.post(DEB_REMOTE_PATH, gen_deb_remote(url)))
        repo.update(client.post(DEB_REPO_PATH, gen_repo()))
        sync(cfg, remote, repo)
    finally:
        if remote:
            client.delete(remote["pulp_href"])
        if repo:
            client.delete(repo["pulp_href"])
    return client.get(DEB_GENERIC_CONTENT_PATH)["results"]


def create_deb_publication(cfg, repo, version_href=None):
    """Create a deb publication.

    :param pulp_smash.config.PulpSmashConfig cfg: Information about the Pulp
        host.
    :param repo: A dict of information about the repository.
    :param version_href: A href for the repo version to be published.
    :returns: A publication. A dict of information about the just created
        publication.
    """
    if version_href:
        body = {"repository_version": version_href}
    else:
        body = {"repository": repo["pulp_href"]}
    body["simple"] = True
    body["structured"] = True

    client = api.Client(cfg, api.json_handler)
    call_report = client.post(DEB_PUBLICATION_PATH, body)
    tasks = tuple(api.poll_spawned_tasks(cfg, call_report))
    return client.get(tasks[-1]["created_resources"][0])


def create_verbatim_publication(cfg, repo, version_href=None):
    """Create a verbatim publication.

    :param pulp_smash.config.PulpSmashConfig cfg: Information about the Pulp
        host.
    :param repo: A dict of information about the repository.
    :param version_href: A href for the repo version to be published.
    :returns: A publication. A dict of information about the just created
        publication.
    """
    if version_href:
        body = {"repository_version": version_href}
    else:
        body = {"repository": repo["pulp_href"]}

    client = api.Client(cfg, api.json_handler)
    call_report = client.post(VERBATIM_PUBLICATION_PATH, body)
    tasks = tuple(api.poll_spawned_tasks(cfg, call_report))
    return client.get(tasks[-1]["created_resources"][0])


def gen_artifact(url):
    """Creates an artifact."""
    response = utils.http_get(url)
    with NamedTemporaryFile() as temp_file:
        temp_file.write(response)
        temp_file.flush()
        artifact = ArtifactsApi(core_client).create(file=temp_file.name)
        return artifact.to_dict()


class PulpTaskError(Exception):
    """Exception to describe task errors."""

    def __init__(self, task):
        """Provide task info to exception."""
        description = task.error["description"]
        super().__init__(self, f"Pulp task failed ({description})")
        self.task = task


def monitor_task(task_href):
    """Polls the Task API until the task is in a completed state.

    Prints the task details and a success or failure message. Exits on failure.

    Args:
        task_href(str): The href of the task to monitor

    Returns:
        list[str]: List of hrefs that identify resource created by the task

    """
    completed = ["completed", "failed", "canceled"]
    task = task_api.read(task_href)
    while task.state not in completed:
        sleep(2)
        task = task_api.read(task_href)

    if task.state == "completed":
        return task.created_resources

    raise PulpTaskError(task=task)
