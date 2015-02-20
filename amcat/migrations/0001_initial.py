# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import amcat.tools.djangotoolkit
from django.conf import settings
import amcat.tools.model
import amcat.forms.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Affiliation',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column=b'affiliation_id')),
                ('name', models.CharField(max_length=200)),
            ],
            options={
                'ordering': ('name',),
                'db_table': 'affiliations',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AmCAT',
            fields=[
                ('id', models.BooleanField(default=False, serialize=False, primary_key=True, db_column='singleton_pk')),
                ('global_announcement', models.TextField(null=True, blank=True)),
                ('db_version', models.IntegerField()),
            ],
            options={
                'db_table': 'amcat_system',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='article_id')),
                ('date', models.DateTimeField(db_index=True)),
                ('section', models.CharField(max_length=500, null=True, blank=True)),
                ('pagenr', models.IntegerField(null=True, blank=True)),
                ('headline', models.TextField()),
                ('byline', models.TextField(null=True, blank=True)),
                ('length', models.IntegerField(blank=True)),
                ('metastring', models.TextField(null=True, blank=True)),
                ('url', models.TextField(db_index=True, max_length=750, null=True, blank=True)),
                ('externalid', models.IntegerField(null=True, blank=True)),
                ('author', models.TextField(max_length=100, null=True, blank=True)),
                ('addressee', models.TextField(max_length=100, null=True, blank=True)),
                ('uuid', amcat.tools.model.PostgresNativeUUIDField(name=b'uuid', editable=False, blank=True, unique=True, db_index=True)),
                ('text', models.TextField()),
                ('insertscript', models.CharField(max_length=500, null=True, blank=True)),
                ('insertdate', models.DateTimeField(auto_now_add=True, null=True)),
            ],
            options={
                'db_table': 'articles',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ArticleSet',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='articleset_id')),
                ('name', models.CharField(max_length=200)),
                ('provenance', models.TextField(null=True)),
                ('articles', models.ManyToManyField(related_name='articlesets_set', to='amcat.Article')),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'articlesets',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Code',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='code_id')),
                ('uuid', amcat.tools.model.PostgresNativeUUIDField(name=b'uuid', editable=False, blank=True, unique=True, db_index=True)),
            ],
            options={
                'db_table': 'codes',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Codebook',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='codebook_id')),
                ('name', models.TextField()),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'codebooks',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodebookCode',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='codebook_object_id')),
                ('hide', models.BooleanField(default=False)),
                ('validfrom', models.DateTimeField(null=True)),
                ('validto', models.DateTimeField(null=True)),
                ('ordernr', models.IntegerField(default=0, help_text='Annotator should order according codes according to this number.', db_index=True)),
                ('code', models.ForeignKey(related_name='codebook_codes', to='amcat.Code')),
                ('codebook', models.ForeignKey(to='amcat.Codebook')),
            ],
            options={
                'ordering': ('ordernr',),
                'db_table': 'codebooks_codes',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodedArticle',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('comments', models.TextField(null=True, blank=True)),
                ('article', models.ForeignKey(related_name='coded_articles', to='amcat.Article')),
            ],
            options={
                'db_table': 'coded_articles',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodedArticleStatus',
            fields=[
                ('id', models.IntegerField(serialize=False, primary_key=True, db_column=b'status_id')),
                ('label', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'coded_article_status',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Coding',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column=b'coding_id')),
                ('start', models.SmallIntegerField(null=True)),
                ('end', models.SmallIntegerField(null=True)),
                ('coded_article', models.ForeignKey(related_name='codings', to='amcat.CodedArticle')),
            ],
            options={
                'db_table': 'codings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodingJob',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column=b'codingjob_id')),
                ('name', models.CharField(max_length=100)),
                ('insertdate', models.DateTimeField(auto_now_add=True)),
                ('archived', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('project', '-id'),
                'db_table': 'codingjobs',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodingRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(max_length=75)),
                ('condition', models.TextField()),
            ],
            options={
                'db_table': 'codingrules',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodingRuleAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('label', models.CharField(max_length=50)),
                ('description', models.TextField()),
            ],
            options={
                'db_table': 'codingruleactions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodingSchema',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='codingschema_id')),
                ('name', models.CharField(max_length=75)),
                ('description', models.TextField(null=True)),
                ('isarticleschema', models.BooleanField(default=False)),
                ('subsentences', models.BooleanField(default=False, help_text='Allow subsentences to be coded.')),
            ],
            options={
                'ordering': ['name'],
                'db_table': 'codingschemas',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodingSchemaField',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column=b'codingschemafield_id')),
                ('fieldnr', models.IntegerField(default=0)),
                ('label', models.TextField()),
                ('required', models.BooleanField(default=True)),
                ('split_codebook', models.BooleanField(default=False, help_text=b'Do not display a list of all codes in annotator, but let the user first choose a root and then one of its descendants.')),
                ('default', models.CharField(max_length=50, null=True, db_column=b'deflt', blank=True)),
                ('codebook', models.ForeignKey(to='amcat.Codebook', null=True)),
                ('codingschema', models.ForeignKey(related_name='fields', to='amcat.CodingSchema')),
            ],
            options={
                'db_table': 'codingschemas_fields',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodingSchemaFieldType',
            fields=[
                ('id', models.IntegerField(serialize=False, primary_key=True, db_column=b'fieldtype_id')),
                ('name', models.CharField(unique=True, max_length=50)),
                ('serialiserclassname', models.CharField(max_length=50, db_column=b'serialiserclass')),
            ],
            options={
                'db_table': 'codingschemas_fieldtypes',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodingValue',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column=b'codingvalue_id')),
                ('strval', models.CharField(max_length=1000, null=True, blank=True)),
                ('intval', models.IntegerField(null=True)),
                ('coding', models.ForeignKey(related_name='values', to='amcat.Coding')),
                ('field', models.ForeignKey(to='amcat.CodingSchemaField')),
            ],
            options={
                'db_table': 'codings_values',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Function',
            fields=[
                ('id', models.IntegerField(serialize=False, primary_key=True, db_column='function_id')),
                ('label', models.CharField(unique=True, max_length=100)),
                ('description', models.TextField(null=True)),
            ],
            options={
                'db_table': 'codebooks_functions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='label_id')),
                ('label', models.TextField()),
                ('code', models.ForeignKey(related_name='labels', to='amcat.Code')),
            ],
            options={
                'ordering': ('language__id',),
                'db_table': 'codes_labels',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='language_id')),
                ('label', models.CharField(unique=True, max_length=50)),
            ],
            options={
                'db_table': 'languages',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Medium',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='medium_id')),
                ('name', models.CharField(unique=True, max_length=200)),
                ('abbrev', models.CharField(max_length=10, null=True, blank=True)),
                ('circulation', models.IntegerField(null=True, blank=True)),
                ('language', models.ForeignKey(to='amcat.Language', null=True)),
            ],
            options={
                'db_table': 'media',
                'verbose_name_plural': 'media',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MediumAlias',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('medium', models.ForeignKey(to='amcat.Medium')),
            ],
            options={
                'db_table': 'media_alias',
                'verbose_name_plural': 'media_aliases',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MediumSourcetype',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='medium_source_id')),
                ('label', models.CharField(max_length=20)),
            ],
            options={
                'db_table': 'media_sourcetypes',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Plugin',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='plugin_id')),
                ('label', models.CharField(unique=True, max_length=100)),
                ('class_name', models.CharField(unique=True, max_length=100)),
            ],
            options={
                'db_table': 'plugins',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PluginType',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='plugintype_id')),
                ('label', models.CharField(unique=True, max_length=100)),
                ('class_name', models.CharField(unique=True, max_length=100)),
            ],
            options={
                'db_table': 'plugintypes',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Privilege',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='privilege_id')),
                ('label', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'privileges',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(serialize=False, editable=False, primary_key=True, db_column='project_id')),
                ('name', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=200, null=True)),
                ('insert_date', models.DateTimeField(auto_now_add=True, db_column='insertdate')),
                ('active', models.BooleanField(default=True)),
                ('articlesets', models.ManyToManyField(related_name='projects_set', to='amcat.ArticleSet')),
                ('codebooks', models.ManyToManyField(related_name='projects_set', to='amcat.Codebook')),
                ('codingschemas', models.ManyToManyField(related_name='projects_set', to='amcat.CodingSchema')),
                ('favourite_articlesets', models.ManyToManyField(related_name='favourite_of_projects', to='amcat.ArticleSet')),
            ],
            options={
                'ordering': ('name',),
                'db_table': 'projects',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project', models.ForeignKey(to='amcat.Project')),
            ],
            options={
                'db_table': 'projects_users_roles',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='role_id')),
                ('label', models.CharField(max_length=50)),
                ('projectlevel', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'roles',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='rule_id')),
                ('label', models.CharField(max_length=255)),
                ('order', models.IntegerField()),
                ('display', models.BooleanField(default=False)),
                ('where', models.TextField()),
                ('insert', models.TextField(null=True, blank=True)),
                ('remove', models.TextField(null=True, blank=True)),
                ('remarks', models.TextField(null=True, blank=True)),
            ],
            options={
                'ordering': ['ruleset', 'order'],
                'db_table': 'rules',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RuleSet',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='rule_id')),
                ('label', models.CharField(max_length=255)),
                ('preprocessing', models.CharField(max_length=1000)),
                ('lexicon_codebook', models.ForeignKey(related_name='+', to='amcat.Codebook')),
                ('lexicon_language', models.ForeignKey(related_name='+', to='amcat.Language')),
            ],
            options={
                'db_table': 'rulesets',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Scraper',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column='scraper_id')),
                ('module', models.CharField(max_length=100)),
                ('class_name', models.CharField(max_length=100)),
                ('label', models.CharField(max_length=100)),
                ('username', models.CharField(max_length=50, null=True)),
                ('password', models.CharField(max_length=25, null=True)),
                ('run_daily', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=True)),
                ('statistics', amcat.tools.djangotoolkit.JsonField(null=True)),
                ('articleset', models.ForeignKey(to='amcat.ArticleSet', null=True)),
            ],
            options={
                'db_table': 'scrapers',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Sentence',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, db_column=b'sentence_id')),
                ('sentence', models.TextField()),
                ('parnr', models.IntegerField()),
                ('sentnr', models.IntegerField()),
                ('article', models.ForeignKey(related_name='sentences', to='amcat.Article')),
            ],
            options={
                'ordering': ['article', 'parnr', 'sentnr'],
                'db_table': 'sentences',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', amcat.tools.model.PostgresNativeUUIDField(name=b'uuid', editable=False, blank=True, unique=True, db_index=True)),
                ('handler_class_name', models.TextField()),
                ('class_name', models.TextField()),
                ('arguments', amcat.forms.fields.JSONField(default=b'{}')),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
                ('persistent', models.BooleanField(default=False)),
                ('project', models.ForeignKey(to='amcat.Project', null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'tasks',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('theme', models.CharField(default=b'AmCAT', max_length=255, choices=[(b'AmCAT', b'AmCAT'), (b'Pink', b'Pink'), (b'Pink Dreamliner', b'Pink Dreamliner'), (b'Darkly', b'Darkly'), (b'Amelia', b'Amelia')])),
                ('fluid', models.BooleanField(default=False, help_text=b'Use fluid layout')),
                ('affiliation', models.ForeignKey(default=1, to='amcat.Affiliation')),
                ('favourite_projects', models.ManyToManyField(related_name='favourite_users', to='amcat.Project')),
                ('language', models.ForeignKey(default=1, to='amcat.Language')),
                ('role', models.ForeignKey(default=0, to='amcat.Role')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'auth_user_profile',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='sentence',
            unique_together=set([('article', 'parnr', 'sentnr')]),
        ),
        migrations.AddField(
            model_name='rule',
            name='ruleset',
            field=models.ForeignKey(related_name='rules', to='amcat.RuleSet'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='role',
            unique_together=set([('label', 'projectlevel')]),
        ),
        migrations.AddField(
            model_name='projectrole',
            name='role',
            field=models.ForeignKey(to='amcat.Role'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='projectrole',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='projectrole',
            unique_together=set([('project', 'user')]),
        ),
        migrations.AddField(
            model_name='project',
            name='guest_role',
            field=models.ForeignKey(default=11, to='amcat.Role', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='insert_user',
            field=models.ForeignKey(related_name='inserted_project', db_column='insertuser_id', editable=False, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='owner',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, db_column='owner_id'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='privilege',
            name='role',
            field=models.ForeignKey(to='amcat.Role'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='plugin',
            name='plugin_type',
            field=models.ForeignKey(related_name='plugins', to='amcat.PluginType', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='label',
            name='language',
            field=models.ForeignKey(related_name='labels', to='amcat.Language'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='label',
            unique_together=set([('code', 'language')]),
        ),
        migrations.AlterUniqueTogether(
            name='codingvalue',
            unique_together=set([('coding', 'field')]),
        ),
        migrations.AddField(
            model_name='codingschemafield',
            name='fieldtype',
            field=models.ForeignKey(to='amcat.CodingSchemaFieldType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingschema',
            name='highlight_language',
            field=models.ForeignKey(to='amcat.Language', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingschema',
            name='highlighters',
            field=models.ManyToManyField(to='amcat.Codebook'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingschema',
            name='project',
            field=models.ForeignKey(to='amcat.Project'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingrule',
            name='action',
            field=models.ForeignKey(to='amcat.CodingRuleAction', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingrule',
            name='codingschema',
            field=models.ForeignKey(related_name='rules', to='amcat.CodingSchema'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingrule',
            name='field',
            field=models.ForeignKey(to='amcat.CodingSchemaField', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingjob',
            name='articleschema',
            field=models.ForeignKey(related_name='codingjobs_article', to='amcat.CodingSchema'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingjob',
            name='articleset',
            field=models.ForeignKey(related_name='codingjob_set', to='amcat.ArticleSet'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingjob',
            name='coder',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingjob',
            name='insertuser',
            field=models.ForeignKey(related_name='+', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingjob',
            name='project',
            field=models.ForeignKey(to='amcat.Project'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codingjob',
            name='unitschema',
            field=models.ForeignKey(related_name='codingjobs_unit', to='amcat.CodingSchema'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='coding',
            name='sentence',
            field=models.ForeignKey(to='amcat.Sentence', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codedarticle',
            name='codingjob',
            field=models.ForeignKey(related_name='coded_articles', to='amcat.CodingJob'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codedarticle',
            name='status',
            field=models.ForeignKey(default=0, to='amcat.CodedArticleStatus'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='codedarticle',
            unique_together=set([('codingjob', 'article')]),
        ),
        migrations.AddField(
            model_name='codebookcode',
            name='function',
            field=models.ForeignKey(default=0, to='amcat.Function'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codebookcode',
            name='parent',
            field=models.ForeignKey(related_name='+', to='amcat.Code', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codebook',
            name='project',
            field=models.ForeignKey(to='amcat.Project'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='articleset',
            name='project',
            field=models.ForeignKey(related_name='articlesets_set', to='amcat.Project'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='medium',
            field=models.ForeignKey(to='amcat.Medium'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='parent',
            field=models.ForeignKey(related_name='children', db_column='parent_article_id', blank=True, to='amcat.Article', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='project',
            field=models.ForeignKey(related_name='articles', to='amcat.Project'),
            preserve_default=True,
        ),
    ]
