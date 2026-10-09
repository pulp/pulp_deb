import unittest
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase
from django.utils import timezone

from pulp_deb.app.models import AptDistribution, AptPublication, AptRepository


class TestDistributedPublicationMigration(TestCase):
    @unittest.skip("FIXME: remove when DistributedPublication table is dropped")
    def test_copies_all_rows(self):
        migration = import_module("pulp_deb.app.migrations.0044_remove_distributedpublication")
        # Create Repository, Publication and Distribution
        repository = AptRepository.objects.create(name=f"migration-{uuid4()}")
        repository_version = repository.latest_version()
        publication = AptPublication.objects.create(repository_version=repository_version)
        distribution = AptDistribution.objects.create(
            name=f"migration-{uuid4()}",
            base_path=f"migration-{uuid4()}",
            publication=publication,
        )

        # Get models from before the migration
        migration_apps = (
            MigrationLoader(connection)
            .project_state(
                [
                    ("core", "0149_distributedpublication"),
                    ("deb", "0043_alter_release_unique_together_and_more"),
                ]
            )
            .apps
        )
        DebDistributedPublication = migration_apps.get_model("deb", "DistributedPublication")
        CoreDistributedPublication = migration_apps.get_model("core", "DistributedPublication")

        # Create a set of deb's DistributedPublicaitions
        source_rows = [
            DebDistributedPublication(
                distribution_id=distribution.pk,
                publication_id=publication.pk,
                expires_at=timezone.now(),
            )
            for _ in range(migration.BATCH_SIZE + 2)
        ]
        DebDistributedPublication.objects.bulk_create(source_rows)
        source_ids = [row.pulp_id for row in source_rows]

        # Migrate data and assert it's copied correctly
        migration.copy_to_core(
            migration_apps,
            SimpleNamespace(connection=connection),
        )
        source_data = set(
            DebDistributedPublication.objects.filter(pulp_id__in=source_ids).values_list(
                "pulp_id",
                "pulp_created",
                "pulp_last_updated",
                "expires_at",
                "distribution_id",
                "publication_id",
            )
        )
        copied_data = set(
            CoreDistributedPublication.objects.filter(pulp_id__in=source_ids).values_list(
                "pulp_id",
                "pulp_created",
                "pulp_last_updated",
                "expires_at",
                "distribution_id",
                "publication_id",
            )
        )
        self.assertEqual(copied_data, source_data)
