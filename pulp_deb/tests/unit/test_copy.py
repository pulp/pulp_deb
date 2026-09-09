"""Unit tests for copy_content in the copy task."""

import json
import re
import uuid
from dataclasses import dataclass

import pytest

from pulp_deb.app.models import AptRepository
from pulp_deb.app.tasks.copy import copy_content
from pulp_deb.tests.unit.utils.content_factory import RepoContentFactory
from pulp_deb.tests.unit.utils.query_recorder import QueryRecorder, detect_n1


class GrowthProfiles:
    """Builders for content selections/relationships, one repo version each.

    Each builder takes (count, repo_name) and returns (repo_version, content_ids to select for
    copy, expected structural content pks pulled in on top of the explicit selection).
    """

    @staticmethod
    def packages(count, repo_name):
        """Grow the number of packages explicitly selected for copy (flat, unstructured)."""
        with RepoContentFactory(repo_name=repo_name) as repo:
            names = [f"{repo_name}-pkg-{i}" for i in range(count)]
            package_pks = repo.add_packages(names)
        return repo.version, package_pks, set()

    @staticmethod
    def packages_within_release_component(count, repo_name):
        """Grow the packages belonging to one Release/ReleaseComponent/ReleaseArchitecture.

        Only the packages themselves are explicitly selected; the structured copy is expected
        to pull in the Release, ReleaseComponent, ReleaseArchitecture and the
        PackageReleaseComponent join rows on top of that.
        """
        with RepoContentFactory(repo_name=repo_name) as repo:
            release_pk = repo.add_release(distribution=repo_name)
            component_pk = repo.add_release_component(distribution=repo_name, component="main")
            architecture_pk = repo.add_release_architecture(
                distribution=repo_name, architecture="amd64"
            )
            names = [f"{repo_name}-pkg-{i}" for i in range(count)]
            package_pks = repo.add_packages(names, architecture="amd64")
            for package_pk in package_pks:
                repo.add_package_release_component(package_pk, component_pk)
        return repo.version, package_pks, {release_pk, component_pk, architecture_pk}

    @staticmethod
    def packages_across_release_components(count, repo_name):
        """Grow the number of DISTINCT ReleaseComponents packages are spread across.

        One package per component, same distribution/architecture. Isolates
        `release_component_ids` -> `release_component_content_qs` growth in
        find_structured_publish_content(), independent of package count itself.
        """
        with RepoContentFactory(repo_name=repo_name) as repo:
            release_pk = repo.add_release(distribution=repo_name)
            architecture_pk = repo.add_release_architecture(
                distribution=repo_name, architecture="amd64"
            )
            component_pks = set()
            package_pks = []
            for i in range(count):
                component_pk = repo.add_release_component(
                    distribution=repo_name, component=f"component-{i}"
                )
                component_pks.add(component_pk)
                package_pk = repo.add_packages([f"{repo_name}-pkg-{i}"], architecture="amd64")[0]
                repo.add_package_release_component(package_pk, component_pk)
                package_pks.append(package_pk)
        return repo.version, package_pks, {release_pk, architecture_pk} | component_pks

    @staticmethod
    def packages_across_architectures(count, repo_name):
        """Grow the number of DISTINCT architectures packages are spread across.

        One architecture per package, same distribution/component. Isolates the
        `architectures` list -> `architecture_qs` growth in
        find_structured_publish_content(), independent of package count itself.
        """
        with RepoContentFactory(repo_name=repo_name) as repo:
            release_pk = repo.add_release(distribution=repo_name)
            component_pk = repo.add_release_component(distribution=repo_name, component="main")
            architecture_pks = set()
            package_pks = []
            for i in range(count):
                architecture = f"arch-{i}"
                architecture_pk = repo.add_release_architecture(
                    distribution=repo_name, architecture=architecture
                )
                architecture_pks.add(architecture_pk)
                package_pk = repo.add_packages([f"{repo_name}-pkg-{i}"], architecture=architecture)[
                    0
                ]
                repo.add_package_release_component(package_pk, component_pk)
                package_pks.append(package_pk)
        return repo.version, package_pks, {release_pk, component_pk} | architecture_pks

    @staticmethod
    def packages_across_distributions(count, repo_name):
        """Grow the number of DISTINCT distributions (Releases) packages are spread across.

        One distribution/component/architecture set per package. Isolates `distributions`
        -> `architecture_qs`/`release_qs` growth in find_structured_publish_content(),
        independent of package count itself.
        """
        with RepoContentFactory(repo_name=repo_name) as repo:
            release_pks = set()
            component_pks = set()
            architecture_pks = set()
            package_pks = []
            for i in range(count):
                distribution = f"{repo_name}-dist-{i}"
                release_pks.add(repo.add_release(distribution=distribution))
                component_pk = repo.add_release_component(
                    distribution=distribution, component="main"
                )
                component_pks.add(component_pk)
                architecture_pks.add(
                    repo.add_release_architecture(distribution=distribution, architecture="amd64")
                )
                package_pk = repo.add_packages([f"{repo_name}-pkg-{i}"], architecture="amd64")[0]
                repo.add_package_release_component(package_pk, component_pk)
                package_pks.append(package_pk)
        return repo.version, package_pks, release_pks | component_pks | architecture_pks

    PROFILES = {
        "packages": (packages, False),
        "packages_within_release_component": (packages_within_release_component, True),
        "packages_across_release_components": (packages_across_release_components, True),
        "packages_across_architectures": (packages_across_architectures, True),
        "packages_across_distributions": (packages_across_distributions, True),
    }


@dataclass
class CopyWorkflowResult:
    children: set
    resolved: set
    recorder: QueryRecorder


@dataclass
class IgnoreFromPath:
    pattern: str
    reason: str


def make_growth_candidate_filter(ignore_paths=None):
    """Build a get_queries() filter_fn matching non-ignored SELECTs with bound params."""
    ignore_paths = ignore_paths or []

    def is_growth_candidate(query) -> bool:
        if query.statement_type != "SELECT" or query.num_params == 0:
            return False
        if any(
            re.search(ignore.pattern, site) for ignore in ignore_paths for site in query.call_site
        ):
            return False
        return True

    return is_growth_candidate


def make_not_ignored_filter(ignore_paths=None):
    """Build a get_queries() filter_fn excluding queries matching one of `ignore_paths`."""
    ignore_paths = ignore_paths or []

    def not_ignored(query) -> bool:
        return not any(
            re.search(ignore.pattern, site) for ignore in ignore_paths for site in query.call_site
        )

    return not_ignored


class TestCopyContentBase:
    def call_copy_workflow(self, content_count: int, profile_name: str) -> CopyWorkflowResult:
        build, structured = GrowthProfiles.PROFILES[profile_name]
        repo_name = f"{profile_name}-{content_count}"
        version, ids, children = build(content_count, repo_name)
        dest_repo = AptRepository.objects.create(name=str(uuid.uuid4()))
        config = [
            {
                "source_repo_version": version.pk,
                "dest_repo": dest_repo.pk,
                "content": list(ids),
            }
        ]
        recorder = QueryRecorder()
        with recorder:
            copy_content(config, structured=structured, dependency_solving=False)
        dest_content = dest_repo.latest_version().content
        resolved = set(dest_content.values_list("pk", flat=True))
        return CopyWorkflowResult(children=children, resolved=resolved, recorder=recorder)

    @pytest.mark.parametrize("profile_name", GrowthProfiles.PROFILES.keys())
    @pytest.mark.django_db
    def test_query_count_is_size_invariant(self, profile_name, save_artifact):
        """copy_content() must issue the same NUMBER of queries regardless of how much content
        is being copied. A differing count for the same profile means an N+1 query bug (e.g. one
        query per referenced item in a Python loop), as opposed to a query whose own bound-param
        count merely grows - that's covered separately.
        """
        SMALL_COUNT = 20
        SCALE_FACTOR = 10
        LARGE_COUNT = SMALL_COUNT * SCALE_FACTOR
        IGNORE_PATHS = [
            IgnoreFromPath(
                pattern=r"pulp_deb/app/models/repository\.py:\d+ in handle_duplicate_releases",
                reason="needs further investigation on real impact",
            ),
        ]

        small = self.call_copy_workflow(SMALL_COUNT, profile_name)
        large = self.call_copy_workflow(LARGE_COUNT, profile_name)
        save_artifact(small.recorder.summary_text(include_sql=True), suffix="small")

        not_ignored = make_not_ignored_filter(IGNORE_PATHS)
        small_queries = small.recorder.get_queries(not_ignored)
        large_queries = large.recorder.get_queries(not_ignored)
        offenders = detect_n1(small_queries, large_queries)

        passed = not offenders  # keeps error msg clean
        assert passed, (
            json.dumps(offenders, indent=4)
            + f"\n\n[{profile_name}] {len(offenders)} quer(ies) fired a different number of "
            f"times between runs:\n"
        )

    @pytest.mark.parametrize("profile_name", GrowthProfiles.PROFILES.keys())
    @pytest.mark.django_db
    def test_scales_sublinearly_across_content_relationships(self, profile_name, save_artifact):
        """The SQL param count from the COPY API should remain stable with input grow.

        A query with growing param count rate means it could reach postgres's limit of 65532
        for big enough input.
        """
        IGNORE_PATHS = [
            IgnoreFromPath(
                pattern=r"pulpcore/app/models/repository\.py:\d+ in __exit__",
                reason="should be fixed in pulpcore",
            ),
            IgnoreFromPath(
                pattern=r"pulp_deb/app/models/repository\.py:\d+ in handle_duplicate_releases",
                reason="needs further investigation on real impact",
            ),
        ]

        SMALL_COUNT = 20
        SCALE_FACTOR = 10
        LARGE_COUNT = SMALL_COUNT * SCALE_FACTOR
        THRESHOLD_FACTOR = 1.1  # only tolerate small growth rates
        small = self.call_copy_workflow(SMALL_COUNT, profile_name)
        large = self.call_copy_workflow(LARGE_COUNT, profile_name)

        small_summary = small.recorder.summary_text(include_sql=True)
        save_artifact(small_summary, suffix="small")

        assert small.children < small.resolved
        assert large.children < large.resolved

        is_growth_candidate = make_growth_candidate_filter(IGNORE_PATHS)
        small_queries = small.recorder.get_queries(is_growth_candidate)
        large_queries = large.recorder.get_queries(is_growth_candidate)

        failures = []
        for small_query, large_query in zip(small_queries, large_queries):
            growth_rate = large_query.num_params / small_query.num_params
            if growth_rate >= THRESHOLD_FACTOR:
                failures.append({**large_query.summary, "growth_rate": round(growth_rate, 2)})

        passed = not failures  # keeps error msg clean
        assert passed, (
            json.dumps(failures, indent=4)
            + f"\n\n[{profile_name}] {len(failures)} quer(ies) grew params count too fast:\n"
        )
