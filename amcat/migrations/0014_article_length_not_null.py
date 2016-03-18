# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import amcat.forms.fields


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0013_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='length',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='query',
            name='parameters',
            field=amcat.forms.fields.JSONField(default={}),
        ),
    ]
