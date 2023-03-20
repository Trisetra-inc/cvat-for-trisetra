# Generated by Django 3.2.18 on 2023-03-20 16:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0065_auto_20230221_0931'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='clientfile',
            options={'default_permissions': (), 'ordering': ('id',)},
        ),
        migrations.AlterModelOptions(
            name='relatedfile',
            options={'default_permissions': (), 'ordering': ('id',)},
        ),
        migrations.AlterModelOptions(
            name='remotefile',
            options={'default_permissions': (), 'ordering': ('id',)},
        ),
        migrations.AlterModelOptions(
            name='serverfile',
            options={'default_permissions': (), 'ordering': ('id',)},
        ),
        migrations.AlterUniqueTogether(
            name='remotefile',
            unique_together={('data', 'file')},
        ),
        migrations.AlterUniqueTogether(
            name='serverfile',
            unique_together={('data', 'file')},
        ),
    ]
