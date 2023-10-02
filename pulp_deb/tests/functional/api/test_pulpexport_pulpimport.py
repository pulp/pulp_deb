"""
Tests PulpImporter/PulpExporter and PulpImport/PulpExport functionality.

NOTE: assumes ALLOWED_EXPORT_PATHS and ALLOWED_IMPORT_PATHS settings contain "/tmp"
all tests will fail if that is not the case.
"""
import pytest

from uuid import uuid4

NUM_REPOS = 2


@pytest.fixture
def deb_gen_import_export_repos(
    deb_get_fixture_server_url,
    deb_remote_factory,
    deb_repository_factory,
    deb_sync_repository,
):
    """A fixture to create a number of synced repositories to export."""

    def _deb_gen_import_export_repos(import_repos=None, export_repos=None):
        """Generate a number of repositories for import and export.

        :param import_repos: (Optional) List of already defined import repositories
        :param export_repos: (Optional) List of already defined export repositories
        :returns: A list of defined import and a list of defined export repositories
        """
        if import_repos or export_repos:
            # Repositories already initialized
            return import_repos, export_repos

        import_repos = []
        export_repos = []
        for r in range(NUM_REPOS):
            import_repo = deb_repository_factory()
            export_repo = deb_repository_factory()
            url = deb_get_fixture_server_url()
            remote = deb_remote_factory(url=url)
            deb_sync_repository(remote, export_repo)

            export_repos.append(export_repo)
            import_repos.append(import_repo)
        return (import_repos, export_repos)

    return _deb_gen_import_export_repos


@pytest.fixture
def deb_create_exporter(
    gen_object_with_cleanup, exporters_pulp_api_client, deb_gen_import_export_repos
):
    """A fixture that creates a pulp exporter."""

    def _deb_create_exporter(import_repos=None, export_repos=None):
        """Creates a pulp exporter.

        :param import_repos: (Optional) List of already defined import repositories
        :param export_repos: (Optional) List of already defined export repositories
        :returns: A pulp exporter with defined export repositories
        """
        if not export_repos:
            _, export_repos = deb_gen_import_export_repos(import_repos, export_repos)

        body = {
            "name": str(uuid4()),
            "repositories": [r.pulp_href for r in export_repos],
            "path": f"/tmp/{uuid4()}/",
        }
        return gen_object_with_cleanup(exporters_pulp_api_client, body)

    return _deb_create_exporter


@pytest.fixture
def deb_create_export(exporters_pulp_exports_api_client, deb_create_exporter, monitor_task):
    """A fixture that creates a pulp export."""

    def _deb_create_export(import_repos=None, export_repos=None, exporter=None, is_chunked=False):
        """Creates a pulp export.

        :param import_repos: (Optional) List of already defined import repositories
        :param export_repos: (Optional) List of already defined export repositories
        :param exporter: (Optional) An already set up pulp exporter
        :param is_chunked: (Optional) Boolean whether the export is chunked or not
        :returns: A pulp export with a set up pulp exporter
        """
        if not exporter:
            exporter = deb_create_exporter(import_repos, export_repos)

        body = {"chunk_size": "5KB"} if is_chunked else {}
        export_response = exporters_pulp_exports_api_client.create(exporter.pulp_href, body)
        export_href = monitor_task(export_response.task).created_resources[0]
        return exporters_pulp_exports_api_client.read(export_href)

    return _deb_create_export


@pytest.fixture
def deb_importer_factory(
    gen_object_with_cleanup, deb_gen_import_export_repos, importers_pulp_api_client
):
    """A fixture that creates a pulp importer."""

    def _deb_importer_factory(import_repos=None, export_repos=None, name=None, mapping=None):
        """Creates a pulp importer.

        :param import_repos: (Optional) List of already defined import repositories
        :param export_repos: (Optional) List of already defined export repositories
        :param name: (Optional) Name of the importer
        :param mapping: (Optional) Mapped import repositories
        :returns: A pulp importer set up with name and mapped import repositories
        """
        _import_repos, _export_repos = deb_gen_import_export_repos(import_repos, export_repos)
        if not name:
            name = str(uuid4())

        if not mapping:
            mapping = {}
            if not import_repos:
                import_repos = _import_repos
            if not export_repos:
                export_repos = _export_repos

            for idx, repo in enumerate(export_repos):
                mapping[repo.name] = import_repos[idx].name

        body = {
            "name": name,
            "repo_mapping": mapping,
        }
        return gen_object_with_cleanup(importers_pulp_api_client, body)

    return _deb_importer_factory


@pytest.fixture
def deb_perform_import(
    deb_create_export,
    deb_gen_import_export_repos,
    importers_pulp_imports_api_client,
    monitor_task_group,
):
    """A fixture that performs an import with a PulpImporter."""

    def _deb_perform_import(
        importer, import_repos=None, export_repos=None, is_chunked=False, an_export=None, body=None
    ):
        """Performs an import with a PulpImporter.

        :param importer: The importer that should perform the import
        :param import_repos: (Optional) List of already defined import repositories
        :param export_repos: (Optional) List of already defined export repositories
        :param is_chunked: (Optional) Boolean whether the export is chunked or not
        :param an_export: (Optional) Already defined exporter
        :param body: (Optional) Already defined import body
        :returns: Task group of the import task
        """
        if body is None:
            body = {}

        if not an_export:
            if not (import_repos or export_repos):
                import_repos, export_repos = deb_gen_import_export_repos

            an_export = deb_create_export(import_repos, export_repos, is_chunked=is_chunked)

        if is_chunked:
            filenames = [f for f in list(an_export.output_file_info.keys()) if f.endswith("json")]
            if "toc" not in body:
                body["toc"] = filenames[0]
        else:
            filenames = [
                f
                for f in list(an_export.output_file_info.keys())
                if f.endswith("tar") or f.endswith(".tar.gz")
            ]
            if "path" not in body:
                body["path"] = filenames[0]

        import_response = importers_pulp_imports_api_client.create(importer.pulp_href, body)
        task_group = monitor_task_group(import_response.task_group)

        return task_group

    return _deb_perform_import


@pytest.mark.parametrize("is_chunked", [False, True])
def test_import(
    deb_gen_import_export_repos,
    deb_get_repository_by_href,
    deb_importer_factory,
    deb_perform_import,
    is_chunked,
):
    """Test a PulpImport."""
    import_repos, export_repos = deb_gen_import_export_repos()
    importer = deb_importer_factory(import_repos, export_repos)
    task_group = deb_perform_import(importer, import_repos, export_repos, is_chunked=is_chunked)
    assert (len(import_repos) + 1) == task_group.completed

    for repo in import_repos:
        repo = deb_get_repository_by_href(repo.pulp_href)
        assert repo.latest_version_href.endswith("versions/1/")


def test_double_import(
    deb_gen_import_export_repos,
    deb_get_repository_by_href,
    deb_importer_factory,
    deb_perform_import,
    importers_pulp_imports_api_client,
):
    """Test two PulpImports for a PulpExport."""
    import_repos, export_repos = deb_gen_import_export_repos()
    importer = deb_importer_factory(import_repos, export_repos)
    deb_perform_import(importer, import_repos, export_repos)
    deb_perform_import(importer, import_repos, export_repos)

    imports = importers_pulp_imports_api_client.list(importer.pulp_href).results
    assert len(imports) == 2

    for repo in import_repos:
        repo = deb_get_repository_by_href(repo.pulp_href)
        assert repo.latest_version_href.endswith("versions/1/")


def test_export(deb_create_exporter, deb_create_export, deb_gen_import_export_repos):
    """Issue and evaluate a PulpExport."""
    import_repos, export_repos = deb_gen_import_export_repos()
    exporter = deb_create_exporter(import_repos, export_repos)
    export = deb_create_export(import_repos, export_repos, exporter)
    assert export is not None
    assert len(exporter.repositories) == len(export.exported_resources)
    assert export.output_file_info is not None
    for an_export_filename in export.output_file_info.keys():
        assert "//" not in an_export_filename
