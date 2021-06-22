from django.test import TestCase

from pulp_deb.app.tasks.synchronizing import _filter_split_architectures, _filter_split_components


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
