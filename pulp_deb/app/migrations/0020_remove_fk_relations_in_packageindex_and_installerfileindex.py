# Generated by Django 3.2.18 on 2023-03-07 15:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('deb', '0019_immutable_metadata_constraints'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='installerfileindex',
            name='release',
        ),
        migrations.RemoveField(
            model_name='packageindex',
            name='release',
        ),
    ]