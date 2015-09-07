# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0005_code_label'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='codebookcode',
            name='function',
        ),
        migrations.DeleteModel(
            name='Function',
        ),
    ]
