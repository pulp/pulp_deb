import pytest


@pytest.mark.parallel
class TestPackageVersionFilter:
    @pytest.fixture(scope="class")
    def repository(self, deb_init_and_sync):
        _repository, _ = deb_init_and_sync()
        return _repository

    @pytest.mark.parametrize(
        "filter,count",
        [
            pytest.param({"version": "1.0"}, 4, id="exact"),
            pytest.param({"version__ne": "1.0"}, 0, id="ne"),
            pytest.param({"version__gt": "1.0~"}, 4, id="gt with tilde"),
            pytest.param({"version__gt": "1.0"}, 0, id="gt"),
            pytest.param({"version__gt": "1.0+"}, 0, id="gt with plus"),
            pytest.param({"version__gte": "1.0~"}, 4, id="gte with tilde"),
            pytest.param({"version__gte": "1.0"}, 4, id="gte"),
            pytest.param({"version__gte": "1.0+"}, 0, id="gte with plus"),
            pytest.param({"version__lt": "1.0~"}, 0, id="lt with tilde"),
            pytest.param({"version__lt": "1.0"}, 0, id="lt"),
            pytest.param({"version__lt": "1.0+"}, 4, id="lt with plus"),
            pytest.param({"version__lte": "1.0~"}, 0, id="lte with tilde"),
            pytest.param({"version__lte": "1.0"}, 4, id="lte"),
            pytest.param({"version__lte": "1.0+"}, 4, id="lte with plus"),
        ],
    )
    def test_returns_a_certain_count_of_entries(self, deb_bindings, repository, filter, count):
        """Verify that Packages can be filtered by versions."""
        # Query content units with filters
        result = deb_bindings.ContentPackagesApi.list(
            repository_version=repository.latest_version_href, **filter
        )
        assert result.count == count
