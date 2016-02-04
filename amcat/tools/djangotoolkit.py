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
Useful functions for dealing with django (models)x
"""


import collections
import json
import re
import time
import urllib
import django
from contextlib import contextmanager
from datetime import datetime

from django.dispatch import Signal
from django.conf import settings
from django.db import connections
from django.db import models, connection
from django.db.models import sql
from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField
from django.http import QueryDict

from amcat.tools.table.table3 import ObjectTable, SortedTable

def parse_date(date):
    """Parse date according to DATE_INPUT_FORMATS in settings"""
    for format in settings.DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(date, format).date()
        except (ValueError, TypeError):
            continue

    raise ValueError("Not a valid date found for {date}. Tried: {settings.DATE_INPUT_FORMATS}.".format(**locals()))

def to_querydict(d, mutable=False):
    """Convert a normal dictionary to a querydict. The dictionary can have lists as values,
    which are interpreted as multiple arguments for one url-parameter."""
    # querydict cannot handle unicode, so utf-8 encode unicode content first
    # TODO: this stinks
    def encode(s):
        if isinstance(s, list):
            return map(encode, s)
        elif isinstance(s, str):
            return s.encode("utf-8")
        else:
            return s
            
    d = {k : encode(v) for (k,v) in d.items()}
    return QueryDict(urllib.urlencode(d, True), mutable=mutable)

def from_querydict(d):
    """Convert a QueryDict to a normal dictionary with lists as values."""
    return dict(d.iterlists())

def db_supports_distinct_on(db='default'):
    """
    Return a boolean indicating whether this database supports DISTINCT ON.
    
    @param db: database to consider
    @type db: str
    """
    return connections[db].features.can_distinct_on_fields


def bulk_insert_returning_ids(new_objects, fields=None):
    """bulk_insert() does not set ids as per Django ticket #19527. However, postgres does
    support this, so we implement this manually in this function."""
    new_objects = list(new_objects)

    if not new_objects:
        return None

    if connection.vendor == "postgresql":
        model = new_objects[0].__class__
        query = sql.InsertQuery(model)
        query.insert_values(model._meta.fields[1:], new_objects)

        if django.VERSION[:3] < (1, 9, 0):
            pk = "{pk.db_column} AS {pk.name}".format(pk=model._meta.pk)
        else:
            pk = model._meta.pk.db_column

        raw_sql, params = query.sql_with_params()[0]
        fields = ", ".join([pk] + (fields if fields else []))
        new_objects = list(model.objects.raw("{raw_sql} RETURNING {fields}".format(**locals()), params))
    else:
        # Do naive O(n) approach
        for new_obj in new_objects:
            new_obj.save()

    return new_objects


def distinct_args(*fields):
    """
    return fields if the db supports distinct on, otherwise an empty list
    Intended usage: qs.distinct(*distinct_args(field1, field2))
    This will run distinct(field1, field2) if supported, otherwise just distinct()
    """
    return fields if db_supports_distinct_on() else []

def get_related(appmodel):
    """Get a sequence of model classes related to the given model class"""
    # from modelviz.py:222 vv
    for field in appmodel._meta.fields:
        if isinstance(field, (ForeignKey, OneToOneField)):
            yield field.related.parent_model
    if appmodel._meta.many_to_many:
        for field in appmodel._meta.many_to_many:
            if isinstance(field, ManyToManyField) and getattr(field, 'creates_table', False):
                yield field.related.parent_model

def get_all_related(modelclasses):
    """Get all related model classes from the given model classes"""
    for m in modelclasses:
        for m2 in get_related(m):
            yield m2

def get_or_create(model_class, **attributes):
    """Retrieve the instance of model_class identified by the given attributes,
    or if not found, create a new instance with these attributes"""
    try:
        return model_class.objects.get(**attributes)
    except model_class.DoesNotExist:
        return model_class.objects.create(**attributes)


@contextmanager
def list_queries(dest=None, output=False, printtime=False, outputopts=None):
    """Context manager to print django queries

    Any queries that were used in the context are placed in dest,
    which is also yielded.
    Note: this will set settings.DEBUG to True temporarily.
    """
    outputopts = outputopts or {}
    t = time.time()
    if dest is None: dest = []
    from django.conf import settings
    from django.db import connection
    nqueries = len(connection.queries)
    debug_old_value = settings.DEBUG
    settings.DEBUG = True
    try:
        yield dest
        dest += connection.queries[nqueries:]
    finally:
        settings.DEBUG = debug_old_value
        if output:
            print("Total time: %1.4f" % (time.time() - t))
            query_list_to_table(dest, output=output, **outputopts)


def query_list_to_table(queries, maxqlen=120, output=False, normalise_numbers=True, **outputoptions):
    """Convert a django query list (list of dict with keys time and sql) into a table3
    If output is non-False, output the table with the given options
    Specify print, "print", or a stream for output to be printed immediately
    """
    time = collections.defaultdict(list)
    for q in queries:
        query = q["sql"]
        if normalise_numbers:
            query = re.sub(r"\d+", "#", query)
        #print(query)
        time[query].append(float(q["time"]))
    t =  ObjectTable(rows = time.items())
    t.addColumn(lambda kv : len(kv[1]), "N")
    t.addColumn(lambda kv : kv[0][:maxqlen], "Query")
    cum = t.addColumn(lambda kv: "%1.4f" % sum(kv[1]), "Cum.")
    t.addColumn(lambda kv: "%1.4f" % (sum(kv[1]) / len(kv[1])), "Avg.")
    t = SortedTable(t, sort=cum)
    if output:
        if "stream" not in outputoptions and output is not True:
            if output in (print, "print"):
                import sys
                outputoptions["stream"] = sys.stdout
            else:
                outputoptions["stream"] = output
        t.output(**outputoptions)
    return t

def get_model_field(obj, field_name):
    """Given a nested fieldname, retrieve value. For example:

    >>> article = Article.objects.get(id=1)
    >>> get_model_field(article, "medium__name")
    "The Guardian"
    """
    fields = field_name.split("__")

    while fields:
        field = fields.pop(0)
        obj = getattr(obj, field)

    return obj

def get_ids(objects):
    """Convert the given object(s) to integers by asking for their .pk.
    Safe to call on integer objects"""
    for obj in objects:
        if not isinstance(obj, int):
            obj = obj.pk
        yield obj


def receiver(signal, sender=None, **kwargs):
    """
    A decorator for connecting receivers to signals. Used by passing in the
    signal and keyword arguments to connect::

        @receiver(post_save, sender=MyModel)
        def signal_receiver(sender, **kwargs):
            ...

    """
    def _decorator(func):
        if isinstance(signal, Signal):
            signals = [signal]
        else:
            signals = signal
        if sender is None or isinstance(sender, type):
            senders = [sender]
        else:
            senders = sender
        for sig in signals:
            for sen in senders:
                sig.connect(func, sen, **kwargs)
        return func
    return _decorator


class JsonField(models.Field):
    __metaclass__ = models.SubfieldBase
    serialize_to_string = True
    def get_internal_type(self):
        return "TextField"
    def value_to_string(self, obj):
        return self.get_prep_value(self._get_val_from_obj(obj))
    def get_prep_value(self, value):
        if value:
            return json.dumps(value)
        return None
    def to_python(self, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

