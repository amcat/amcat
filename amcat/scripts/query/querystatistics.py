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
import json
from amcat.scripts.query import QueryAction


class StatisticsAction(QueryAction):
    """Statistics is a meta-action implemented allowing scripts to to query
    properties about the currently entered query. For example, it returns the
    included mediums, articlesets and terms for the current query. Note that
    it currently returns all mediums / articlesets as running the full query
    is yet to expensive.
    """
    output_types = (
        ("application/json+debug", "Inline"),
        ("application/json", "JSON"),
    )

    def run(self, form):
        return json.dumps({
            "ab": "cd",
            "abc": {
                "123": [1,2,3],
                "789": {
                    "abc": '123'
                }
            }
        })
