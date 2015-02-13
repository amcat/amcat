###########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)                     #
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

import logging
log = logging.getLogger(__name__)


def _get_pivot(row, column):
    for c, value in row:
        if str(c) == column:
            return float(value)
    return 0.0


def get_relative(aggregation, column):
    # TODO: We should probably make aggregation an ordered dict of ordered
    # TODO: dicts, thus making this algorithm run more cheaply.
    pivots = (_get_pivot(row[1], column) for row in aggregation)
    for pivot, (row, row_values) in zip(pivots, aggregation):
        if not pivot:
            continue

        yield row, tuple((col, value / pivot) for col, value in row_values)


# Unittests: amcat.tools.tests.aggregate
