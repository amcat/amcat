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

SUPERADMIN_ROLE = 3
DEVELOPER_ROLE = 4

NAVIGATOR_MENU_CACHE = "navigator_menu_%s"

NAVIGATOR_MENU = [
    # (title, view[, minimum_role])
    ("Home", "navigator.views.report.index"),
    ("Projects", "navigator.views.project.projectlist_favourite"),
    ("Coding Jobs", "navigator.views.codingjob.index"),
    #("Query", None),
    #("Article Selection", "navigator.views.selection.index"),
    #("REST browser", "api.views.index"),
    #("Editors", None),
    #("Annotationschema's", 'navigator.views.schemas.index'),
    ("Lists", None),
    ("Media", "navigator.views.report.media"),
    ("Users", "users"),
    ("Plugins", "plugins"),
    ("Scrapers", "scrapers"),
    
    #("Ontology", "navigator.views.nyi.index"),
    ("User", None),
    ("My Details", "navigator.views.user.view"),
    ("Log out", "accounts.views.logout"),
    # ("Admin", None),
    # ("Server status", "navigator.views.nyi.index"),
    ("Developer", None, DEVELOPER_ROLE),
    ("API", "api", DEVELOPER_ROLE),
    ("Google Code", "http://code.google.com/p/amcat/", DEVELOPER_ROLE),
]

### These are rendered in navigator/base.html ###
PROJECT_MENU = (
    ('overview', 'project'),
    ('article sets', 'project-articlesets'),
    ('query', 'project-selection'),
    ('codingjobs', 'project-codingjobs'),
    ('codingschemas', 'project-schemas'),
    ('codebooks', 'project-codebooks'),
    ('users', 'project-users'),
    ('preprocessing', 'project-preprocessing'),
)

PROJECT_OVERVIEW_MENU = (
    ('favourite projects', 'navigator.views.project.projectlist_favourite'),
    ('my projects', 'navigator.views.project.projectlist_my'),
    ('all projects', 'navigator.views.project.projectlist_all')
)

USER_MENU = (
    ('active affiliated users', 'navigator.views.user.my_affiliated_active'),
    ('all affiliated users', 'navigator.views.user.my_affiliated_all'),
    ('all users', 'navigator.views.user.all'),
)

CODINGJOB_MENU = (
    ('unfinished jobs', 'navigator.views.codingjob.index'),
    ('all jobs', 'navigator.views.codingjob.all')
)
