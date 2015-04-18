# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0003_articleset_featured'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='query',
            options={'ordering': ('-last_saved',)},
        ),
        migrations.AlterField(
            model_name='query',
            name='last_saved',
            field=models.DateTimeField(auto_now=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='query',
            name='private',
            field=models.BooleanField(default=True, db_index=True),
            preserve_default=True,
        ),
    ]
