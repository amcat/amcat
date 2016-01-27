# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0009_recentprojects'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='query',
            name='private',
        ),
    ]
