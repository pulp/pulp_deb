# Generated by Django 3.2.13 on 2022-06-01 12:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deb', '0017_allow_longer_string_lists'),
    ]

    operations = [
        migrations.AlterField(
            model_name='installerfileindex',
            name='architecture',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='installerfileindex',
            name='component',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='packageindex',
            name='architecture',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='packageindex',
            name='component',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='release',
            name='codename',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='release',
            name='distribution',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='release',
            name='suite',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='releasearchitecture',
            name='architecture',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='releasecomponent',
            name='component',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='releasefile',
            name='codename',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='releasefile',
            name='distribution',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='releasefile',
            name='suite',
            field=models.TextField(),
        ),
    ]
