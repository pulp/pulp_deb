from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('deb', '0001_initial_squashed_0031_add_domains'),
    ]

    operations = [
        migrations.AddField(
            model_name='aptrepository',
            name='autopublish',
            field=models.BooleanField(default=False),
        ),
    ]

