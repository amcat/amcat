###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Module with base class for resources in the amcat REST API
"""


from django.core.urlresolvers import reverse, NoReverseMatch
from django.conf.urls import patterns, url
from django.db.models.fields.related import RelatedObject, RelatedField


from rest_framework import generics, serializers, fields, relations

import api.rest.resources
from api.rest.serializer import AmCATModelSerializer
def get_related_fieldname(model, fieldname):
    field = model._meta.get_field_by_name(fieldname)[0]

    if isinstance(field, (RelatedObject, RelatedField)):
        return "{}__id".format(fieldname)

    return fieldname

class ClassProperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()
    
class AmCATResource(generics.ListAPIView):
    """
    Base class for the AmCAT REST API
    Subclassing modules should specify the model that the view is based on
    """

    model = None
    extra_filters = []
    ignore_filters = ['auth_token__id']

    @classmethod
    def _get_filter_fields_for_model(cls):
        for fieldname in cls.model._meta.get_all_field_names():
            fieldname = get_related_fieldname(cls.model, fieldname)
            if fieldname in cls.ignore_filters:
                continue
            yield fieldname
    
    @classmethod
    def get_filter_fields(cls):
        """Return a list of fields that will be used to filter on"""
        result = ['pk']
        for field in cls._get_filter_fields_for_model():
            result.append(field)
        for field in cls.extra_filters:
            result.append(field)
        return result
    filter_fields=ClassProperty(get_filter_fields)
    
    @classmethod
    def get_url_pattern(cls):
        """The url pattern for use in the django urls routing table"""
        pattern = r'^{model_name}$'.format(model_name=cls.get_model_name())
        return url(pattern, cls.as_view(), name=cls.get_view_name())
    
    @classmethod
    def get_model_name(cls):
        """The 'name' of this view, used in the url (api/v4/NAME/) and the view name"""
        return cls.model.__name__.lower()
    
    @classmethod
    def get_view_name(cls):
        """The 'view name' of this view, ie the thing that can be used in reverse(.)"""
        return 'api-v4-{model_name}'.format(model_name=cls.get_model_name())

    @classmethod
    def get_name(cls):
        """The human readable name of this view"""
        return "{model} List".format(model=cls.get_model_name().title())
    
    @classmethod
    def get_url(cls):
        """Get the url for this view."""
        return reverse(cls.get_view_name())

    @classmethod
    def get_label(cls):
        return '{{{label}}}'.format(
            label=getattr(cls.model, '__label__', 'label')
        )

    @classmethod
    def get_rowlink(cls):
        try:
            return reverse(cls.model.__name__.lower(), kwargs=dict(id=123)).replace('123', '{id}')
        except NoReverseMatch:
            return None

    @property
    def url(self):
        """
        Get the url for this view. Convenience and compatibility shortcut for classmethod get_url
        Needs to be an instance attribute as class properties are not possible?
        """
        return self.get_url()

    @classmethod
    def get_field_names(cls):
        """Get a list of field names from the serializer"""
        # We are a class method and rest_framework likes instance methods, so lots of ()'s
        return [name for (name, field) in cls().get_serializer_class()().get_fields().iteritems()
                if not AmCATModelSerializer.skip_field(field)]
    
    def metadata(self, request):
        """This is used by the OPTIONS request; add models, fields, and label for datatables"""
        metadata = super(AmCATResource, self).metadata(request)
        metadata['label'] = self.get_label() 
        grfm = api.rest.resources.get_resource_for_model
        metadata['models'] = {name : grfm(field.queryset.model).get_url()
                              for (name, field) in self.get_serializer().get_fields().iteritems()
                              if hasattr(field, 'queryset')}
        
        metadata['fields'] = {name : _get_field_name(field)
                              for (name, field) in  self.get_serializer().get_fields().iteritems()}

        metadata['filter_fields'] = list(self.get_filter_fields())

        return metadata


    @classmethod
    def create_subclass(cls, use_model):
        """
        Create a subclass of this class with the given model. The name will
        be set to <Model>Resource.
        """
        class subclass(cls):
            model = use_model
        subclass.__name__ = '{use_model.__name__}Resource'.format(**locals())
        if subclass.__name__ == 'AmCATResource':
            subclass.__name__ = 'AmCATSystemResource'
        return subclass



def _get_field_name(field):
    "Return the field name to report in OPTIONS (for datatables)"
    n = field.__class__.__name__
    return dict(PrimaryKeyRelatedField='ModelChoiceField',
                ManyPrimaryKeyRelatedField='ModelMultipleChoiceField',
                ).get(n,n)




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from api.rest.apitestcase import ApiTestCase

class TestAmCATResource(ApiTestCase):
    def test_get_field_names(self):
        from api.rest.resources.amcatresource import AmCATResource
        from api.rest.serializer import AmCATModelSerializer
        from amcat.models import Project

        # Test order of fields.
        class TestSerializer(AmCATModelSerializer):
            class Meta:
                model = Project
                fields = ('name', 'description', 'id')

        class TestResource(AmCATResource):
            model = Project
            serializer_class = TestSerializer

        self.assertEqual(
            tuple(TestResource.get_field_names()),
            ('name', 'description', 'id')
        )

        # Test exclude
        class TestSerializer(AmCATModelSerializer):
            class Meta:
                model = Project
                exclude = ('id',)

        class TestResource(AmCATResource):
            model = Project
            serializer_class = TestSerializer

        self.assertTrue('id' not in TestResource.get_field_names())


    def test_page_size(self):
        from api.rest.resources import ProjectResource 

        amcattest.create_test_project(name="t", description="t", insert_date="2011-01-01")
        amcattest.create_test_project(name="t2", description="t2", insert_date="2011-01-01")

        # Assumes that default page_size is greater or equal to 2..
        self.assertEqual(len(self.get(ProjectResource)['results']), 2)

        res = self.get(ProjectResource, page_size=1)
        self.assertEqual(len(res['results']), 1)
        self.assertEqual(res['total'], 2)
        self.assertEqual(res['per_page'], 1)
    
    def test_options(self):
        from api.rest.resources import ArticleResource, ProjectResource
        opts = self.get_options(ProjectResource)
        name = u'Project Resource'
        models = {u'owner': u'/api/v4/user', u'guest_role': u'/api/v4/role',
                  #these should NOT be included as we don't want the foreign key fields
                  #u'codebooks': u'/api/v4/codebook',
                  #u'codingschemas': u'/api/v4/codingschema',
                  #u'articlesets': u'/api/v4/articleset',
                  u'insert_user': u'/api/v4/user', }
        
        fields = {u'index_default': u'BooleanField', u'name': u'CharField', u'guest_role': u'ModelChoiceField',
                  #these should NOT be included as we don't want the foreign key fields
                  #u'codebooks': u'ModelChoiceField', u'codingschemas': u'ModelChoiceField',
                  #u'articlesets': u'ModelChoiceField',
                  u'owner': u'ModelChoiceField', u'active': u'BooleanField', u'description': u'CharField',
                  u'id': u'IntegerField',
                  u'insert_date': u'DateTimeField',
                  u'insert_user': u'ModelChoiceField',
                  u'favourite': u'SerializerMethodField',
                  }
        parses = [u'application/json', u'application/x-www-form-urlencoded', u'multipart/form-data',
                  u'application/xml']
        label = u'{name}'
        renders = {u'application/json', u'text/html'}#, u'text/csv'}
        description = u''
        
        
        self.assertEqual(opts['name'], name)
        self.assertEqual(opts['label'], label)
        self.assertEqual(opts['description'], description)

            
        
        self.assertDictsEqual(opts['models'], models)
        self.assertDictsEqual(opts['fields'], fields)
        # CSV not supported yet, this will fail:
        missing = renders - set(opts['renders'])
        self.assertFalse(missing, "Missing renderers: {missing}".format(**locals()))

