from pulp_deb.app.models import Package


VERSIONS = [
    "1",
    "1.0~asdf",
    "1.0",
    "1.0-1~0",
    "1.0-1~1",
    "1.0-1",
    "1.0-1+1",
    "1.0-1+1.2",
    "1.0-1+2",
    "1.0-1+12",
    "1.0-1+a",
    "1.0-1+b~",
    "1.0-1+b",
    "2",
    "2:1.0",
    "11:1.0",
]


def test_sort_debver(db):
    for version in reversed(VERSIONS):
        Package.objects.create(relative_path=f"test_sort_debver-{version}", version=version)

    sorted_versions = (
        Package.objects.filter(relative_path__startswith="test_sort_debver-")
        .order_by("version")
        .values_list("version", flat=True)
    )

    assert list(sorted_versions) == VERSIONS
