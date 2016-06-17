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
import functools
from itertools import chain
from typing import Sequence

from amcat.tools.model import PostgresNativeUUIDField
from django.db import models
from django.db.models import QuerySet

from exportable import columns, DeclaredTable
from exportable.columns import UUIDColumn
from exportable.table import AttributeTable, get_declared_columns, filter_columns, DictTable

from api5.columns import ModelColumn, PrimaryKeyColumn

FIELD_MAP = {
    models.AutoField: PrimaryKeyColumn,  # FIXME: only true for AmCAT
    models.ForeignKey: ModelColumn,
    models.IntegerField: columns.IntColumn,
    models.TextField: columns.TextColumn,
    models.CharField: columns.TextColumn,
    models.DateTimeField: columns.DateTimeColumn,
    PostgresNativeUUIDField: UUIDColumn
}


def get_column_from_field(field: models.Field):
    if field.__class__ not in FIELD_MAP:
        raise ValueError("Could not convert {} to exportable Column".format(field))

    column_class = FIELD_MAP[field.__class__]
    if column_class is ModelColumn:
        column = column_class(model=field.model, label=field.name, verbose_name=field.verbose_name)
    else:
        column = column_class(label=field.name, verbose_name=field.verbose_name)
    column._django_fields = field  # Backref to original Django Field
    return column


@functools.lru_cache()
def build_declared_table(model: type(models.Model)):
    columns = map(get_column_from_field, model._meta.fields)
    decl_table_name = "{}Table".format(model.__name__)
    decl_table_attrs = {c.label: c for c in columns}
    return type(decl_table_name, (DeclaredTable,), decl_table_attrs)


class QuerySetTable(DictTable):
    def __init__(self, rows: QuerySet, columns: Sequence[columns.Column], *args, **kwargs):
        # Save queryset so it is accessible by columns
        self.queryset = rows

        # Determine rows based on queryset
        column_labels = [c.label for c in columns if not c.rowfunc]
        rows = rows.values_list(*column_labels)
        rows = (dict(zip(column_labels, row)) for row in rows)

        super().__init__(rows, columns, *args, **kwargs)

    def __len__(self):
        return self.queryset.count()


class DeclaredModelTable(DeclaredTable):
    @classmethod
    def _get_columns(cls):
        include = getattr(cls.Meta, "include", None)
        exclude = getattr(cls.Meta, "exclude", None)

        for attr in (a for a in dir(cls.Meta) if not a.startswith("_")):
            if attr not in ("include", "exclude", "model"):
                raise ValueError("{} on {} is not a recognized option".format(attr, cls.Meta))

        if not hasattr(cls.Meta, "model") or cls.Meta.model is None:
            raise ValueError("DeclaredModelTables must have a model declared.")

        table = build_declared_table(cls.Meta.model)
        columns = chain(get_declared_columns(table), super()._get_columns())
        return filter_columns(columns, include=include, exclude=exclude)

    class Meta:
        model = None
        include = None
        exclude = None