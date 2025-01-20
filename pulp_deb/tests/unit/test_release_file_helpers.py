import pytest
from unittest.mock import MagicMock, patch
from django.test import override_settings

from pulp_deb.app.tasks.synchronizing import (
    MissingReleaseFileField,
    _collect_release_artifacts,
    _parse_release_file_attributes,
)


@pytest.fixture
def mock_d_content():
    """
    Return a mock of the 'd_content' object.
    """
    d_content = MagicMock()
    d_content.content.distribution = "buster"
    d_content.content.codename = None
    d_content.content.suite = None
    d_content.content.components = None
    d_content.content.architectures = None
    return d_content


@pytest.fixture
def mock_main_artifact(tmp_path):
    """
    Create a fixture that has .file.open(...) returning a real file object.
    We'll let the test function write the file content as needed.
    """
    artifact = MagicMock()
    fake_file_path = tmp_path / "Release"
    artifact._fake_file_path = fake_file_path

    def _open(mode="rb"):
        return open(fake_file_path, mode)

    artifact.file.open.side_effect = _open

    return artifact


def test_collect_release_artifacts_all_found(mock_d_content):
    """
    Test if release artifacts paths are correctly collected.
    """
    mock_d_artifact_release = MagicMock()
    mock_d_artifact_release.relative_path = "some/Release"
    mock_d_artifact_gpg = MagicMock()
    mock_d_artifact_gpg.relative_path = "some/Release.gpg"
    mock_d_artifact_inrelease = MagicMock()
    mock_d_artifact_inrelease.relative_path = "some/InRelease"

    mock_d_content.d_artifacts = [
        mock_d_artifact_release,
        mock_d_artifact_gpg,
        mock_d_artifact_inrelease,
    ]

    release_da, release_gpg_da, inrelease_da = _collect_release_artifacts(mock_d_content)
    assert release_da == mock_d_artifact_release
    assert release_gpg_da == mock_d_artifact_gpg
    assert inrelease_da == mock_d_artifact_inrelease


def test_collect_release_artifacts_none_found(mock_d_content):
    """
    Test that unrelated artifacts do not set the release files.
    """
    # None of Release, Release.gpg or InRelease
    mock_artifact_1 = MagicMock()
    mock_artifact_1.relative_path = "something/else"
    mock_artifact_2 = MagicMock()
    mock_artifact_2.relative_path = "else/something"

    mock_d_content.d_artifacts = [mock_artifact_1, mock_artifact_2]

    release_da, release_gpg_da, inrelease_da = _collect_release_artifacts(mock_d_content)
    assert release_da is None
    assert release_gpg_da is None
    assert inrelease_da is None


def test_collect_release_artifacts_some_found(mock_d_content):
    """
    Test that the correct artifact gets returned if there are some missing.
    """
    mock_artifact_release = MagicMock()
    mock_artifact_release.relative_path = "dist/Release"
    mock_d_content.d_artifacts = [mock_artifact_release]

    release_da, release_gpg_da, inrelease_da = _collect_release_artifacts(mock_d_content)
    assert release_da == mock_artifact_release
    assert release_gpg_da is None
    assert inrelease_da is None


@pytest.mark.parametrize("dist_ends_slash", [False, True])
def test_parse_release_file_attributes_normal(mock_d_content, mock_main_artifact, dist_ends_slash):
    """
    Test if a valid Release file is returned.
    """
    if dist_ends_slash:
        mock_d_content.content.distribution = "buster/"
    else:
        mock_d_content.content.distribution = "buster"

    data = (
        "Codename: buster\n"
        "Suite: stable\n"
        "Components: main contrib\n"
        "Architectures: amd64 i386\n"
    )
    mock_main_artifact._fake_file_path.write_text(data)

    _parse_release_file_attributes(mock_d_content, mock_main_artifact)

    assert mock_d_content.content.codename == "buster"
    assert mock_d_content.content.suite == "stable"
    assert mock_d_content.content.components == "main contrib"
    assert mock_d_content.content.architectures == "amd64 i386"


@pytest.mark.parametrize("field_name", ["Components", "Architectures"])
def test_parse_release_file_attributes_missing_fields_nonflat(
    field_name, mock_d_content, mock_main_artifact
):
    """
    If a field is missing in a non flat repository, then we raise MissingReleaseFileField.
    This applies for "components" or "architectures" if they are missing from the Release file.
    """
    mock_d_content.content.distribution = "buster"

    if field_name == "Components":
        data = "Codename: buster\n" "Suite: stable\n" "Architectures: amd64 i386\n"
    else:
        data = "Codename: buster\n" "Suite: stable\n" "Components: main contrib\n"

    mock_main_artifact._fake_file_path.write_text(data)

    with pytest.raises(MissingReleaseFileField) as exc:
        _parse_release_file_attributes(mock_d_content, mock_main_artifact)

    assert field_name in str(exc.value)


def test_parse_release_file_attributes_missing_fields_flat_repo(mock_d_content, mock_main_artifact):
    """
    If fields are missing in a flat repository, we log a warning and set them to "".
    """
    mock_d_content.content.distribution = "buster/"

    data = "Codename: buster\n" "Suite: stable\n"
    mock_main_artifact._fake_file_path.write_text(data)

    with patch("pulp_deb.app.tasks.synchronizing.log.warning") as mock_log_warn:
        _parse_release_file_attributes(mock_d_content, mock_main_artifact)

    assert mock_d_content.content.components == ""
    assert mock_d_content.content.architectures == ""

    assert mock_log_warn.call_count == 2
    calls = [c[0][0] for c in mock_log_warn.call_args_list]
    assert "contains no 'Components' field" in calls[0]
    assert "contains no 'Architectures' field" in calls[1]


@override_settings(PERMISSIVE_SYNC=True)
def test_parse_release_file_attributes_permissive_component(mock_d_content, mock_main_artifact):
    """
    Test if PERMISSIVE_SYNC=True allows for the "Component" field in a Release file to be parsed.
    """
    mock_d_content.content.distribution = "buster"

    data = "Codename: buster\n" "Suite: stable\n" "Component: main\n" "Architectures: amd64\n"
    mock_main_artifact._fake_file_path.write_text(data)

    _parse_release_file_attributes(mock_d_content, mock_main_artifact)

    assert mock_d_content.content.components == "main"
    assert mock_d_content.content.architectures is not None


@override_settings(PERMISSIVE_SYNC=True)
def test_parse_release_file_attributes_permissive_architecture(mock_d_content, mock_main_artifact):
    """
    Test if PERMISSIVE_SYNC=True allows for the "Architecture" field in a Release file to be parsed.
    """
    mock_d_content.content.distribution = "buster"
    data = "Codename: buster\n" "Suite: stable\n" "Components: main\n" "Architecture: amd64 i386\n"
    mock_main_artifact._fake_file_path.write_text(data)

    _parse_release_file_attributes(mock_d_content, mock_main_artifact)

    assert mock_d_content.content.components is not None
    assert mock_d_content.content.architectures == "amd64 i386"


@override_settings(PERMISSIVE_SYNC=False)
@pytest.mark.parametrize("field_name", ["Components", "Architectures"])
def test_parse_release_file_attributes_permissive_disabled_compoent(
    mock_d_content, mock_main_artifact, field_name
):
    """
    Test whether PERMISSIVE_SYNC=False correctly raises MissingReleaseFileField,
    if fields in Release are called "Component" or "Architecture" and not their plurals.
    """
    mock_d_content.content.distribution = "buster"

    if field_name == "Components":
        data = "Codename: buster\n" "Suite: stable\n" "Component: main\n" "Architectures: amd64\n"
    else:
        data = "Codename: buster\n" "Suite: stable\n" "Components: main\n" "Architecture: amd64\n"

    mock_main_artifact._fake_file_path.write_text(data)

    with pytest.raises(MissingReleaseFileField) as exc:
        _parse_release_file_attributes(mock_d_content, mock_main_artifact)
    assert f"missing the required field '{field_name}'" in str(exc.value)
