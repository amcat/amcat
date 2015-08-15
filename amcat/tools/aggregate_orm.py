"""
Contains logic to aggregate using Postgres / Django ORM, similar to amcates.py.
"""
import collections
from django.db.models import Avg
from amcat.models import Article, CodedArticle, Coding, CodingSchemaField, CodingValue

ARTICLE_AGGREGATES = ("date", "medium")
ARTICLE_EXCLUDE = (
    "section", "pagenr", "headline", "byline", "length", "metastring",
    "url", "externalid", "author", "addressee", "uuid", "text", "parent",
    "project", "insertscript", "insertdate"
)


class ORMAggregate(object):
    """ORMAggregate assumes """
    def __init__(self, codingjobs, article_ids):
        self.article_ids = set(article_ids)
        self.articles = Article.objects.filter(id__in=self.article_ids)
        self.articles = self.articles.select_related("medium").defer(*ARTICLE_EXCLUDE)
        self.codingjobs = codingjobs

        coded_articles = CodedArticle.objects.filter(
            codingjob__id__in=(c.id for c in self.codingjobs),
            article__id__in=article_ids
        )

        coded_articles_ids = coded_articles.values_list("id", flat=True)
        self.codings = Coding.objects.filter(id__in=coded_articles_ids)

    def _aggregate_on_article_field(self, articles, field):
        aggregate = collections.defaultdict(set)
        for article in articles:
            aggregate[getattr(article, field)].add(article)
        return aggregate

    def aggregate_day(self, interval):
        # Aggregating on an interval can only happen on the whole set of articles, as it is only
        # allowed on the x-axis.
        extra = "date_trunc('{interval}', date)".format(interval=interval)
        aggregate = self.articles.extra({'interval': extra}).defer().select_related().only("id")
        return self._aggregate_on_article_field(aggregate, "interval")

    def aggregate_medium(self, articles):
        return self._aggregate_on_article_field(articles, "medium")

    def get_aggregate(self, x_axis, y_axis, interval=None):
        """
        @param x_axis: "date", "medium"
        @param y_axis: "medium", "avg_<schemafieldid>"
        @param interval: if x_axis is date, specify an interval
        @return dict of dicts, containing the aggregation
        """
        x_aggr = collections.namedtuple("XAggr", [x_axis, "y"])
        y_aggr = collections.namedtuple("YAggr", [y_axis, "value"])

        for x_key, x_val in self._get_aggregate(x_axis, y_axis, interval).iteritems():
            yield x_aggr(x_key, [y_aggr(y_key, y_val) for y_key, y_val in x_val.items()])

    def _get_aggregate(self, x_axis, y_axis, interval):
        # Aggregate on x_axis
        if x_axis == "date":
            if interval not in ("day", "week", "month", "quarter", "year"):
                raise ValueError("Not a valid interval: {!r}".format(interval))
            aggregate = self.aggregate_day(interval)
        elif x_axis == "medium":
            aggregate = self.aggregate_medium(self.articles)
        else:
            raise ValueError("Not a valid x_axis: {!r}".format(x_axis))

        # Aggregate on y-axis.
        if y_axis == "medium":
            for aggr_key, articles in aggregate.items():
                aggregate[aggr_key] = len(self.aggregate_medium(articles))
        elif y_axis == "total":
            for aggr_key, articles in aggregate.items():
                aggregate[aggr_key] = len(articles)
        else:
            assert y_axis.startswith("schemafield_avg_")

            _, schemafield_id = y_axis.split("schemafield_avg_")
            schemafield = CodingSchemaField.objects.get(id=int(schemafield_id))
            for aggr_key, articles in aggregate.items():
                average = self.average_schemafield(articles, schemafield)

                if average is None:
                    del aggregate[aggr_key]
                else:
                    aggregate[aggr_key] = {schemafield: self.average_schemafield(articles, schemafield)}

        return aggregate

    def average_schemafield(self, articles, schemafield):
        article_ids = (a.id for a in articles)

        coding_values = CodingValue.objects \
            .filter(field=schemafield, coding__coded_article__article__id__in=article_ids) \
            .aggregate(avg=Avg("intval")) \
            .values()

        return coding_values[0]

