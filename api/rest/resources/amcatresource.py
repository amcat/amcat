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
from django.conf.urls import url
from django.core.urlresolvers import reverse, NoReverseMatch
from django_filters.rest_framework import FilterSet
from django_filters import rest_framework as filters
from rest_framework import generics

from api.rest import tablerenderer
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer


class AmCATResource(DatatablesMixin, generics.ListAPIView):
    """
    Base class for the AmCAT REST API
    Subclassing modules should specify the model that the view is based on
    """
    model = None
    ordering_fields = ("id",)
    required_scopes = ['resources']

    def __init__(self, *args, **kwargs):
        super(AmCATResource, self).__init__(*args, **kwargs)

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
        return reverse("api:" + cls.get_view_name())

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
        return cls().get_serializer_class()().get_fields().keys()

    @classmethod
    def create_subclass(cls, use_model):
        """
        Create a subclass of this class with the given model. The name will
        be set to <Model>Resource.
        """
        class subclass(cls):
            queryset = use_model.objects.all()
            class serializer_class(AmCATModelSerializer):
                class Meta:
                    model = use_model
                    fields = '__all__'

            class filter_class(FilterSet):
                class Meta:
                    model = use_model
                    exclude = 'parameters', 'properties'

            model = use_model

        subclass.__name__ = '{use_model.__name__}Resource'.format(**locals())
        if subclass.__name__ == 'AmCATResource':
            subclass.__name__ = 'AmCATSystemResource'
        return subclass

    @classmethod
    def get_label(cls):
        try:
            model = cls.queryset.model
        except AttributeError:
            model = cls.model

        return "{" + getattr(model, '__label__', 'label') + "}"

    def finalize_response(self, request, response, *args, **kargs):
        format = request.query_params.get("format", request.data.get("format", "api"))
        filename = request.query_params.get("filename", request.data.get("filename", "data"))
        response = super(AmCATResource, self).finalize_response(request, response, *args, **kargs)
        response = tablerenderer.set_response_content(response, format, filename)
        return response

    def get_queryset(self):
        return self.model.objects.all()