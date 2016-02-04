# -*- coding: utf-8 -*-

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0006_auto_20150907_1238'),
    ]

    operations = [
        migrations.AlterField(
            model_name='codingjob',
            name='articleschema',
            field=models.ForeignKey(related_name='codingjobs_article', blank=True, to='amcat.CodingSchema', null=True),
        ),
        migrations.AlterField(
            model_name='codingjob',
            name='unitschema',
            field=models.ForeignKey(related_name='codingjobs_unit', blank=True, to='amcat.CodingSchema', null=True),
        ),
    ]
