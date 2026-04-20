"""Scheduled reminders disguised as tests — these exist to nag, not to verify behavior."""

from importlib.metadata import requires as pkg_requires
from packaging.requirements import Requirement
from packaging.version import Version


def _pulpcore_lower_bound():
    deps = pkg_requires("pulp-deb") or []
    pulpcore_spec = next(d for d in deps if d.split(";")[0].strip().startswith("pulpcore"))
    pulpcore_spec = pulpcore_spec.split(";")[0].strip()
    req = Requirement(pulpcore_spec)
    lower_bounds = [spec.version for spec in req.specifier if spec.operator in (">=", ">")]
    if not lower_bounds:
        raise ValueError(f"Could not find a lower bound in: {pulpcore_spec!r}")
    return Version(max(lower_bounds, key=Version))


def test_pulpcore_lower_bound_below_3_115():
    """
    This is a reminder mechanism, not a functional test.

    Once the pulpcore lower bound in pyproject.toml reaches 3.115, the
    distribution/publication phase-out work tracked in
    https://github.com/pulp/pulp_deb/issues/1430 should be finished and this
    test should be removed.

    If this test is failing, poke Pedro (@pedro-brochado on Matrix) to complete
    the phase-out and delete this test.
    """
    lower_bound = _pulpcore_lower_bound()
    assert lower_bound < Version("3.115"), (
        f"pulpcore lower bound is {lower_bound}, which is >= 3.115. "
        "This is a reminder that the distribution/publication phase-out "
        "(https://github.com/pulp/pulp_deb/issues/1430) should now be "
        "completed. Poke @pedro-brochado on Matrix to finish the phase-out "
        "and remove this test."
    )
