"""Tests for optimized syncs against a previous version that lacks a package index."""

import io
from unittest import IsolatedAsyncioTestCase, mock

from pulp_deb.app.tasks.synchronizing import DebFirstStage, gen_remote_options

SYNCHRONIZING = "pulp_deb.app.tasks.synchronizing"


class TestOptimizeWithoutPreviousPackageIndex(IsolatedAsyncioTestCase):
    """
    An index that is new upstream, for example a new component or architecture, has no counterpart
    in the previous repository version. See https://github.com/pulp/pulp_deb/issues/719.
    """

    def setUp(self):
        remote = mock.Mock(
            url="http://example.com/debian/",
            distributions="stable",
            components="main",
            architectures="amd64",
            policy="immediate",
            sync_sources=False,
            sync_udebs=False,
            sync_installer=False,
            gpgkey=None,
            ignore_missing_package_indices=False,
        )
        previous_version = mock.Mock(
            info={
                "remote_options": gen_remote_options(remote),
                "sync_options": {"optimize": True, "mirror": False},
            }
        )
        self.stage = DebFirstStage(remote, True, False, previous_version)
        self.stage._create_unit = mock.AsyncMock(
            return_value=mock.Mock(artifact_set_sha256="new-index")
        )

    async def test_new_package_index_is_processed(self):
        """The new index must be parsed, not compared with a previous index that is not there."""
        self.assertTrue(self.stage.optimize)
        main_artifact = mock.AsyncMock(return_value=mock.Mock(file=io.BytesIO(b"")))
        with (
            mock.patch(
                f"{SYNCHRONIZING}._get_previous_package_index",
                mock.AsyncMock(return_value=None),
            ),
            mock.patch(f"{SYNCHRONIZING}._get_main_artifact_blocking", main_artifact),
        ):
            await self.stage._handle_package_index(
                release_file=mock.Mock(relative_path="dists/stable/Release", architectures="amd64"),
                release_component=mock.Mock(plain_component="main", component="main"),
                base_architecture="amd64",
                index_architecture="amd64",
                file_references={"main/binary-amd64/Packages": {"SHA256": "0" * 64, "Size": "0"}},
            )
        main_artifact.assert_awaited_once()
