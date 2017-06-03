import csv
import datetime
import json
import os
from io import BytesIO

from collections import OrderedDict

from amcat.models import Article
from amcat.scripts.article_upload.upload import UploadScript, _open, ArticleField
from amcat.scripts.article_upload.upload_plugins import UploadPlugin

# At least this many fields have to match in order to detect it as that language. Set to 3,
# because EN and NL share 2 values: 'url' and 'type'
LANG_MATCH_THRESHOLD = 3


class Language:
    query = None
    date = None
    url = None
    sentiment = None
    type = None
    discussion_length = None
    reach = None
    author = None
    followers = None
    influence = None
    GPS_latitude = None
    GPS_longitude = None
    message_text = None
    source = None
    title = None

    @classmethod
    def matches(cls, items):
        """
        Test if a set of keys matches this language.
        @param items: The keys to test
        @return: True if it's a match, otherwise False.
        """
        if isinstance(items, dict):
            items = items.keys()
        items = set(items)
        known_cols = {v for k, v in cls.__dict__.items() if k[:2] != "__"}
        return len(items & known_cols) >= LANG_MATCH_THRESHOLD

    @classmethod
    def reverseMap(cls, language_clss):
        return {v: k for language_cls in language_clss for k, v in language_cls.__dict__.items() if k[:2] != "__"}


class Lang_NL(Language):
    query = "zoekopdracht"
    date = "datum"
    url = "url"
    sentiment = "sentiment"
    type = "type"
    discussion_length = "discussielengte"
    reach = "bereik"
    author = "auteur"
    followers = "volgers"
    influence = "invloed"
    GPS_latitude = "GPS breedtegraad"
    GPS_longitude = "GPS lengtegraad"
    message_text = "bericht tekst"
    source = "type bron"
    title = "titel"


class Lang_EN(Language):
    query = "query"
    date = "date"
    url = "url"
    sentiment = "sentiment"
    type = "type"
    discussion_length = "discussion length"
    reach = "reach"
    author = "author"
    followers = "followers"
    influence = "influence"
    GPS_latitude = "GPS latitude"
    GPS_longitude = "GPS longitude"
    message_text = "message text"
    source = "source"
    title = "title"


ESFIELDS = {
    # TODO: proper types
    'query': "query",
    'date': "date",
    'url': "url",
    'sentiment': "sentiment",
    'type': "type",
    'discussion_length': "discussionLength",
    'reach': "reach",
    'author': "author",
    'followers': "followers",
    'influence': "influence",
    'GPS_latitude': "GPSLatitude",
    'GPS_longitude': "GPSLongitude",
    'message_text': "text",
    'source': "source",
    'title': "title"
}


class CoostoForm(UploadScript.form_class):
    pass


@UploadPlugin(label="Coosto")
class CoostoUpload(UploadScript):
    """
    Upload Coosto files to AmCAT.    
    """
    options_form = CoostoForm
    languages = (Lang_EN, Lang_NL)

    @classmethod
    def get_fields(cls, file: str, encoding: str):
        fields = OrderedDict()
        fieldMap = Language.reverseMap(cls.languages)
        for file, encoding, _ in cls._get_files(file, encoding):
            reader = csv.DictReader(_open(file, encoding), delimiter=";")
            rows = [row for row in reader]
            fields.update((k, (fieldMap[k], [row[k] for row in rows])) for k in reader.fieldnames)

        for source, (destination, values) in fields.items():
            dest_name = ESFIELDS[destination]
            yield ArticleField(source, destination=dest_name, values=values)

    def parse_file(self, file: str, encoding: str, _: None):
        self.queries = set()
        rows = csv.DictReader(_open(file, encoding), delimiter=";")
        self.lang = self._get_language(rows)

        yield from (self._scrape_unit(row) for row in rows)

    def _scrape_unit(self, row):
        self.queries.add(row[self.lang.query])
        art = self.map_article(row)
        a = Article(**art)
        return a

    def _get_language(self, csvDictReader):
        try:
            lang = next(lang for lang in self.languages if lang.matches(csvDictReader.fieldnames))
        except StopIteration:
            raise Exception("Couldn't find a matching language")
        return lang

    def get_provenance(self, file, articles):
        n = len(articles)
        filename = os.path.split(file)[-1]
        timestamp = str(datetime.datetime.now())[:16]
        queries = "; ".join(self.queries)
        return ("[{timestamp}] Uploaded {n} articles from Coosto export {filename!r} "
                "queries: {queries}".format(**locals()))
