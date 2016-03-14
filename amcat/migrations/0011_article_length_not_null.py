# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0010_remove_syntax_rules'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='length',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
