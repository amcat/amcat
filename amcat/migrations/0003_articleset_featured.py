# -*- coding: utf-8 -*-

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0002_query'),
    ]

    operations = [
        migrations.AddField(
            model_name='articleset',
            name='featured',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
