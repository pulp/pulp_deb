"""Tests for checkpoint distribution and publications."""

from datetime import datetime, timedelta
import re
from time import sleep
from urllib.parse import urlparse
import uuid
from aiohttp import ClientResponseError
import pytest
from pulp_deb.tests.functional.constants import DEB_PACKAGE_RELPATH
from pulp_deb.tests.functional.utils import get_local_package_absolute_path


@pytest.fixture(scope="class")
def setup(
    deb_repository_factory,
    deb_publication_factory,
    deb_distribution_factory,
    deb_package_factory,
    apt_repository_api,
):
    def create_publication(repo, checkpoint):
        package_upload_params = {
            "file": str(get_local_package_absolute_path(DEB_PACKAGE_RELPATH)),
            "relative_path": DEB_PACKAGE_RELPATH,
            "distribution": str(uuid.uuid4()),
            "component": str(uuid.uuid4()),
            "repository": repo.pulp_href,
        }
        deb_package_factory(**package_upload_params)

        repo = apt_repository_api.read(repo.pulp_href)
        return deb_publication_factory(repo, checkpoint=checkpoint)

    repo = deb_repository_factory()
    distribution = deb_distribution_factory(repository=repo, checkpoint=True)

    pubs = []
    pubs.append(create_publication(repo, False))
    sleep(1)
    pubs.append(create_publication(repo, True))
    sleep(1)
    pubs.append(create_publication(repo, False))
    sleep(1)
    pubs.append(create_publication(repo, True))
    sleep(1)
    pubs.append(create_publication(repo, False))

    return pubs, distribution


@pytest.fixture
def checkpoint_url(distribution_base_url):
    def _checkpoint_url(distribution, timestamp):
        distro_base_url = distribution_base_url(distribution.base_url)
        return f"{distro_base_url}{_format_checkpoint_timestamp(timestamp)}/"

    return _checkpoint_url


def _format_checkpoint_timestamp(timestamp):
    return datetime.strftime(timestamp, "%Y%m%dT%H%M%SZ")


class TestCheckpointDistribution:

    def test_base_path_lists_checkpoints(self, setup, http_get, distribution_base_url):
        pubs, distribution = setup

        response = http_get(distribution_base_url(distribution.base_url)).decode("utf-8")

        checkpoints_ts = set(re.findall(r"\d{8}T\d{6}Z", response))
        assert len(checkpoints_ts) == 2
        assert _format_checkpoint_timestamp(pubs[1].pulp_created) in checkpoints_ts
        assert _format_checkpoint_timestamp(pubs[3].pulp_created) in checkpoints_ts

    def test_no_trailing_slash_is_redirected(self, setup, http_get, distribution_base_url):
        """Test checkpoint listing when path doesn't end with a slash."""

        pubs, distribution = setup

        response = http_get(distribution_base_url(distribution.base_url[:-1])).decode("utf-8")
        checkpoints_ts = set(re.findall(r"\d{8}T\d{6}Z", response))

        assert len(checkpoints_ts) == 2
        assert _format_checkpoint_timestamp(pubs[1].pulp_created) in checkpoints_ts
        assert _format_checkpoint_timestamp(pubs[3].pulp_created) in checkpoints_ts

    def test_exact_timestamp_is_served(self, setup, http_get, checkpoint_url):
        pubs, distribution = setup

        pub_1_url = checkpoint_url(distribution, pubs[1].pulp_created)
        response = http_get(pub_1_url).decode("utf-8")

        assert f"<h1>Index of {urlparse(pub_1_url).path}</h1>" in response

    def test_invalid_timestamp_returns_404(self, setup, http_get, distribution_base_url):
        _, distribution = setup
        with pytest.raises(ClientResponseError) as exc:
            http_get(distribution_base_url(f"{distribution.base_url}invalid_ts/"))

        assert exc.value.status == 404

        with pytest.raises(ClientResponseError) as exc:
            http_get(distribution_base_url(f"{distribution.base_url}20259928T092752Z/"))

        assert exc.value.status == 404

    def test_non_checkpoint_timestamp_is_redirected(self, setup, http_get, checkpoint_url):
        pubs, distribution = setup
        # Using a non-checkpoint publication timestamp
        pub_3_url = checkpoint_url(distribution, pubs[3].pulp_created)
        pub_4_url = checkpoint_url(distribution, pubs[4].pulp_created)

        response = http_get(pub_4_url).decode("utf-8")
        assert f"<h1>Index of {urlparse(pub_3_url).path}</h1>" in response

        # Test without a trailing slash
        response = http_get(pub_4_url[:-1]).decode("utf-8")
        assert f"<h1>Index of {urlparse(pub_3_url).path}</h1>" in response

    def test_arbitrary_timestamp_is_redirected(self, setup, http_get, checkpoint_url):
        pubs, distribution = setup
        pub_1_url = checkpoint_url(distribution, pubs[1].pulp_created)
        arbitrary_url = checkpoint_url(distribution, pubs[1].pulp_created + timedelta(seconds=1))

        response = http_get(arbitrary_url).decode("utf-8")
        assert f"<h1>Index of {urlparse(pub_1_url).path}</h1>" in response

        # Test without a trailing slash
        response = http_get(arbitrary_url[:-1]).decode("utf-8")
        assert f"<h1>Index of {urlparse(pub_1_url).path}</h1>" in response

    def test_current_timestamp_serves_latest_checkpoint(self, setup, http_get, checkpoint_url):
        pubs, distribution = setup
        pub_3_url = checkpoint_url(distribution, pubs[3].pulp_created)
        now_url = checkpoint_url(distribution, datetime.now())

        response = http_get(now_url).decode("utf-8")

        assert f"<h1>Index of {urlparse(pub_3_url).path}</h1>" in response

    def test_before_first_timestamp_returns_404(self, setup, http_get, checkpoint_url):
        pubs, distribution = setup
        pub_0_url = checkpoint_url(distribution, pubs[0].pulp_created)

        with pytest.raises(ClientResponseError) as exc:
            http_get(pub_0_url).decode("utf-8")

        assert exc.value.status == 404

    def test_future_timestamp_returns_404(self, setup, http_get, checkpoint_url):
        _, distribution = setup
        url = checkpoint_url(distribution, datetime.now() + timedelta(days=1))

        with pytest.raises(ClientResponseError) as exc:
            http_get(url).decode("utf-8")

        assert exc.value.status == 404
