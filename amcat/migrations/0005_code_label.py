# -*- coding: utf-8 -*-

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0004_auto_20150418_1656'),
    ]

    operations = [
        migrations.AddField(
            model_name='code',
            name='label',
            field=models.TextField(default='?'),
            preserve_default=False,
        ),
    ]
