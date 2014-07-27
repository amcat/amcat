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
from django.conf.urls import url
from rest_framework import generics

from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest import tablerenderer

class AmCATResource(DatatablesMixin, generics.ListAPIView):
    """
    Base class for the AmCAT REST API
    Subclassing modules should specify the model that the view is based on
    """
    model = None
    ordering_fields = ("id",)

    def __init__(self, *args, **kwargs):
        super(AmCATResource, self).__init__(*args, **kwargs)

        # TODO: Remove this hack. Djangorestframework uses serializer_class to determine
        # TODO: the fields a resource has, but does not bother to call get_serializer_class,
        # TODO: resulting in errors.
        if self.serializer_class is None:
            self.serializer_class = self.get_serializer_class()

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
                if not AmCATModelSerializer.skip_field(name, field)]
    
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

    def finalize_response(self, request, response, *args, **kargs):
        response = super(AmCATResource, self).finalize_response(request, response, *args, **kargs)
        response = tablerenderer.set_response_content(response)
        return response


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
        name = u'api-v4-project'
        models = {u'owner': u'/api/v4/user', u'guest_role': u'/api/v4/role',
                  #these should NOT be included as we don't want the foreign key fields
                  #u'codebooks': u'/api/v4/codebook',
                  #u'codingschemas': u'/api/v4/codingschema',
                  #u'articlesets': u'/api/v4/articleset',
                  u'insert_user': u'/api/v4/user', }
        
        fields = {u'name': u'CharField',
                  u'guest_role': u'ModelChoiceField',
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

