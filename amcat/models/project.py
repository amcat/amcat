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

"""ORM Module representing projects"""

import itertools
from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q
from typing import Union, Set

import amcat.models
from amcat.models import ProjectRole
from amcat.tools.model import AmcatModel
from amcat.models.coding.codebook import Codebook
from amcat.models.coding.codingschema import CodingSchema
from amcat.models.article import Article
from amcat.models.articleset import ArticleSetArticle, ArticleSet

from amcat.models.authorisation import Role, ROLE_PROJECT_READER

LITTER_PROJECT_ID = 1

LAST_VISITED_FIELD_NAME = "last_visited_at"

import logging; log = logging.getLogger(__name__)


class Project(AmcatModel):
    """Model for table projects.

    Projects are the main organizing unit in AmCAT. Most other objects are
    contained within a project: articles, sets, codingjobs etc.

    Projects have users in different roles. For most authorisation questions,
    AmCAT uses the role of the user in the project that an object is contained in
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='project_id', editable=False)

    name = models.CharField(max_length=50)
    description = models.CharField(max_length=200, null=True)

    insert_date = models.DateTimeField(db_column='insertdate', auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, db_column='owner_id')

    # We need null=True to prevent djangorestframework from complaining about it, as
    # it asserts required=True and editable=False to be an error. This is probably
    # fine from an API point of view, but not really in combination with Django. Anyway,
    # here's the bug report:
    #    https://github.com/tomchristie/django-rest-framework/issues/1658
    insert_user = models.ForeignKey(settings.AUTH_USER_MODEL, db_column='insertuser_id',
                                    related_name='inserted_project',
                                    editable=False, null=True)

    guest_role = models.ForeignKey("amcat.Role", default=ROLE_PROJECT_READER, null=True)

    active = models.BooleanField(default=True)

    # Temporary field enabling R plugins in the query screen
    r_plugins_enabled = models.BooleanField(default=False)

    # Coding fields
    codingschemas = models.ManyToManyField("amcat.CodingSchema", related_name="projects_set")
    codebooks = models.ManyToManyField("amcat.Codebook", related_name="projects_set")
    articlesets = models.ManyToManyField("amcat.ArticleSet", related_name="projects_set")
    favourite_articlesets = models.ManyToManyField("amcat.articleset", related_name="favourite_of_projects")

    def get_used_properties(self, only_favourites=False) -> Set[str]:
        articlesets = (self.favourite_articlesets if only_favourites else self.articlesets).all().only("id")
        return set(itertools.chain.from_iterable(aset.get_used_properties() for aset in articlesets))

    def get_codingschemas(self):
        """
        Return all codingschemas connected to this project. This returns codingschemas
        owned by it and linked to it.
        """
        return CodingSchema.objects.filter(Q(projects_set=self)|Q(project=self)).distinct()

    def get_codebooks(self):
        """
        Return all codebooks connected to this project. This returns codebooks
        owned by it and linked to it.
        """
        return Codebook.objects.filter(Q(projects_set=self)|Q(project=self)).distinct()

    @property
    def users(self):
        """Get a list of all users with some role in this project"""
        return (r.user for r in self.projectrole_set.all())

    def all_articlesets(self, distinct=True):
        """
        Get a set of articlesets either owned by this project or
        contained in a set owned by this project
        """
        sets = ArticleSet.objects.filter(Q(project=self)|Q(projects_set=self))
        if distinct: return sets.distinct()
        return sets

    def all_articles(self):
        """
        Get a set of articles either owned by this project
        or contained in a set owned by this project
        """
        return Article.objects.filter(Q(articlesets_set__project=self)|Q(project=self)).distinct()

    def get_all_article_ids(self):
        """
        Get a sequence of article ids either owned by this project
        or contained in a set owned by this project
        """
        return itertools.chain(
            Article.objects.filter(project=self).values_list("id", flat=True),
            ArticleSetArticle.objects.filter(articleset__project=self).values_list("article__id", flat=True)
        )

    class Meta():
        db_table = 'projects'
        app_label = 'amcat'
        ordering = ('name',)

    def save(self, *args, **kargs):
        if self.insert_user_id is None:
            # Import at top causes a circular import, unfortunately
            from navigator.utils.auth import get_request

            # No insert user is set, try to retrieve it
            req = get_request()
            if req is not None:
                self.insert_user_id = req.user.id

        super(Project, self).save(*args, **kargs)

    def has_role(self, user: "amcat.models.User", role: Union[str, int, Role]):
        """
        Returns whether the user has the given role on this project
        If user is site-admin, always return True
        @param role: a role instance, ID, or label
        @param user: a user object
        """
        if user.is_superuser:
            return True

        if isinstance(role, str):
            role_id = Role.objects.get(label=role).id
        elif isinstance(role, Role):
            role_id = role.id
        else:
            role_id = role

        actual_role_id = self.get_role_id(user=user)

        log.info("{user.id}:{user.username} has role {actual_role_id} on project {self}, >=? {role_id}"
                 .format(**locals()))

        return actual_role_id is not None and actual_role_id >= role_id

    def get_role_id(self, user=None):
        """
        Return the role id that this user has, by his own right or as guest
        If user is None, returns the guest role id
        """
        project_role = None
        guest_role = self.guest_role_id

        if user and not user.is_anonymous():
            try:
                project_role = self.projectrole_set.get(user=user).role_id
            except ProjectRole.DoesNotExist:
                pass

        # int > None is removed in python3, so avoid direct comparison
        if project_role is None: return guest_role
        if guest_role is None: return project_role
        return max(project_role, guest_role)


class RecentProject(AmcatModel):

    user = models.ForeignKey("amcat.UserProfile")

    # related_name should be the same as the ProjectSerializer's column name to assert sortability
    project = models.ForeignKey(Project, related_name=LAST_VISITED_FIELD_NAME)
    date_visited = models.DateTimeField()

    def format_date_visited_as_delta(self):
        timediff = (datetime.now() - self.date_visited).total_seconds()
        if timediff < 1:
            return "just now"
        timespans = [1, 60, 3600, 86400, 604800, 1814400]
        names = ["second", "minute", "hour", "day", "week", None]

        name = None
        timespan = None
        for (n, t) in zip(names, timespans):
            if timediff / t < 1:
                break
            name = n
            timespan = t
        net_timespan = int(timediff / timespan)
        plural = "" if net_timespan == 1 else "s"
        if name:
            return "{} {}{} ago".format(net_timespan, name, plural)

        return self.date_visited

    @classmethod
    def get_recent_projects(cls, userprofile):
        """
        Returns recently created projects
        @param userprofile: the userprofile
        @return: The queryset of recent projects, ordered by date (descending)
        @rtype: django.db.models.query.QuerySet
        """
        return RecentProject.objects.filter(user=userprofile).order_by('-date_visited')

    @classmethod
    def update_visited(cls, userprofile, project, date_visited=None):
        """
        Creates or updates the date
        @returns: a tuple containing the RecentProject and a bool indicating whether it was created (`True`) or
            updated (`False`)
        @rtype: tuple[RecentProject, bool]
        """
        if not date_visited:
            date_visited = datetime.now()
        return RecentProject.objects.update_or_create({"date_visited": date_visited },
                                               user=userprofile, project=project)

    class Meta():
        db_table = 'user_recent_projects'
        unique_together = ("user", "project")
        app_label = "amcat"
        ordering = ["date_visited"]
