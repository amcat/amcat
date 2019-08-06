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
import uuid
from amcat.models import Coding, CodingValue, CodedArticle, Article, CodingJob


class SQLObject(object):
    joins_needed = []

    def __init__(self, prefix=None):
        self.prefix = uuid.uuid4().hex if prefix is None else prefix

    def get_setup_statements(self):
        """Yield sql statements which should be executed before the aggregation
        begins. This could be used to create and populate temporary tables and
        indices."""
        return ()

    def get_teardown_statements(self):
        """Same as setup_statements, but executed after aggregation."""
        return ()

    def get_selects(self):
        raise NotImplementedError("Subclasses should implement get_selects().")

    def get_joins(self, seen_categories=None):
        return ()

    def get_wheres(self):
        return ()

    def get_group_by(self):
        return None


INNER_JOIN = r'INNER JOIN {table} AS T{{prefix}}_{table} ON ({prefix}{t1}.{f1} = T{{prefix}}_{table}.{f2})'


class JOINS:
    codings = INNER_JOIN.format(
        table=Coding._meta.db_table,
        t1=CodingValue._meta.db_table,
        f1="coding_id",
        f2="coding_id",
        prefix=""
    )

    coded_articles = INNER_JOIN.format(
        table=CodedArticle._meta.db_table,
        t1=Coding._meta.db_table,
        f1="coded_article_id",
        f2="id",
        prefix="T_"
    )

    articles = INNER_JOIN.format(
        table=Article._meta.db_table,
        t1=CodedArticle._meta.db_table,
        f1="article_id",
        f2="article_id",
        prefix="T_"
    )

    codings_values = INNER_JOIN.format(
        table=CodingValue._meta.db_table,
        t1=Coding._meta.db_table,
        f1="coding_id",
        f2="coding_id",
        prefix="T_"
    )

    codingjobs = INNER_JOIN.format(
        table=CodingJob._meta.db_table,
        t1=CodedArticle._meta.db_table,
        f1="codingjob_id",
        f2="codingjob_id",
        prefix="T_"
    )

    terms = INNER_JOIN.format(
        table="{{table}}",
        t1=Article._meta.db_table,
        f1="article_id",
        f2="article_id",
        prefix="T_"
    )
