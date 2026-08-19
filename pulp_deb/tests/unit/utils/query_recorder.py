import inspect
import json
from collections import Counter
from dataclasses import dataclass

import sqlparse
import sqlparse.exceptions
from django.db import connection


def _pretty_sql(sql: str) -> str:
    """Reformat SQL via sqlparse, falling back to the raw string if it's too large to parse.

    sqlparse caps parsing at 10000 tokens (a DoS guard) and raises SQLParseError past that -
    queries with a huge literal IN (...) list can easily exceed it.
    """
    try:
        return sqlparse.format(sql, reindent=True, keyword_case="upper")
    except sqlparse.exceptions.SQLParseError:
        return sql


@dataclass
class RecordedQuery:
    """A single query as actually sent to the database, with its raw bound params."""

    sql: str
    num_params: int
    many: bool
    django_cursor_t: str
    psycopg_cursor_t: str | None
    statement_type: str
    call_site: list[str]
    call_line: str

    @property
    def summary(self) -> dict:
        """A short representation of this query, omitting the (often long) raw SQL text."""
        return {
            "statement_type": self.statement_type,
            "num_params": self.num_params,
            "many": self.many,
            "django_cursor_t": self.django_cursor_t,
            "psycopg_cursor_t": self.psycopg_cursor_t,
            "call_site": self.call_site,
            "call_line": self.call_line,
        }


class QueryRecorder:
    """Captures every query's raw bound-parameter count as it's actually executed.

    Usable as a context manager: `with QueryRecorder() as recorder: ...` wraps the block in
    `connection.execute_wrapper(self)`.
    """

    def __init__(self):
        self.queries: list[RecordedQuery] = []
        self._wrapper = None

    def get_queries(self, filter_fn=None) -> list[RecordedQuery]:
        """Recorded queries, optionally narrowed by filter_fn(query) -> bool."""
        return [q for q in self.queries if filter_fn is None or filter_fn(q)]

    @staticmethod
    def _sql_statement_type(sql: str) -> str:
        """Best-effort statement keyword (SELECT/INSERT/UPDATE/CREATE/...).

        Not a real SQL parser - just the leading token, uppercased. Good enough to classify SQL
        our own code generates; doesn't handle leading comments or distinguish e.g. CREATE TABLE
        from CREATE INDEX.
        """
        sql = sql.strip()
        return sql.split(None, 1)[0].upper() if sql else ""

    @staticmethod
    def _qualname(a_class: type) -> str:
        return f"{a_class.__module__}.{a_class.__qualname__}"

    @staticmethod
    def _psycopg_base(raw_cursor_class: type) -> type | None:
        """The psycopg-defined base in the MRO, e.g. django's ServerBindingCursor -> psycopg.Cursor.

        Django's own cursor classes (django.db.backends.postgresql.base.Cursor,
        ServerBindingCursor, ...) subclass psycopg's cursor directly rather than wrapping it, so
        the actual psycopg class only shows up in the MRO, not as a separate `.cursor` attribute.
        """
        return next(
            (c for c in raw_cursor_class.__mro__ if c.__module__.split(".")[0] == "psycopg"),
            None,
        )

    @staticmethod
    def _call_site() -> tuple[list[str], str]:
        """Collect every stack frame whose file path contains "pulp", innermost first.

        A single frame often isn't enough context (e.g. a generic helper shared by many call
        sites), so this walks the whole call chain through pulp code instead of stopping at the
        first match. Excludes this file itself.
        Returns (sites, line): sites is a list of "file:lineno in function" strings; line is the
        innermost matching frame's source text.
        """
        sites = []
        line = ""
        for frame_info in inspect.stack(context=1):
            if frame_info.filename == __file__:
                continue
            if "pulp" not in frame_info.filename:
                continue
            sites.append(f"{frame_info.filename}:{frame_info.lineno} in {frame_info.function}")
            if not line:
                line = frame_info.code_context[0].strip() if frame_info.code_context else ""
        sites.reverse()
        return sites, line

    def __call__(self, execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if many:
            # executemany(): params is a list of per-row parameter sequences, not one flat
            # sequence - count every row's params, not just the number of rows.
            num_params = sum(len(row) for row in params or ())
        else:
            num_params = len(params or ())

        # context["cursor"] is Django's CursorWrapper; .cursor is Django's own cursor class
        # (e.g. django.db.backends.postgresql.base.ServerBindingCursor), which is what actually
        # enforces the limit - and which itself subclasses the underlying psycopg cursor class.
        raw_cursor = getattr(context["cursor"], "cursor", context["cursor"])
        raw_cursor_class = type(raw_cursor)
        psycopg_base = self._psycopg_base(raw_cursor_class)
        call_site, call_line = self._call_site()

        self.queries.append(
            RecordedQuery(
                sql=sql,
                num_params=num_params,
                many=many,
                django_cursor_t=self._qualname(raw_cursor_class),
                psycopg_cursor_t=self._qualname(psycopg_base) if psycopg_base else None,
                statement_type=self._sql_statement_type(sql),
                call_site=call_site,
                call_line=call_line,
            )
        )
        return result

    def __enter__(self):
        self._wrapper = connection.execute_wrapper(self)
        self._wrapper.__enter__()
        return self

    def __exit__(self, *exc_info):
        return self._wrapper.__exit__(*exc_info)

    def max_params(self):
        return max((q.num_params for q in self.queries), default=0)

    def summary_text(self, include_sql=False) -> str:
        """Build every recorded query's summary as indented JSON, as a single string.

        Each entry carries a query_id matching the "--- query N ---" labels below it, so the two
        can be correlated. By default omits the (often long) raw SQL text. With include_sql=True,
        each query's SQL is also included - reformatted with sqlparse, as its own readable block
        after the JSON summary, since JSON strings can't hold the real newlines a pretty-printed
        query needs.
        """
        summaries = [{"query_id": i, **q.summary} for i, q in enumerate(self.queries)]
        lines = [json.dumps(summaries, indent=4)]
        if include_sql:
            for i, query in enumerate(self.queries):
                lines.append(f"\n--- query {i} ---")
                for site in query.call_site:
                    lines.append(f"--- {site}")
                lines.append(f"--- {query.call_line}")
                lines.append(_pretty_sql(query.sql))
        return "\n".join(lines)

    def print_summary(self, include_sql=False):
        """Print summary_text() to stdout."""
        print(self.summary_text(include_sql=include_sql))


def detect_n1(small_queries, large_queries) -> list[dict]:
    """Find call sites whose query count differs between a small and a large run.

    Groups by (call_site[-1], call_line) - the innermost call_site entry (the frame that
    actually produced call_line) paired with the source text itself - not call_line alone,
    which can collide across unrelated call sites and merge distinct query origins together.
    A per-item N+1 loop shows up here as a call site firing small_count times in the small run
    and large_count times in the large run.

    Returns one {**query.summary, "small_count", "large_count", "growth_rate"} dict (using one
    representative large-run query) per call site whose counts differ.
    """

    def key_of(query):
        return (query.call_site[-1], query.call_line)

    small_counts = Counter(key_of(q) for q in small_queries)
    large_counts = Counter(key_of(q) for q in large_queries)
    representative = {key_of(q): q for q in large_queries}

    offenders = []
    for key, large_count in large_counts.items():
        small_count = small_counts.get(key, 0)
        if large_count == small_count:
            continue
        growth_rate = round(large_count / small_count, 2) if small_count else None
        offenders.append(
            {
                **representative[key].summary,
                "small_count": small_count,
                "large_count": large_count,
                "growth_rate": growth_rate,
            }
        )
    return offenders
