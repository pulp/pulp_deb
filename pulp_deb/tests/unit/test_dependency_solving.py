from unittest.mock import MagicMock, patch

import pytest

from pulp_deb.app.tasks.dependency_solving import (
    DependencySolveError,
    _find_satisfier,
    _parse_relations,
    _version_satisfies,
    solve_dependencies,
)


@pytest.fixture
def pkg():
    """Build a Package mock with the fields the solver reads."""

    def _make(name, version, depends=None, provides=None, pk=None, arch="amd64"):
        p = MagicMock()
        p.package = name
        p.version = version
        p.architecture = arch
        p.depends = depends
        p.pre_depends = None
        p.provides = provides
        p.pk = pk if pk is not None else id(p)
        p.name = "{}_{}_{}".format(name, version, arch)
        return p

    return _make


@pytest.fixture
def qs():
    """Build a Django QuerySet stub supporting filter()/exclude() and iteration."""

    def _make(items):
        q = MagicMock()
        q._items = list(items)

        def _filter(*args, **kwargs):
            out = list(q._items)
            for key, val in kwargs.items():
                field = key.split("__")[0]
                out = [p for p in out if getattr(p, field, None) == val]
            return _make(out)

        q.filter.side_effect = _filter
        q.exclude.side_effect = lambda **kw: _make(
            [p for p in q._items if not all(getattr(p, k, None) == v for k, v in kw.items())]
        )
        q.__iter__.side_effect = lambda: iter(q._items)
        q.__bool__.side_effect = lambda: bool(q._items)
        q.none.return_value = _make([]) if items else q
        return q

    return _make


def test_parses_or_group_with_version():
    rels = _parse_relations("libfoo (>= 1.2.3) | libbar")
    assert len(rels) == 1 and len(rels[0]) == 2
    assert rels[0][0]["version"] == (">=", "1.2.3")
    assert rels[0][1]["name"] == "libbar"


def test_version_satisfies_respects_epoch():
    # Epoch wins over upstream version per Debian policy.
    assert _version_satisfies("2:1.0", (">=", "1:9.9"))
    assert not _version_satisfies("1.0", (">=", "2.0"))


def test_find_satisfier_picks_newest(pkg, qs):
    pkgs = [pkg("libssl3", v) for v in ("3.0.7-25", "3.0.7-27", "3.0.7-26")]
    assert _find_satisfier({"name": "libssl3"}, qs(pkgs)).version == "3.0.7-27"


def test_find_satisfier_via_provides(pkg, qs):
    pkgs = [pkg("libssl3", "3.0", provides="libssl1.1")]
    assert _find_satisfier({"name": "libssl1.1"}, qs(pkgs)).package == "libssl3"
    # Unversioned Provides cannot satisfy a versioned dep.
    assert _find_satisfier({"name": "libssl1.1", "version": (">=", "1.1.1")}, qs(pkgs)) is None


def test_solver_walks_chain(pkg, qs):
    a = pkg("a", "1.0", depends="b", pk=1)
    b = pkg("b", "1.0", depends="c", pk=2)
    c = pkg("c", "1.0", pk=3)
    with patch("pulp_deb.app.tasks.dependency_solving.Package") as Pkg:
        Pkg.objects.filter.return_value = qs([a, b, c])
        Pkg.get_pulp_type.return_value = "deb.package"
        srv = MagicMock()
        srv.content.filter.return_value.only.return_value = qs([a, b, c])
        assert solve_dependencies([a], srv, dest_base_version=None) == {1, 2, 3}


def test_solver_skips_deps_already_in_dest(pkg, qs):
    a = pkg("a", "1.0", depends="b (>= 1.0)", pk=10)
    b = pkg("b", "1.0", pk=11)
    with patch("pulp_deb.app.tasks.dependency_solving.Package") as Pkg:
        Pkg.objects.filter.side_effect = [qs([a, b]), qs([b])]
        srv, dest = MagicMock(), MagicMock()
        srv.content.filter.return_value.only.return_value = qs([a, b])
        dest.content.filter.return_value.only.return_value = qs([b])
        assert solve_dependencies([a], srv, dest_base_version=dest) == {10}


def test_solver_raises_on_unsatisfiable(pkg, qs):
    a = pkg("a", "1.0", depends="missing-pkg (>= 1.0)", pk=20)
    with patch("pulp_deb.app.tasks.dependency_solving.Package") as Pkg:
        Pkg.objects.filter.return_value = qs([a])
        srv = MagicMock()
        srv.pk = 99
        srv.content.filter.return_value.only.return_value = qs([a])
        with pytest.raises(DependencySolveError):
            solve_dependencies([a], srv)
