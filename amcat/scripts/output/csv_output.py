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

import csv
import io

from amcat.tools.table import tableoutput

def table_to_csv(table_obj, delimiter=","):
    """Convert a table3 object to a csv file (string)"""
    buff = io.StringIO()

    tableoutput.table2csv(table_obj, csvwriter=csv.writer(
        buff, dialect='excel', delimiter=delimiter),
        writecolnames=True, writerownames=False, tabseparated=False
    )

    return buff.getvalue()

