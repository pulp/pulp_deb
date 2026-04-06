from django.db import migrations


def replace_empty_fingerprint_with_null(apps, schema_editor):
    """Replace empty and bare-prefix package_signing_fingerprint values with NULL."""
    AptRepository = apps.get_model("deb", "AptRepository")
    AptRepository.objects.filter(package_signing_fingerprint="").update(
        package_signing_fingerprint=None
    )


def replace_null_fingerprint_with_empty(apps, schema_editor):
    """Replace NULL package_signing_fingerprint values with empty string."""
    AptRepository = apps.get_model("deb", "AptRepository")
    AptRepository.objects.filter(package_signing_fingerprint=None).update(
        package_signing_fingerprint=""
    )


class Migration(migrations.Migration):
    dependencies = [
        ("deb", "0036_add_deb_package_signing_result"),
    ]

    operations = [
        migrations.RunPython(
            replace_empty_fingerprint_with_null,
            replace_null_fingerprint_with_empty,
        ),
    ]
