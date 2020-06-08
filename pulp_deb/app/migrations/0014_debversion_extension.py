# This Migration was _not_ automatically generated.
# When regenerating the migrations ever, this one _must_ be preserved.

from django.db import migrations
from django.contrib.postgres.operations import CreateExtension


class Migration(migrations.Migration):

    dependencies = [
        ('deb', '0013_aptremote_ignore_missing_package_indices'),
    ]

    operations = [
        CreateExtension(name='debversion'),
    ]
