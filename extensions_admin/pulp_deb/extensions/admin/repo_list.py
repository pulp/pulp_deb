# -*- coding: utf-8 -*-

from gettext import gettext as _

from pulp.client.commands.repo.cudl import ListRepositoriesCommand
from pulp.common import constants as pulp_constants

from pulp_deb.common import constants


class RepoListCommand(ListRepositoriesCommand):
    def __init__(self, context):
        repos_title = _(constants.REPOS_TITLE)
        super(RepoListCommand, self).__init__(context, repos_title=repos_title)

        # Both get_repositories and get_other_repositories will act on the full
        # list of repositories. Lazy cache the data here since both will be
        # called in succession, saving the round trip to the server.
        self.all_repos_cache = None

    def get_repositories(self, query_params, **kwargs):
        all_repos = self._all_repos(query_params, **kwargs)

        rpm_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if pulp_constants.REPO_NOTE_TYPE_KEY in notes and notes[pulp_constants.REPO_NOTE_TYPE_KEY] == constants.REPO_NOTE_PKG:  # noqa
                rpm_repos.append(repo)

        # Strip out the certificate and private key if present
        for r in rpm_repos:
            # The importers will only be present in a --details view, so make
            # sure it's there before proceeding
            if 'importers' not in r:
                continue
            try:
                # there can only be one importer
                imp_config = r['importers'][0]['config']
            except IndexError:
                continue

            # If either are present, tell the user the feed is using SSL
            if 'ssl_client_cert' in imp_config or 'ssl_client_key' in imp_config:  # noqa
                imp_config['feed_ssl_configured'] = 'True'

            # Remove the actual values so they aren't displayed
            imp_config.pop('ssl_client_cert', None)
            imp_config.pop('ssl_client_key', None)

        return rpm_repos

    def get_other_repositories(self, query_params, **kwargs):
        all_repos = self._all_repos(query_params, **kwargs)

        non_rpm_repos = []
        for repo in all_repos:
            notes = repo['notes']
            if notes.get(pulp_constants.REPO_NOTE_TYPE_KEY, None) != constants.REPO_NOTE_PKG:  # noqa
                non_rpm_repos.append(repo)

        return non_rpm_repos

    def _all_repos(self, query_params, **kwargs):

        # This is safe from any issues with concurrency due to how the CLI works
        if self.all_repos_cache is None:
            self.all_repos_cache = self.context.server.repo.repositories(
                query_params).response_body

        return self.all_repos_cache
