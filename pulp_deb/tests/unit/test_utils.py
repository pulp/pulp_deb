"""Unit tests for test-support utilities under tests/unit/utils/."""

import uuid

import pytest
from django.db import connection

from pulp_deb.app.models import Package
from pulp_deb.tests.unit.utils.query_recorder import QueryRecorder


class TestQueryRecorder:
    """Sanity checks for QueryRecorder itself, using the cursor directly."""

    @pytest.mark.django_db
    def test_records_a_single_execute(self):
        with QueryRecorder() as recorder:
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s, %s, %s", [1, 2, 3])

        assert len(recorder.queries) == 1
        query = recorder.queries[0]
        assert query.num_params == 3
        assert query.many is False
        assert query.statement_type == "SELECT"
        assert "SELECT" in query.sql

    @pytest.mark.django_db
    def test_records_zero_params(self):
        with QueryRecorder() as recorder:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

        assert recorder.queries[0].num_params == 0

    @pytest.mark.django_db
    def test_records_multiple_queries_in_order(self):
        with QueryRecorder() as recorder:
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s", [1])
                cursor.execute("SELECT %s, %s", [1, 2])

        assert [q.num_params for q in recorder.queries] == [1, 2]

    @pytest.mark.django_db
    def test_records_executemany_by_summing_every_row(self):
        with QueryRecorder() as recorder:
            with connection.cursor() as cursor:
                cursor.execute("CREATE TEMPORARY TABLE query_recorder_test (a int, b int)")
                cursor.executemany(
                    "INSERT INTO query_recorder_test (a, b) VALUES (%s, %s)",
                    [(1, 2), (3, 4), (5, 6)],
                )

        insert_query = next(q for q in recorder.queries if q.many)
        # 3 rows * 2 params each - not len(params) == 3, which would just be the row count.
        assert insert_query.num_params == 6
        assert insert_query.many is True
        assert insert_query.statement_type == "INSERT"

        create_query = next(q for q in recorder.queries if q.statement_type == "CREATE")
        assert create_query.many is False

    @pytest.mark.parametrize(
        "sql,expected",
        [
            ("SELECT 1", "SELECT"),
            ("  \n  UPDATE t SET a = 1", "UPDATE"),
            ("delete from t where a = 1", "DELETE"),
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_sql_statement_type_heuristic(self, sql, expected):
        assert QueryRecorder._sql_statement_type(sql) == expected

    @pytest.mark.django_db
    def test_max_params_returns_the_largest_single_query(self):
        with QueryRecorder() as recorder:
            with connection.cursor() as cursor:
                cursor.execute("SELECT %s", [1])
                cursor.execute("SELECT %s, %s, %s", [1, 2, 3])

        assert recorder.max_params() == 3

    def test_max_params_defaults_to_zero_when_empty(self):
        assert QueryRecorder().max_params() == 0

    @pytest.mark.django_db
    def test_iterator_calls(self):
        with QueryRecorder() as recorder:
            list(Package.objects.all().only("pk"))
            list(Package.objects.all().only("pk").iterator())
            list(Package.objects.all().only("pk").iterator(chunk_size=100))
        recorder.print_summary(include_sql=True)

    @pytest.mark.django_db
    def test_iterator_calls_with_pk__in(self):
        ids = [uuid.uuid4() for _ in range(3)]
        with QueryRecorder() as recorder:
            list(Package.objects.filter(pk__in=ids).only("pk"))
            list(Package.objects.filter(pk__in=ids).only("pk").iterator())
            list(Package.objects.filter(pk__in=ids).only("pk").iterator(chunk_size=100))
        recorder.print_summary(include_sql=True)
