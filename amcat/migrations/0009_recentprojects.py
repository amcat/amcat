# -*- coding: utf-8 -*-

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0008_auto_20151028_1300'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecentProject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_visited', models.DateTimeField()),
                ('project', models.ForeignKey(related_name='last_visited_at', to='amcat.Project')),
                ('user', models.ForeignKey(to='amcat.UserProfile')),
            ],
            options={
                'ordering': ['date_visited'],
                'db_table': 'user_recent_projects',
            },
        ),
        migrations.AddField(
            model_name='userprofile',
            name='recent_projects',
            field=models.ManyToManyField(related_name='recent_projects', through='amcat.RecentProject', to='amcat.Project'),
        ),
        migrations.AlterUniqueTogether(
            name='recentproject',
            unique_together=set([('user', 'project')]),
        ),
    ]
