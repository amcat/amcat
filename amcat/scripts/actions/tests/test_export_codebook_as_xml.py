from lxml import etree
from amcat.models import Codebook
from amcat.scripts.actions.export_codebook_as_xml import codebook_to_xml
from amcat.tools import amcattest


class TestExportCodebookAsXML(amcattest.AmCATTestCase):
    def test_codebook_to_xml(self):
        # Empty codebook
        cb = codebook_to_xml(amcattest.create_test_codebook())

        self.assertEquals(cb.tag, "codebook")
        children = [c.tag for c in cb.iterchildren()]

        for prop in ("project_id", "name", "roots", "id"):
            self.assertTrue(prop in children)

        self.assertFalse(len([c for c in cb.find("roots")]))

        # Codebook with two roots
        cb = codebook_to_xml(amcattest.create_test_codebook_with_codes()[0])
        self.assertEquals([c.find("label").text for c in cb.find("roots")], ["A", "B"])
        self.assertTrue(b"A1a" in etree.tostring(cb))

        # Test unicode
        cb = amcattest.create_test_codebook_with_codes()[0]
        c = cb.codes[0]
        c.label = u"\u2603"  # It's Mr. Snowman!
        c.save()

        # Shouldn't raise errors
        cb = codebook_to_xml(Codebook.objects.get(id=cb.id))
        etree.tostring(cb)
