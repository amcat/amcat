# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2018-05-03 20:13
from __future__ import unicode_literals

from django.db.models import F

import amcat.tools.model
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('amcat', '0011_display_props'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.CreateModel(
                name='ProjectArticleSet',
                fields=[
                    ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('articleset', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='amcat.ArticleSet')),
                    ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='amcat.Project')),
                ],
                options={
                    'db_table': 'projects_articlesets',
                    'unique_together': set([('project', 'articleset')]),
                },
            ),
            migrations.AlterField(
                model_name='project',
                name='articlesets',
                field=models.ManyToManyField(related_name='projects_set', through='amcat.ProjectArticleSet', to='amcat.ArticleSet'),
            )
        ]),
        migrations.AddField(
            model_name='projectarticleset',
            name='is_favourite',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
        migrations.RunSQL(  # insert articleset owners into projects_articlesets
            """
            INSERT INTO projects_articlesets (is_favourite, project_id, articleset_id) 
            SELECT FALSE, articlesets.project_id, articlesets.articleset_id 
            FROM articlesets 
            ON CONFLICT (project_id, articleset_id) DO NOTHING ;""",

            reverse_sql="""
            DELETE FROM projects_articlesets
            WHERE (projects_articlesets.project_id, projects_articlesets.articleset_id) IN (
                SELECT articlesets.project_id, articlesets.articleset_id 
                FROM articlesets
            )
            """
        ),
        migrations.RunSQL(  # insert or update favourites into projects_articlesets
            """
            INSERT INTO projects_articlesets (is_favourite, project_id, articleset_id) 
            SELECT TRUE, projects_favourite_articlesets.project_id, projects_favourite_articlesets.articleset_id 
            FROM projects_favourite_articlesets 
            ON CONFLICT (project_id, articleset_id) DO UPDATE 
            SET is_favourite = TRUE ;""",

            reverse_sql=
            "INSERT INTO projects_favourite_articlesets (project_id, articleset_id) "
            "SELECT projects_articlesets.project_id, projects_articlesets.articleset_id "
            "FROM projects_articlesets "
            "WHERE projects_articlesets.is_favourite = TRUE "
            "ON CONFLICT DO NOTHING "
        ),
        migrations.RemoveField(model_name='project', name='favourite_articlesets')
    ]
