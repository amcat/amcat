from collections import OrderedDict

import datetime
from django.core.files.uploadedfile import UploadedFile
from lxml import etree, html

import iso8601

from amcat import models
from amcat.models import Article
from amcat.scripts.article_upload.upload import UploadScript, ArticleField
from amcat.scripts.article_upload.upload_plugins import UploadPlugin
from amcat.tools import toolkit
from amcat.tools.amcates import get_property_primitive_type


class XMLUploadBase(UploadScript):
    articlePath = None
    exclude_paths = ()
    suggested_fields = ()

    @classmethod
    def parseElement(cls, el):
        return el.text

    @classmethod
    def _preprocess(cls, file: UploadedFile):
        t = etree.ElementTree(file=file)
        data = []
        for article in t.iterfind(cls.articlePath):
            articletree = etree.ElementTree(article)
            paths = ((articletree.getelementpath(el), etree.tounicode(el), cls.parseElement(el)) for el in articletree.iter())
            data.append([{"path": path, "content": text, "outerXML": xml} for path, xml, text in paths])
        return data

    @classmethod
    def get_fields(cls, upload: models.UploadedFile):
        suggested_fields = dict(cls.suggested_fields)
        fields = OrderedDict()
        for file, data in cls._get_files(upload):
            for art in data:
                for field in art:
                    path = field['path']
                    content = field['content']

                    if not content or path in cls.exclude_paths:
                        continue

                    if path not in fields:
                        fields[path] = ArticleField(label=path, values=[], suggested_destination=suggested_fields.get(path))

                    fields[path].values.append("".join(txt or "" for txt in content))

        return list(fields.values())


@UploadPlugin(label="XML Article", mime_types="application/xml")
class XMLSingleArticle(XMLUploadBase):
    articlePath = "."
    exclude_paths = (".", "itemMeta", "contentMeta", "contentSet")
    suggested_fields = (("contentMeta/contentCreated", "date"),
                        ("contentSet/inlineXML", "text"),
                        ("contentMeta/headline", "title"))

    @classmethod
    def get_fields(cls, upload):
        fieldnames = [f[0] for f in cls.suggested_fields]
        return sorted(super().get_fields(upload), key=(lambda field: field.label not in fieldnames))

    @classmethod
    def parseElement(cls, el):
        if el.tag == "inlineXML" and "html" in el.attrib["contenttype"]:
            return html.fromstring(el.text).text_content()
        if el.tag in ("contentCreated", "versionCreated"):
            return iso8601.parse_date(el.text)
        return super().parseElement(el)

    def parse_file(self, file: UploadedFile, _data):
        for fields in _data:
            data = {f["path"]: f["content"] for f in fields}
            art = {}
            for field, setting in self.options['field_map'].items():
                datatype = get_property_primitive_type(field)
                value, typ = setting['value'], setting['type']
                val = data.get(value) if typ == 'field' else value
                if val:
                    if datatype is datetime.datetime and type(val) is str:
                        val = toolkit.read_date(val)
                    art[field] = val
            yield Article(**art)