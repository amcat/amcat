from .fileupload import FileUploadForm
from .upload import UploadScript
import csv, datetime, json
from io import BytesIO
from amcat.models import Article, Medium
from amcat.scripts.article_upload.fileupload import ZipFileUploadForm


class CoostoForm(UploadScript.options_form, ZipFileUploadForm):
    pass

class CoostoUpload(UploadScript):
    """
    Upload Coosto files to AmCAT.    
    """
    options_form =  CoostoForm

    def _get_units(self, file):
        io = BytesIO(file.text.encode("utf-8"))
        self.queries = set()
        rows = csv.DictReader(io, delimiter=";")
        return rows
        
    def _scrape_unit(self, row):
        row = {k:v.decode("utf-8") for k,v in row.iteritems()}
        query = row.pop('zoekopdracht')
        self.queries.add(query)
        medium = Medium.get_or_create(row.pop('type bron'))
        date = row.pop('datum')
        date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M")
        headline = row.pop('titel')
        pagenr = row.pop('bereik') or None
        text = row.pop('bericht tekst')
        url = row.pop('url')
        author=row.pop('auteur')
        metastring = json.dumps(row)
        
        a = Article(headline=headline, pagenr=pagenr,
                    text=text, date=date,
                    medium=medium, url=url,
                    author=author, metastring=metastring)
        yield a 

    def get_provenance(self, file, articles):
        n = len(articles)
        filename = file and file.name
        timestamp = unicode(datetime.datetime.now())[:16]
        queries = "; ".join(self.queries)
        return ("[{timestamp}] Uploaded {n} articles from Coosto export {filename!r} "
                "queries: {queries}".format(**locals()))


        
