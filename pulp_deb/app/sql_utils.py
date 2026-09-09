from collections.abc import Iterable

from django.db.models import F, Field, ForeignKey, Func, Q
from django.db.models.lookups import Lookup

from pulpcore.plugin.models import Content, RepositoryVersion
from pulpcore.plugin.util import get_domain_pk


class _AnyArray(Lookup):
    """PostgreSQL ``= ANY(%s)`` lookup. Passes the list as one array parameter."""

    lookup_name = "any_array"

    def get_prep_lookup(self):
        return [self.lhs.output_field.get_prep_value(v) for v in self.rhs]

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        return f"{lhs} = ANY(%s)", lhs_params + [list(self.rhs)]


Field.register_lookup(_AnyArray)
ForeignKey.register_lookup(_AnyArray)


def safe_in(field_name: str, values: Iterable) -> Q:
    """Passes a non-query-set iterable of values a single array parameter.

    This ensures selections such as `pk__in=(1,2, ..., n)` doesn't generate a SQL with
    n query params (e.g, `WHERE pk in (%s, %s, ..., %s)`), but a single %s which is a
    postgres array of values. This prevent hitting the 65535 query param limit on the
    extended query protocol:

    <https://www.postgresql.org/docs/current/protocol-flow.html#PROTOCOL-FLOW-EXT-QUERY>

    Use this if you need to pass a potentially large list of materialized values into
    a `{field}__in` filter. If the values are purely from queryset, this is not required.
    """
    if not isinstance(values, (list, set, tuple, frozenset)):
        values_type = type(values)
        raise TypeError(
            f"This is designed to be used with in-memory iterable of values. Got: {values_type}"
        )
    return Q(**{f"{field_name}__any_array": list(values)})


def get_content_in_repoversion(repo_version, content_qs=None, pulp_type=None, cast=False):
    """Get content present in repo_version.

    Args:
        repo_version: RepositoryVersion to restrict to.
        content_qs: Base queryset to restrict, defaults to Content.objects.
        pulp_type: Restrict to this pulp_type.
        cast: If True, query the specific Content subclass for pulp_type instead of base
            Content rows, so its own fields (not just pk) are accessible on the results.
            Requires pulp_type.
    """
    # TODO: remove once RepositoryVersion.get_content() applies its own unnest() workaround
    # unconditionally instead of only when content_ids has >= 65535 items.
    #
    # The reason behind this to enable testing membership against a large set (repo content)
    # with few query params, which the use of the pg array solves. Besides that, the query
    # leverages the fact that the table already contains the content_ids field, so it can
    # select the content in the repository version directly on the db side (without requiring
    # the app to ever re-send the whole set).
    repo_content_ids = (
        RepositoryVersion.objects.filter(pk=repo_version.pk)
        .annotate(cids=Func(F("content_ids"), function="unnest"))
        .values_list("cids", flat=True)
    )

    if cast:
        if pulp_type is None:
            raise ValueError("cast=True requires pulp_type")
        content_qs = Content.get_model_for_pulp_type(pulp_type).objects
        return content_qs.filter(pk__in=repo_content_ids, pulp_domain=get_domain_pk())

    content_qs = content_qs if content_qs is not None else Content.objects
    content_qs = content_qs.filter(pk__in=repo_content_ids, pulp_domain=get_domain_pk())
    if pulp_type is not None:
        content_qs = content_qs.filter(pulp_type=pulp_type)
    return content_qs
