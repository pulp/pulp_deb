# Generated by Django 4.2.1 on 2023-05-17 10:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0106_alter_artifactdistribution_distribution_ptr_and_more'),
        ('deb', '0021_remove_release_from_structure_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aptdistribution',
            name='distribution_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.distribution'),
        ),
        migrations.AlterField(
            model_name='aptpublication',
            name='publication_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.publication'),
        ),
        migrations.AlterField(
            model_name='aptpublication',
            name='signing_service',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='deb.aptreleasesigningservice'),
        ),
        migrations.AlterField(
            model_name='aptremote',
            name='remote_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.remote'),
        ),
        migrations.AlterField(
            model_name='aptrepository',
            name='repository_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.repository'),
        ),
        migrations.AlterField(
            model_name='genericcontent',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='installerfileindex',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='installerpackage',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='package',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='packageindex',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='packagereleasecomponent',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='packagereleasecomponent',
            name='package',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='deb.package'),
        ),
        migrations.AlterField(
            model_name='packagereleasecomponent',
            name='release_component',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='deb.releasecomponent'),
        ),
        migrations.AlterField(
            model_name='release',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='releasearchitecture',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='releasecomponent',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='releasefile',
            name='content_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.content'),
        ),
        migrations.AlterField(
            model_name='verbatimpublication',
            name='publication_ptr',
            field=models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='core.publication'),
        ),
    ]
