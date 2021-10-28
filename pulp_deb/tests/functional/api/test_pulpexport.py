"""
Tests PulpExporter and PulpExport functionality.
NOTE: assumes ALLOWED_EXPORT_PATHS setting contains "/tmp" - all tests will fail if this is not
the case.
"""
from pulp_smash import api, cli, config
from pulp_smash.utils import uuid4
from pulp_smash.pulp3.bindings import (
    delete_orphans,
    monitor_task,
    PulpTestCase,
)

from pulp_smash.pulp3.utils import gen_repo

from pulp_deb.tests.functional.utils import (
    gen_deb_client,
    gen_deb_remote,
)

from pulpcore.client.pulpcore import (
    ApiClient as CoreApiClient,
    ExportersPulpApi,
    ExportersPulpExportsApi,
)

from pulpcore.client.pulp_deb import (
    RepositoriesAptApi,
    RepositorySyncURL,
    RemotesAptApi,
)


class BaseExporterCase(PulpTestCase):
    """
    Base functionality for Exporter and Export test classes.
    The export process isn't possible without repositories having been sync'd - arranging for
    that to happen once per-class (instead of once-per-test) is the primary purpose of this parent
    class.
    """

    @classmethod
    def _setup_repositories(cls):
        """Create and sync a number of repositories to be exported."""
        # create and remember a set of repo
        repos = []
        remotes = []
        a_repo = cls.repo_api.create(gen_repo())
        # give it a remote and sync it
        body = gen_deb_remote()
        remote = cls.remote_api.create(body)
        repository_sync_data = RepositorySyncURL(remote=remote.pulp_href)
        sync_response = cls.repo_api.sync(a_repo.pulp_href, repository_sync_data)
        monitor_task(sync_response.task)
        # remember it
        repos.append(a_repo)
        remotes.append(remote)
        return a_repo, remote

    @classmethod
    def setUpClass(cls):
        """Create class-wide variables."""
        cls.cfg = config.get_config()
        cls.client = api.Client(cls.cfg, api.json_handler)
        cls.core_client = CoreApiClient(configuration=cls.cfg.get_bindings_config())
        cls.deb_client = gen_deb_client()

        cls.repo_api = RepositoriesAptApi(cls.deb_client)
        cls.remote_api = RemotesAptApi(cls.deb_client)
        cls.exporter_api = ExportersPulpApi(cls.core_client)
        cls.exports_api = ExportersPulpExportsApi(cls.core_client)

        (cls.repo, cls.remote) = cls._setup_repositories()

    @classmethod
    def tearDownClass(cls):
        """Clean up after ourselves."""
        cls.remote_api.delete(cls.remote.pulp_href)
        cls.repo_api.delete(cls.repo.pulp_href)
        delete_orphans()

    def _delete_exporter(self, exporter):
        """
        Utility routine to delete an exporter.
        Delete even with existing last_export should now Just Work
        (as of https://pulp.plan.io/issues/6555)
        """
        cli_client = cli.Client(self.cfg)
        cmd = ("rm", "-rf", exporter.path)
        cli_client.run(cmd, sudo=True)

        self.exporter_api.delete(exporter.pulp_href)

    def _create_exporter(self, cleanup=True):
        """
        Utility routine to create an exporter for the available repositories.
        """
        body = {
            "name": uuid4(),
            "path": "/tmp/{}/".format(uuid4()),
            "repositories": [self.repo.pulp_href],
        }
        exporter = self.exporter_api.create(body)
        if cleanup:
            self.addCleanup(self._delete_exporter, exporter)
        return exporter, body


class PulpExportAptTestCase(BaseExporterCase):
    """Test PulpExport CRDL methods (Update is not allowed)."""

    def _gen_export(self, exporter, body={}):
        """Create and read back an export for the specified PulpExporter."""
        export_response = self.exports_api.create(exporter.pulp_href, body)
        monitor_task(export_response.task)
        task = self.client.get(export_response.task)
        resources = task["created_resources"]
        self.assertEqual(1, len(resources))
        export_href = resources[0]
        export = self.exports_api.read(export_href)
        self.assertIsNotNone(export)
        return export

    def test_export(self):
        """Issue and evaluate a PulpExport (tests both Create and Read)."""
        (exporter, body) = self._create_exporter(cleanup=False)
        try:
            export = self._gen_export(exporter)
            self.assertIsNotNone(export)
            self.assertEqual(len(exporter.repositories), len(export.exported_resources))
            self.assertIsNotNone(export.output_file_info)
            for an_export_filename in export.output_file_info.keys():
                self.assertFalse("//" in an_export_filename)

        finally:
            self._delete_exporter(exporter)
