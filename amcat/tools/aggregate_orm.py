"""
Contains logic to aggregate using Postgres / Django ORM, similar to amcates.py.
"""
import collections

from django.db.models import Avg

from amcat.models import Article, CodingSchemaField, CodingValue, Code
from amcat.models.coding.codingschemafield import  FIELDTYPE_IDS

ARTICLE_AGGREGATES = ("date", "medium")
ARTICLE_EXCLUDE = (
    "section", "pagenr", "headline", "byline", "length", "metastring",
    "url", "externalid", "author", "addressee", "uuid", "text", "parent",
    "project", "insertscript", "insertdate"
)

def to_article_ids(articles):
    for article in articles:
        if isinstance(article, Article):
            yield article.id
        else:
            yield article

class Category(object):
    def _aggregate_on_field(self, objects, field):
        aggregate = collections.defaultdict(set)
        for obj in objects:
            value = getattr(obj, field)
            aggregate[value].add(obj)
        return aggregate

    def aggregate(self, codingjob_ids, article_ids):
        """
        @type codingjob_ids: list
        @type article_ids: list
        @return: dictionary of the form {value: [article_id|Article]}
        """
        raise NotImplementedError("Subclasses should implement aggregate(codingjob_ids, article_ids).")

class IntervalCategory(Category):
    def __init__(self, interval):
        super(IntervalCategory, self).__init__()
        self.interval = interval

    def aggregate(self, codingjob_ids, article_ids):
        articles = Article.objects.filter(id__in=article_ids)
        extra = "date_trunc('{interval}', date)".format(interval=self.interval)
        aggregate = articles.extra({'interval': extra}).defer().select_related().only("id")
        aggregate = self._aggregate_on_field(aggregate, "interval")
        aggregate = {date: [a.id for a in arts] for date, arts in aggregate.items()}
        return aggregate

    def __repr__(self):
        return "<Interval: %s>" % self.interval

class YearCategory(IntervalCategory):
    def __init__(self):
        super(YearCategory, self).__init__("year")

class QuarterCategory(IntervalCategory):
    def __init__(self):
        super(QuarterCategory, self).__init__("quarter")

class MonthCategory(IntervalCategory):
    def __init__(self):
        super(MonthCategory, self).__init__("month")

class WeekCategory(IntervalCategory):
    def __init__(self):
        super(WeekCategory, self).__init__("week")

class DayCategory(IntervalCategory):
    def __init__(self):
        super(DayCategory, self).__init__("day")

class MediumCategory(Category):
    def aggregate(self, codingjob_ids, article_ids):
        articles = Article.objects.filter(id__in=article_ids).only("id", "medium").select_related("medium")
        aggregate = super(MediumCategory, self)._aggregate_on_field(articles, "medium")
        aggregate = {medium: [a.id for a in arts] for medium, arts in aggregate.items()}
        return aggregate

class SchemafieldCategory(Category):
    def __init__(self, field):
        self.field = field

    def aggregate(self, codingjob_ids, article_ids):
        coding_values = (CodingValue.objects
                         .filter(field__id=self.field.id)
                         .filter(coding__coded_article__codingjob__id__in=codingjob_ids)
                         .filter(coding__coded_article__article__id__in=article_ids)
                         .values_list("coding__coded_article__article_id", "intval"))

        codes = Code.objects.in_bulk([code_id for (aid, code_id) in coding_values])

        aggregate = collections.defaultdict(set)
        for aid, code_id in coding_values:
            aggregate[code_id and codes[code_id]].add(aid)
        return aggregate

    def __repr__(self):
        return "<SchemafieldCategory: %s>" % self.field

class BaseAggregationValue:
    def aggregate(self, codingjobs, article_ids, codingschemafield=None):
        """
        @param
        @type codingschemafield: (int, int)
        """
        raise NotImplementedError("Subclasses should implement aggregate(codingjob_ids, article_ids).")

class Average(BaseAggregationValue):
    def __init__(self, field):
        """@type field: CodingSchemaField"""
        assert_msg = "Average only aggregates on codingschemafields for now"
        assert isinstance(field, CodingSchemaField), assert_msg
        self.field = field

    def aggregate(self, codingjob_ids, article_ids, codingschemafield=None):
        coding_values = CodingValue.objects.all()

        if codingschemafield:
            csid, csvalue = codingschemafield
            coding_values = coding_values.filter(
                coding__coded_article__codings__values__field__id=csid,
                coding__coded_article__codings__values__intval=csvalue,
            )

        average = (coding_values
            .filter(field__id=self.field.id)
            .filter(coding__coded_article__codingjob__id__in=codingjob_ids)
            .filter(coding__coded_article__article__id__in=article_ids)
            .aggregate(avg=Avg("intval"))
            .values()[0]
        )

        return average

    def __repr__(self):
        return "<Average: %s>" % self.field

class Count(BaseAggregationValue):
    def aggregate(self, codingjob_ids, article_ids, codingschemafield=None):
        return len(article_ids)


class ORMAggregate(object):
    def __init__(self, codingjob_ids, article_ids, flat=False, empty=False):
        self.article_ids = article_ids
        self.codingjob_ids = codingjob_ids
        self.flat = flat
        self.empty = empty

    def _get_aggregate_categories(self, categories, values, article_ids, codingschemafield=None):
        category = categories.pop(0)
        aggregated = category.aggregate(self.codingjob_ids, article_ids)
        for bucket, article_ids in aggregated.items():
            if isinstance(category, SchemafieldCategory): # sorry wva..
                codingschemafield = (category.field.id, bucket.id)

            aggregated = tuple(self._get_aggregate(categories, values, article_ids, codingschemafield))

            if categories:
                for buckets, vals in aggregated:
                    yield (bucket,) + buckets, vals
            else:
                yield ((bucket,), aggregated)

    def _get_aggregate_values(self, values, article_ids, codingschemafield=None):
        for value in values:
            yield value.aggregate(self.codingjob_ids, article_ids, codingschemafield)

    def _get_aggregate(self, categories, values, article_ids, codingschemafield=None):
        categories = list(categories)
        values = list(values)

        if categories:
            return self._get_aggregate_categories(categories, values, article_ids, codingschemafield)
        else:
            return tuple(self._get_aggregate_values(values, article_ids, codingschemafield))

    def get_aggregate(self, categories=(), values=()):
        """
        @type codingjobs: QuerySet
        @type articles: QuerySet
        @type categories: iterable of Category
        @type values: iterable of Value
        """
        if not values:
            raise ValueError("You must specify at least one value.")

        aggregation = self._get_aggregate(categories, values, self.article_ids)

        # Filter empty values
        if not self.empty:
            aggregation = ((cats, vals) for cats, vals in aggregation if any(vals))

        # Flatten categories, i.e. [((Medium,), (1, 2))] to [((Medium, (1, 2))]
        if self.flat and len(categories) == 1:
            aggregation = ((cat[0], vals) for cat, vals in aggregation)

        # Flatten values, i.e. [(Medium, (1,))] to [(Medium, 1)]
        if self.flat and len(values) == 1:
            aggregation = ((cats, val[0]) for cats, val in aggregation)

        return aggregation

