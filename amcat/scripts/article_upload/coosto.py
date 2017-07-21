from .fileupload import FileUploadForm
from .upload import UploadScript
import csv, datetime, json
from amcat.models import Article, Medium
from amcat.scripts.article_upload.fileupload import ZipFileUploadForm
import logging
log = logging.getLogger(__name__)

# At least this many fields have to match in order to detect it as that language. Set to 4,
# because EN and NL share 3 values: 'url', 'sentiment', and 'type'
LANG_MATCH_THRESHOLD = 4


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
        attrs = (v for k, v in cls.__dict__.items() if k[:2] != "__")
        known_cols = {field for attr in attrs for field in attr}
        return len(items & known_cols) >= LANG_MATCH_THRESHOLD

    @classmethod
    def popfield(cls, row, attr):
        """
        Pop the field from the row corresponding to the attribute
        """
        key = getattr(cls, attr)
        for k in key:
            if k in row:
                return row.pop(k)
        raise KeyError("Could not find key {key} in row {row}".format(**locals()))

class Lang_NL(Language):
    query = ["zoekopdracht"]
    date = ["datum"]
    url = ["url"]
    sentiment = ["sentiment"]
    type = ["type"]
    discussion_length = ["discussielengte"]
    reach = ["bereik", "views"]
    author = ["auteur"]
    followers = ["volgers"]
    influence = ["invloed"]
    GPS_latitude = ["GPS breedtegraad"]
    GPS_longitude = ["GPS lengtegraad"]
    message_text = ["bericht tekst"]
    source = ["type bron"]
    title = ["titel"]


class Lang_EN(Language):
    query = ["query"]
    date = ["date"]
    url = ["url"]
    sentiment = ["sentiment"]
    type = ["type"]
    discussion_length = ["discussion length"]
    reach = ["reach"]
    author = ["author"]
    followers = ["followers"]
    influence = ["influence"]
    GPS_latitude = ["GPS latitude"]
    GPS_longitude = ["GPS longitude"]
    message_text = ["message text"]
    source = ["source"]
    title = ["title"]


class CoostoForm(UploadScript.options_form, ZipFileUploadForm):
    pass


class CoostoUpload(UploadScript):
    """
    Upload Coosto files to AmCAT.    
    """
    options_form = CoostoForm
    languages = (Lang_EN, Lang_NL)

    def _get_units(self, file):
        from cStringIO import StringIO
        io = StringIO(file.text.encode("utf-8"))
        self.queries = set()
        rows = csv.DictReader(io, delimiter=";")
        self.lang = self._get_language(rows)
        return rows

    def _scrape_unit(self, row):
        row = {k: v.decode("utf-8") for k, v in row.iteritems()}
        query = self.lang.popfield(row, "query")
        self.queries.add(query)
        medium = Medium.get_or_create(self.lang.popfield(row, "source"))
        date = self.lang.popfield(row, "date")
        date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M")
        headline = self.lang.popfield(row, "title")
        pagenr = self.lang.popfield(row, "reach") or None
        text = self.lang.popfield(row, "message_text")
        url = self.lang.popfield(row, "url")
        author = self.lang.popfield(row, "author")
        metastring = json.dumps(row)

        a = Article(headline=headline, pagenr=pagenr,
                    text=text, date=date,
                    medium=medium, url=url,
                    author=author, metastring=metastring)
        yield a

    def _get_language(self, csvDictReader):
        try:
            lang = next(lang for lang in self.languages if lang.matches(csvDictReader.fieldnames))
        except StopIteration:
            raise Exception("Couldn't find a matching language")
        log.info("Coosto language detected: {}".format(lang.__name__))
        return lang

    def get_provenance(self, file, articles):
        n = len(articles)
        filename = file and file.name
        timestamp = unicode(datetime.datetime.now())[:16]
        queries = "; ".join(self.queries)
        return ("[{timestamp}] Uploaded {n} articles from Coosto export {filename!r} "
                "queries: {queries}".format(**locals()))
