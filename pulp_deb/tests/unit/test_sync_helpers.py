from django.test import TestCase
from unittest import mock

from pulp_deb.app.tasks.synchronizing import (
    _filter_split_architectures,
    _filter_split_components,
    _get_artifact_set_sha256,
)


class TestArtifactSetSha256Generation(TestCase):
    """
    Tests the _get_artifact_set_sha256() helper function.

    IMPORTANT:  _get_artifact_set_sha256()is used to generate uniqueness constraints for ReleaseFile
    and PackageIndex content. It must not be altered lightly!
    """

    d_artifact1 = mock.Mock()
    d_artifact1.relative_path = "dists/default/all/binary-amd64/Packages.xz"
    d_artifact1.artifact.sha256 = "1e4ee5542231148c5ca39533ff19d93848ec1829cbf7d269f7ebabef856e184b"

    d_artifact2 = mock.Mock()
    d_artifact2.relative_path = "dists/default/all/binary-amd64/Packages"
    d_artifact2.artifact.sha256 = "a55e0fbdaa6ea8a849398d89b8581f00318a6ce6d0c2ab8d875e22f0513771ca"

    d_content = mock.Mock()
    d_content.d_artifacts = [d_artifact1, d_artifact2]

    expected_hash = "0013ba371fba7f563a476ce55648ab745241295c71b481d3e60a9414162aab41"

    def test_expected_artifact_set_hash(self):
        """
        This test ensures that _get_artifact_set_sha256 delivers the expected hash for a mocked
        example declarative content for a PackageIndex.
        """
        artifact_list = ["Packages", "Packages.gz", "Packages.xz", "Release"]
        self.assertEqual(
            _get_artifact_set_sha256(self.d_content, artifact_list), self.expected_hash
        )

    def test_altered_artifact_list(self):
        """
        This test ensures that supplying _get_artifact_set_sha256 with an expanded artifact list,
        but unchanged declarative content, does NOT result in a changed hash!
        """
        new_artifact_list = ["Something.new", "Packages", "Packages.xz", "Release"]
        self.assertEqual(
            _get_artifact_set_sha256(self.d_content, new_artifact_list), self.expected_hash
        )


class TestArchitectureFiltering(TestCase):
    """
    Tests common as well as edge cases handled by the _filter_split_architectures function.
    """

    def test_no_architecture_filtering(self):
        """
        Test filtering if the remotes architectures field is the empty string or None.
        """
        release_file_architectures = "arm64 armel armhf i386 mips mips64el mipsel amd64"
        filtered_list = ["amd64", "arm64", "armel", "armhf", "i386", "mips", "mips64el", "mipsel"]
        distribution = "stable"

        self.assertEqual(
            _filter_split_architectures(release_file_architectures, None, distribution),
            filtered_list,
        )
        self.assertEqual(
            _filter_split_architectures(release_file_architectures, "", distribution),
            filtered_list,
        )

    def test_common_architecture_filtering(self):
        """
        Represents the common case where a remote asks to filter for one or two architectures.
        """
        release_file_architectures = "arm64 armel armhf i386 mips mips64el mipsel amd64"

        self.assertEqual(
            _filter_split_architectures(release_file_architectures, "amd64", "stable"),
            ["amd64"],
        )
        self.assertEqual(
            _filter_split_architectures(release_file_architectures, "amd64 i386", "stable"),
            ["amd64", "i386"],
        )

    def test_all_architecture_filtering(self):
        """
        This test checks that the all architecture is never removed if present.
        """
        release_file_architectures = "arm64 armel armhf i386 all mips64el mipsel amd64"

        self.assertEqual(
            _filter_split_architectures(release_file_architectures, "amd64", "stable"),
            ["all", "amd64"],
        )
        self.assertEqual(
            _filter_split_architectures(release_file_architectures, "amd64 i386", "stable"),
            ["all", "amd64", "i386"],
        )
        self.assertEqual(
            _filter_split_architectures(release_file_architectures, "amd64 all", "stable"),
            ["all", "amd64"],
        )
        self.assertEqual(
            _filter_split_architectures(release_file_architectures, "all amd64 i386", "stable"),
            ["all", "amd64", "i386"],
        )

    def test_superfluous_architecture_filtering(self):
        """
        This test checks what happens if the remote filters for architectures not in the release
        file.
        """
        release_file_architectures = "arm64 armel armhf i386 all mips64el mipsel amd64"

        expected_log_message = (
            "Architecture 'bogus' is not amongst the release file architectures 'arm64 armel armhf "
            "i386 all mips64el mipsel amd64' for distribution 'stable'. This could be valid, but "
            "more often indicates an error in the architectures field of the remote being used."
        )

        with self.assertLogs(level="WARNING") as captured:
            self.assertEqual(
                _filter_split_architectures(release_file_architectures, "amd64 bogus", "stable"),
                ["all", "amd64"],
            )
            self.assertEqual(
                _filter_split_architectures(release_file_architectures, "bogus", "stable"),
                ["all"],
            )
            release_file_architectures = "arm64 armel armhf i386 mips64el mipsel amd64"

            self.assertEqual(
                _filter_split_architectures(release_file_architectures, "bogus", "stable"),
                [],
            )
            self.assertEqual(len(captured.records), 3)
            self.assertEqual(captured.records[0].getMessage(), expected_log_message)


class TestComponentFiltering(TestCase):
    """
    Tests common as well as edge cases handled by the _filter_split_components function.
    """

    def test_no_component_filtering(self):
        """
        Test filtering if the remotes components field is the empty string or None.
        """
        release_file_components = "main contrib non-free"
        filtered_list = ["contrib", "main", "non-free"]
        distribution = "stable"

        self.assertEqual(
            _filter_split_components(release_file_components, None, distribution),
            filtered_list,
        )
        self.assertEqual(
            _filter_split_components(release_file_components, "", distribution),
            filtered_list,
        )

        # Also check that path prefixes are retained:
        release_file_components = "updates/main updates/contrib updates/non-free"
        filtered_list = ["updates/contrib", "updates/main", "updates/non-free"]
        distribution = "stable/updates"

        self.assertEqual(
            _filter_split_components(release_file_components, None, distribution),
            filtered_list,
        )
        self.assertEqual(
            _filter_split_components(release_file_components, "", distribution),
            filtered_list,
        )

    def test_common_component_filtering(self):
        """
        Represents the common case where a remote asks to filter for one or two compoents.
        """
        release_file_components = "main contrib non-free"

        self.assertEqual(
            _filter_split_components(release_file_components, "main", "stable"), ["main"]
        )
        self.assertEqual(
            _filter_split_components(release_file_components, "main contrib", "stable"),
            ["contrib", "main"],
        )

    def test_path_prefix_component_filtering(self):
        """
        This test checks that users can filter both by specifying the components they want with as
        well as without path prefixes.
        """
        release_file_components = "updates/main updates/contrib updates/non-free"
        distribution = "stable/updates"

        self.assertEqual(
            _filter_split_components(release_file_components, "main contrib", distribution),
            ["updates/contrib", "updates/main"],
        )
        remote_components = "updates/main updates/contrib"
        self.assertEqual(
            _filter_split_components(release_file_components, remote_components, distribution),
            ["updates/contrib", "updates/main"],
        )

    def test_superfluous_component_filtering(self):
        """
        This test checks what happens if the remote filters for components not in the release file.
        """
        expected_log_message = (
            "Component 'bogus' is not amongst the release file components 'main contrib non-free' "
            "for distribution 'stable'. This could be valid, but more often indicates an error in "
            "the components field of the remote being used."
        )

        with self.assertLogs(level="WARNING") as captured:
            release_file_components = "main contrib non-free"
            self.assertEqual(
                _filter_split_components(release_file_components, "bogus", "stable"), []
            )
            self.assertEqual(
                _filter_split_components(release_file_components, "main bogus", "stable"), ["main"]
            )
            release_file_components = "updates/main updates/contrib updates/non-free"
            self.assertEqual(
                _filter_split_components(release_file_components, "main bogus", "stable/updates"),
                ["updates/main"],
            )

            self.assertEqual(len(captured.records), 3)
            self.assertEqual(captured.records[0].getMessage(), expected_log_message)
