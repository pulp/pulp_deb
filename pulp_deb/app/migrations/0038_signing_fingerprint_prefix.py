from django.db import migrations, models


def add_fingerprint_prefix(apps, schema_editor):
    """Add 'v4:' prefix to package_signing_fingerprint values that lack a prefix."""
    AptRepository = apps.get_model("deb", "AptRepository")
    AptRepository.objects.filter(
        package_signing_fingerprint__isnull=False,
    ).exclude(
        package_signing_fingerprint="",
    ).exclude(
        package_signing_fingerprint__contains=":",
    ).update(
        package_signing_fingerprint=models.functions.Concat(
            models.Value("v4:"), "package_signing_fingerprint"
        ),
    )

    AptRepositoryReleasePackageSigningFingerprintOverride = apps.get_model(
        "deb", "AptRepositoryReleasePackageSigningFingerprintOverride"
    )
    AptRepositoryReleasePackageSigningFingerprintOverride.objects.exclude(
        package_signing_fingerprint="",
    ).exclude(
        package_signing_fingerprint__contains=":",
    ).update(
        package_signing_fingerprint=models.functions.Concat(
            models.Value("v4:"), "package_signing_fingerprint"
        ),
    )

    DebPackageSigningResult = apps.get_model("deb", "DebPackageSigningResult")
    DebPackageSigningResult.objects.exclude(
        package_signing_fingerprint="",
    ).exclude(
        package_signing_fingerprint__contains=":",
    ).update(
        package_signing_fingerprint=models.functions.Concat(
            models.Value("v4:"), "package_signing_fingerprint"
        ),
    )


def remove_fingerprint_prefix(apps, schema_editor):
    """Remove type prefix (e.g. 'v4:', 'keyid:') from package_signing_fingerprint values."""
    AptRepository = apps.get_model("deb", "AptRepository")
    AptRepository.objects.filter(
        package_signing_fingerprint__contains=":",
    ).update(
        package_signing_fingerprint=models.Func(
            "package_signing_fingerprint",
            models.Value("^[^:]+:"),
            models.Value(""),
            function="REGEXP_REPLACE",
            output_field=models.TextField(),
        ),
    )

    AptRepositoryReleasePackageSigningFingerprintOverride = apps.get_model(
        "deb", "AptRepositoryReleasePackageSigningFingerprintOverride"
    )
    AptRepositoryReleasePackageSigningFingerprintOverride.objects.filter(
        package_signing_fingerprint__contains=":",
    ).update(
        package_signing_fingerprint=models.Func(
            "package_signing_fingerprint",
            models.Value("^[^:]+:"),
            models.Value(""),
            function="REGEXP_REPLACE",
            output_field=models.TextField(),
        ),
    )

    DebPackageSigningResult = apps.get_model("deb", "DebPackageSigningResult")
    DebPackageSigningResult.objects.filter(
        package_signing_fingerprint__contains=":",
    ).update(
        package_signing_fingerprint=models.Func(
            "package_signing_fingerprint",
            models.Value("^[^:]+:"),
            models.Value(""),
            function="REGEXP_REPLACE",
            output_field=models.TextField(),
        ),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("deb", "0037_DATA_fix_signing_fingerprint"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aptrepository",
            name="package_signing_fingerprint",
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name="aptrepositoryreleasepackagesigningfingerprintoverride",
            name="package_signing_fingerprint",
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name="debpackagesigningresult",
            name="package_signing_fingerprint",
            field=models.TextField(),
        ),
        migrations.RunPython(add_fingerprint_prefix, remove_fingerprint_prefix),
    ]
