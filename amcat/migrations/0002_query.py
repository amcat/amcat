# -*- coding: utf-8 -*-

from django.db import models, migrations
from django.conf import settings
import amcat.forms.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('amcat', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Query',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='query_id')),
                ('name', models.TextField()),
                ('parameters', amcat.forms.fields.JSONField(default={})),
                ('private', models.BooleanField(default=True)),
                ('last_saved', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(to='amcat.Project')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'queries',
            },
            bases=(models.Model,),
        ),
    ]
