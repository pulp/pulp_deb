from collections import deque
from gettext import gettext as _

from debian.deb822 import PkgRelation
from debian.debian_support import Version
from django.db.models import Q

from pulp_deb.app.models import Package


class DependencySolveError(Exception):
    """Raised when a transitive dependency cannot be satisfied from the source repository."""


_OP_FUNCS = {
    ">=": lambda a, b: a >= b,
    ">>": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<<": lambda a, b: a < b,
    "=": lambda a, b: a == b,
}


def _parse_relations(*depends_strings):
    combined = ", ".join(s for s in depends_strings if s)
    if not combined.strip():
        return []
    try:
        return PkgRelation.parse_relations(combined)
    except Exception:
        return []


def _version_satisfies(pkg_version, constraint):
    if not constraint:
        return True
    op, target = constraint
    return _OP_FUNCS.get(op, lambda a, b: False)(Version(pkg_version), Version(target))


def _candidates_for(alt, package_qs, pkg_arch=None):
    name = alt["name"]
    qs = package_qs.filter(package=name)
    alt_arch = alt.get("arch")
    if alt_arch:
        qs = qs.filter(architecture=alt_arch)
    elif pkg_arch:
        # Restrict deps to the consumer's arch or arch-independent (`all`).
        qs = qs.filter(Q(architecture=pkg_arch) | Q(architecture="all"))
    return qs


def _find_satisfier(alternative, package_qs, pkg_arch=None):
    """Best Package satisfying a single OR-alternative (direct hit or via Provides)."""
    constraint = alternative.get("version")

    direct = list(_candidates_for(alternative, package_qs, pkg_arch))
    direct.sort(key=lambda p: Version(p.version), reverse=True)
    for pkg in direct:
        if _version_satisfies(pkg.version, constraint):
            return pkg

    # Provides: a Package P providing the name we need.  Versioned Provides
    # are rare; we honour them when present, otherwise treat as unversioned.
    name = alternative["name"]
    provides_qs = package_qs.exclude(provides__isnull=True).exclude(provides="")
    if pkg_arch:
        provides_qs = provides_qs.filter(Q(architecture=pkg_arch) | Q(architecture="all"))
    for pkg in provides_qs:
        for or_group in _parse_relations(pkg.provides):
            for prov in or_group:
                if prov["name"] != name:
                    continue
                prov_version = prov.get("version")
                if not constraint:
                    return pkg
                if (
                    prov_version
                    and prov_version[0] == "="
                    and _version_satisfies(prov_version[1], constraint)
                ):
                    return pkg
                # Unversioned Provides cannot satisfy a versioned dependency per policy.
    return None


def _relation_satisfied_by_set(relation, package_qs, pkg_arch=None):
    return any(_find_satisfier(alt, package_qs, pkg_arch) is not None for alt in relation)


def _packages_in(repo_version):
    if repo_version is None:
        return Package.objects.none()
    return Package.objects.filter(
        pk__in=repo_version.content.filter(pulp_type=Package.get_pulp_type()).only("pk")
    )


def _format_relation(relation):
    parts = []
    for alt in relation:
        s = alt["name"]
        if alt.get("arch"):
            s += ":{}".format(alt["arch"])
        if alt.get("version"):
            s += " ({} {})".format(*alt["version"])
        parts.append(s)
    return " | ".join(parts)


def solve_dependencies(initial_packages, source_repo_version, dest_base_version=None):
    """BFS over Depends + Pre-Depends. Returns the set of Package pks to copy.

    A relation already satisfied by ``dest_base_version`` is skipped; otherwise
    the newest satisfying Package in ``source_repo_version`` is chosen, then
    walked transitively.  Raises :class:`DependencySolveError` on unsatisfiable
    relations.
    """
    source_pkgs = _packages_in(source_repo_version)
    dest_pkgs = _packages_in(dest_base_version)

    seen = set()
    queue = deque(initial_packages)
    final = set()

    while queue:
        pkg = queue.popleft()
        if pkg.pk in seen:
            continue
        seen.add(pkg.pk)
        final.add(pkg.pk)

        for relation in _parse_relations(pkg.depends, pkg.pre_depends):
            if dest_base_version is not None and _relation_satisfied_by_set(
                relation, dest_pkgs, pkg.architecture
            ):
                continue

            chosen = None
            for alt in relation:
                chosen = _find_satisfier(alt, source_pkgs, pkg.architecture)
                if chosen:
                    break

            if chosen is None:
                raise DependencySolveError(
                    _(
                        "Cannot solve dependency for {pkg}: "
                        "'{rel}' is not satisfiable in source repository version {srv}"
                    ).format(
                        pkg=pkg.name,
                        rel=_format_relation(relation),
                        srv=source_repo_version.pk,
                    )
                )

            if chosen.pk not in seen:
                queue.append(chosen)

    return final
