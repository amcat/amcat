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
This module contains helper functions for more efficient counting of
query results.
"""

from django.db.models.query import QuerySet
from django.db import connection, DatabaseError
from django.db.models.sql.where import WhereNode

from amcat.models import Article, ArticleSet, ArticleSetArticle

import logging; log = logging.getLogger(__name__)

SIMPLIFY = {
    Article: {
        ("articleset_id", ArticleSet) : ("articleset", ArticleSetArticle)
    }
}


def _get_single_where(node):
    """
    Simplify a where clause to a single X=Y constraint, or raise a ValueError if that is impossible
    """
    if hasattr(node, "children"):
        # WhereNode with children
        if node.negated:
            raise ValueError("Negated node: {node}".format(**locals()))
        wheres = (_get_single_where(c) for c in node.children)
        wheres = [x for x in wheres if x is not None]
        if len(wheres) > 1:
            raise ValueError("Node {node} has multiple wheres: {wheres}".format(**locals()))
        elif len(wheres) == 1:
            return wheres[0]
    else:
        # tuple node
        return node

def simplify_count(qs):
    """
    If possible, simplify the count query to remove unneeded joins (i.e. what the query optimizer
    was hired for). Since we only have the query set to go from, need to inspect it to see whether
    we can optimize. For safety, only optimize known relations from SIMPLIFY
    """
    if qs.model not in SIMPLIFY: raise ValueError("Can't simplify %s" % qs.model)

    # Get the single conjoined where clause, or raise a ValueError trying
    where = _get_single_where(qs.query.where)

    if where is None:
        raise ValueError("No where clause, nothing to simplify")

    constraint, test, annotation, value = where
    column, model = constraint.field.column, constraint.field.model

    if test != 'exact' or annotation is not True or (column, model) not in SIMPLIFY[qs.model] :
        raise ValueError("Can't simplify %s %s %s:%s" % (qs.model, test, model, column))

    # So now we know that the query has one equality constraint on a column on a different table
    # i.e. the query is of form qs.model.objects.filter(model__field=value)
    # check whether we can simplify this query
    simple_column, simple_model = SIMPLIFY[qs.model][column, model]
    return simple_model.objects.filter(**{simple_column : value}).count()

def approximate_count(qs):
    """
    Postgres keeps a counter for each table in pg_class. When no WHERE-
    clauses are applied to the query, return that value.
    """
    SQL = "SELECT reltuples FROM pg_class WHERE relname=%s"

    if not len(qs.query.where.children):
        # This query does not use any WHERE-clauses
        cursor = connection.cursor()
        try:
            cursor.execute(SQL, [qs.model._meta.db_table])
            c = int(cursor.fetchone()[0])
        except DatabaseError:
            raise ValueError("Where clause used or database error. Cannot return approx count")
        else:
            if c >= 100: return c

        raise ValueError("Approximation not reliable")

    raise ValueError("Where clause(s) applied. Cannot return approx count")

def count(qs):
    """
    Selected the most efficient technique for counting this queryset
    """
    if not isinstance(qs, QuerySet):
        return len(qs)

    try:
        return simplify_count(qs)
    except ValueError, e:
        log.debug("Could not simplify count for {qs.query}: {e}".format(qs=qs, e=e))

    try:
        return approximate_count(qs)
    except ValueError, e:
        log.debug("Error on approximating {qs.query}: {e}".format(qs=qs, e=e))

    return qs.count()
