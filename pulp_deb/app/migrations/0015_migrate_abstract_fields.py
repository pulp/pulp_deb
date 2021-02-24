
from django.db import migrations


def migrate_distribution_fields(apps, schema_editor):
    # Set the core "_publication" field with the value of the detail "publication" field
    AptDistribution = apps.get_model('deb', 'aptdistribution')

    distributions = list(AptDistribution.objects.all())

    for distribution in distributions:
        distribution._publication = distribution.publication

    AptDistribution.objects.bulk_update(distributions, ['_publication'])


class Migration(migrations.Migration):

    dependencies = [
        ('deb', '0014_auto_publish'),
        ('core', '0060_add_new_distribution_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='aptdistribution',
            name='publication',
        ),
    ]
