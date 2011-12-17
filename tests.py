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
Test cases that are automatically detected and run by django

Please don't include test cases here directly, but place them in an appropriate
location and import here
"""


from amcat.tools.logging.amcatlogging import *
from amcat.tools.amcattest import *
from amcat.tools.djangotoolkit import *
from amcat.tools.table.table3 import *
from amcat.tools.caching import *
from amcat.tools.dbtoolkit import *
from amcat.tools.sendmail import *

from amcat.model.coding.codingtoolkit import *
from amcat.model.coding.serialiser import *

from amcat.scripts.article_upload.tests import *
from amcat.scripts.scriptmanager import *

from amcat.model.coding.test_nqueries import *
