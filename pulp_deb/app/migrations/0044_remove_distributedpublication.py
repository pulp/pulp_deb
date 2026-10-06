import logging
from itertools import islice

from django.db import migrations, transaction

logger = logging.getLogger(__name__)
BATCH_SIZE = 5000


def copy_to_core(apps, schema_editor):
    """Best-effort data backfill."""
    try:
        with transaction.atomic(using=schema_editor.connection.alias):
            DebDistributedPublication = apps.get_model("deb", "DistributedPublication")
            CoreDistributedPublication = apps.get_model("core", "DistributedPublication")
            db_alias = schema_editor.connection.alias
            rows = (
                DebDistributedPublication.objects.using(db_alias)
                .values(
                    "pulp_id",
                    "pulp_created",
                    "pulp_last_updated",
                    "expires_at",
                    "distribution_id",
                    "publication_id",
                )
                .iterator(chunk_size=BATCH_SIZE)
            )
            created_field = CoreDistributedPublication._meta.get_field("pulp_created")
            updated_field = CoreDistributedPublication._meta.get_field("pulp_last_updated")
            auto_now_add = created_field.auto_now_add
            auto_now = updated_field.auto_now
            try:
                # bulk_create normally refreshes these fields; preserve their legacy values.
                created_field.auto_now_add = False
                updated_field.auto_now = False
                while True:
                    batch = list(islice(rows, BATCH_SIZE))
                    if not batch:
                        break
                    CoreDistributedPublication.objects.using(db_alias).bulk_create(
                        [CoreDistributedPublication(**row) for row in batch],
                        batch_size=BATCH_SIZE,
                        ignore_conflicts=True,
                    )
            finally:
                created_field.auto_now_add = auto_now_add
                updated_field.auto_now = auto_now
    except Exception:
        logger.warning(
            "Could not copy distributed publication data to pulpcore; "
            "continuing because the legacy table is retained.",
            exc_info=True,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0149_distributedpublication"),
        ("deb", "0043_alter_release_unique_together_and_more"),
    ]

    operations = [
        migrations.RunPython(copy_to_core),
    ]
