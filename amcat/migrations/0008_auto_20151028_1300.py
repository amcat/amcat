# -*- coding: utf-8 -*-

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0007_optionalschemas'),
    ]

    operations = [
        migrations.AlterField(
            model_name='codingschema',
            name='highlight_language',
            field=models.ForeignKey(blank=True, to='amcat.Language', null=True),
        ),
    ]
